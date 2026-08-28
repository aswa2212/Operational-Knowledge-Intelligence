#!/usr/bin/env python
"""
run_demo.py — OKI end-to-end demonstration script.

Run from repo root:
    python scripts/run_demo.py

What it does (Tier 1 happy path):
  1. Health-check the backend
  2. Register synthetic sources for both demo processes
  3. Sync each source (ingest documents)
  4. Run rule extraction (two-pass) for each process
  5. Run conflict resolver for each process
  6. Build skill packages for each process
  7. Submit 4 representative cases (2x refund, 2x incident) and print decisions
  8. List pending approvals (high-risk cases escalated to human)
  9. Run the evaluation harness and print pass/fail counts
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

BASE = "http://localhost:8000/api/v1"
TIMEOUT = 30.0          # default per-request timeout
EXTRACTION_TIMEOUT = 300.0  # extraction makes N LLM calls — give it 5 minutes

PROCESSES = ["refund_handling", "incident_triage"]

# ─── Demo case payloads ────────────────────────────────────────────────────────
DEMO_CASES = [
    {
        "label": "Small refund, standard customer (expect: approve)",
        "process": "refund_handling",
        "fields": {
            "days_since_purchase": 20,
            "order_value": 80,
            "customer_tier": "standard",
            "item_category": "software",
            "reason": "product_defect",
        },
    },
    {
        "label": "Large refund, VIP customer (expect: escalate to human)",
        "process": "refund_handling",
        "fields": {
            "days_since_purchase": 5,
            "order_value": 1200,
            "customer_tier": "VIP",
            "item_category": "electronics",
            "reason": "dissatisfied",
        },
    },
    {
        "label": "DDoS affecting 50k users (expect: escalate to human)",
        "process": "incident_triage",
        "fields": {
            "error_type": "DDoS",
            "affected_users_count": 50000,
            "system_component": "api_gateway",
            "severity_signal": "service_down",
        },
    },
    {
        "label": "Isolated auth failure (expect: auto-handle)",
        "process": "incident_triage",
        "fields": {
            "error_type": "auth_failure",
            "affected_users_count": 3,
            "system_component": "auth_service",
            "severity_signal": "isolated",
        },
    },
]

# ─── Helper ────────────────────────────────────────────────────────────────────

def _req(
    client: httpx.Client,
    method: str,
    path: str,
    body: Any = None,
    *,
    label: str = "",
    timeout: float | None = None,
) -> dict:
    url = f"{BASE}{path}"
    resp = client.request(method, url, json=body, timeout=timeout or TIMEOUT)
    if resp.status_code >= 400:
        print(f"  x {label or path}  [{resp.status_code}]: {resp.text[:200]}")
        return {}
    data = resp.json()
    return data


def section(title: str) -> None:
    width = 60
    print(f"\n{'--' * 30}")
    print(f"  {title}")
    print(f"{'--' * 30}")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n=== OKI - Operational Knowledge Intelligence Demo ===")

    client = httpx.Client(timeout=TIMEOUT)

    # 1. Health check
    section("1. Health check")
    health = _req(client, "GET", "/health", label="health")
    if health.get("status") != "ok":
        print("  Backend not reachable -- start it with:")
        print("    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir backend")
        sys.exit(1)
    print(f"  OK Backend healthy -- version {health.get('version')}")

    # 2. Register sources
    section("2. Register synthetic sources")
    source_ids: dict[str, int] = {}
    for process in PROCESSES:
        result = _req(
            client, "POST", "/sources",
            {"type": "synthetic", "name": f"demo_{process}", "config": {"process": process}},
            label=f"create source {process}",
        )
        sid = result.get("id")
        if sid:
            source_ids[process] = sid
            print(f"  OK Registered source id={sid}  process={process}")
        else:
            print(f"  -- Source may already exist for {process} -- continuing")

    # If we didn't get IDs from creation (already existed), fetch them
    if len(source_ids) < len(PROCESSES):
        sources = _req(client, "GET", "/sources", label="list sources")
        for s in sources:
            config = json.loads(s.get("config_json", "{}"))
            p = config.get("process", "")
            if p in PROCESSES and p not in source_ids:
                source_ids[p] = s["id"]

    # 3. Sync sources
    section("3. Sync sources (ingest documents)")
    for process, sid in source_ids.items():
        result = _req(client, "POST", f"/sources/{sid}/sync", label=f"sync {process}")
        inserted = result.get("inserted", "?")
        print(f"  OK Synced {process}  ->  {inserted} documents ingested")
        time.sleep(0.5)

    # 4. Run extraction
    section("4. Rule extraction (two-pass LLM)")
    for process in PROCESSES:
        print(f"  ... Extracting rules for {process} ...")
        result = _req(
            client, "POST", "/extraction/run",
            {"process": process, "method": "two_pass"},
            label=f"extraction {process}",
            timeout=EXTRACTION_TIMEOUT,
        )
        extracted = result.get("two_pass", {}).get("rules_inserted", 0)
        docs_processed = result.get("two_pass", {}).get("docs_processed", 0)
        print(f"  OK {process}  ->  rules_extracted={extracted}  docs_processed={docs_processed}")
        time.sleep(1)

    # 5. Conflict resolution
    section("5. Conflict resolver")
    for process in PROCESSES:
        result = _req(
            client, "POST", "/conflicts/resolve-run",
            {"process": process},
            label=f"resolve {process}",
        )
        resolved = result.get("resolved", 0)
        flagged = result.get("flagged", 0)
        print(f"  OK {process}  ->  resolved={resolved}  flagged_for_human={flagged}")

    # 6. Build skill packages
    section("6. Build skill packages")
    for process in PROCESSES:
        result = _req(
            client, "POST", "/skills/build",
            {"process": process},
            label=f"build skill {process}",
        )
        version = result.get("version", "?")
        rule_count = result.get("rule_count", "?")
        print(f"  OK {process}  ->  v{version}  ({rule_count} rules)")

    # 7. Submit demo cases
    section("7. Submit demo cases through decision agent")
    for case in DEMO_CASES:
        print(f"\n  Case: {case['label']}")
        result = _req(
            client, "POST", "/cases",
            {"process": case["process"], "fields": case["fields"]},
            label="submit case",
        )
        if result:
            decision = result.get("decision", "unknown")
            conf = result.get("confidence", 0)
            escalated = result.get("escalated", False)
            case_id = result.get("case_id", "?")
            icon = "ESCALATED" if escalated else ("APPROVED" if "approve" in decision else "DENIED")
            print(f"  [{icon}] Case #{case_id}  |  decision={decision}  |  confidence={conf:.0%}  |  escalated={escalated}")

    # 8. Pending approvals
    section("8. Pending human approvals")
    approvals = _req(client, "GET", "/approvals?status=pending", label="list approvals")
    if isinstance(approvals, list):
        if approvals:
            for a in approvals:
                print(f"  PENDING Approval #{a['id']}  type={a['type']}  |  {a.get('reason', '')[:80]}")
        else:
            print("  OK No pending approvals")

    # 9. Evaluation
    section("9. Evaluation harness")
    print("  ... Running evaluation fixtures ...")
    result = _req(
        client, "POST", "/evaluation/run",
        {"fixture_file": "eval_cases.json"},
        label="evaluation run",
    )
    if result:
        fixture_count = result.get("fixture_count", 0)
        summary = result.get("summary", {})
        agent_summary = summary.get("oki_agent", {})
        n = agent_summary.get("n", fixture_count)
        acc = agent_summary.get("accuracy", 0)
        passed = round(acc * n) if n else 0
        status = "PASS" if acc >= 0.8 else "WARN"
        print(f"  [{status}] {passed}/{n} passed  |  accuracy={acc:.0%}")

    client.close()
    print("\n=== Demo complete. Open http://localhost:5173 to view the live dashboard. ===\n")


if __name__ == "__main__":
    main()
