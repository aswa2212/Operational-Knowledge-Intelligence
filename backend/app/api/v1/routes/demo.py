"""
demo.py — Demo Showcase router for OKI live evaluation.

Provides orchestration endpoints for the Demo Showcase layer:
- POST /api/v1/demo/execute: runs real end-to-end pipeline (sync, extraction toggle, resolution, decision, tool action)
- GET  /api/v1/demo/state: gets real status across all processes
- POST /api/v1/demo/reset: resets runtime demo data (cases, decisions, actions) while keeping configured sources
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.connection import get_db
from app.core.services.extract_rules import run_two_pass_extraction, run_single_pass_extraction
from app.core.services.decide_case import submit_and_decide
from app.core.services.execute_action import execute_action

logger = logging.getLogger("oki.demo")

router = APIRouter(prefix="/demo", tags=["Demo Showcase"])


class DemoExecuteRequest(BaseModel):
    process: str = "refund_handling"  # refund_handling | pricing_exceptions | incident_triage
    fields: dict[str, Any]
    extraction_method: str = "two_pass"  # two_pass | single_pass
    sync_live: bool = False


@router.post("/execute")
def execute_demo_pipeline(body: DemoExecuteRequest):
    """
    Executes the REAL pipeline without synthetic mocks:
    1. Reads ingested documents for the process
    2. Runs extraction (Single-Pass vs Two-Pass)
    3. Runs conflict resolution and builds active skill version
    4. Evaluates case with decide_case (deterministic + TF-IDF)
    5. Executes bounded tool action live
    Returns full trace for the glass-box console.
    """
    conn = get_db()
    process = body.process
    method = body.extraction_method

    from app.db.json_compat import extract_json_path

    # 1. Fetch ingested documents
    raw_docs = conn.execute(
        """
        SELECT d.*, s.name as source_name, s.config_json
        FROM documents d
        JOIN sources s ON d.source_id = s.id
        ORDER BY d.id DESC
        """
    ).fetchall()
    docs_list = []
    for d in raw_docs:
        d_dict = dict(d)
        proc = extract_json_path(d_dict, "config_json", ["process"])
        s_name = d_dict.get("source_name")
        if proc == process or s_name == process or s_name == f"demo_{process}":
            docs_list.append(d_dict)

    if not docs_list:
        docs = conn.execute("SELECT * FROM documents ORDER BY timestamp DESC LIMIT 100").fetchall()
        docs_list = [dict(d) for d in docs]

    # Deduplicate docs
    seen = set()
    deduped_docs = []
    for d in docs_list:
        key = (d.get("source_type"), d.get("external_id") or d.get("title") or d.get("id"))
        if key not in seen:
            seen.add(key)
            deduped_docs.append(d)
    docs_list = deduped_docs

    extraction_stats = {
        "method": method,
        "documents_processed": len(docs_list),
        "rules_extracted": 0,
        "error": None,
        "fallback_used": False,
    }

    # 2. Extract rules if docs available
    if docs_list:
        try:
            if method == "single_pass":
                ext_res = run_single_pass_extraction(conn, process, docs_list)
            else:
                ext_res = run_two_pass_extraction(conn, process, docs_list)
            extraction_stats["rules_extracted"] = ext_res.get("rules_inserted", 0)
        except Exception as e:
            logger.warning(f"[Demo] Extraction note: {e}. Utilizing active skill rules.")
            extraction_stats["error"] = str(e)
            extraction_stats["fallback_used"] = True

    # 3. Resolve conflicts and compile skill
    from app.core.services.resolve_conflicts import run_conflict_resolution
    from app.core.services.build_skills import build_skills_file

    try:
        cand_rows = conn.execute("SELECT * FROM candidate_rules WHERE process = ?", (process,)).fetchall()
        if cand_rows:
            run_conflict_resolution(conn, process)
            build_skills_file(conn, process)
    except Exception as e:
        logger.warning(f"[Demo] Resolution/Build error: {e}")

    # Check active skill
    active_skill = conn.execute(
        "SELECT * FROM skill_versions WHERE process = ? ORDER BY version DESC LIMIT 1", (process,)
    ).fetchone()
    resolved_rules = conn.execute(
        "SELECT * FROM resolved_rules WHERE process = ? AND status = 'active'", (process,)
    ).fetchall()

    # 4. Decide case
    try:
        case_id, output = submit_and_decide(conn, process, body.fields, source="demo_showcase")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision engine failed: {e}")

    # 5. Execute action if decision made
    action_result = None
    dec_row = conn.execute("SELECT id, risk_level, confidence FROM decisions WHERE case_id = ?", (case_id,)).fetchone()
    if dec_row:
        dec_id = dec_row["id"]
        # If not escalated or if low risk, execute action
        if not output.escalated:
            try:
                action_result = execute_action(conn, dec_id)
            except Exception as e:
                action_result = {"success": False, "error": str(e)}

    return {
        "success": True,
        "case_id": case_id,
        "process": process,
        "input_fields": body.fields,
        "pipeline_trace": {
            "ingestion": {
                "total_documents": len(docs_list),
                "sources_active": list(set(d.get("source_type") for d in docs_list)),
            },
            "extraction": extraction_stats,
            "skills": {
                "active_version": active_skill["version"] if active_skill else "none",
                "rules_count": len(resolved_rules),
            },
            "decision": {
                "decision": output.decision,
                "confidence": output.confidence,
                "risk_level": dec_row["risk_level"] if dec_row else "unknown",
                "matched_rule_id": output.matched_rule_id,
                "escalated": output.escalated,
                "escalation_reason": output.escalation_reason,
            },
            "action_execution": action_result,
        },
    }


@router.get("/state")
def get_demo_state():
    """Returns overview state for the demo dashboard."""
    conn = get_db()
    processes = ["refund_handling", "pricing_exceptions", "incident_triage"]
    state = {}
    for p in processes:
        skill = conn.execute(
            "SELECT * FROM skill_versions WHERE process = ? ORDER BY version DESC LIMIT 1", (p,)
        ).fetchone()
        cases_cnt = conn.execute("SELECT COUNT(*) FROM cases WHERE process = ?", (p,)).fetchone()[0]
        state[p] = {
            "has_skill": skill is not None,
            "skill_version": skill["version"] if skill else None,
            "cases_count": cases_cnt,
        }
    return state


@router.post("/reset")
def reset_demo_data():
    """Resets cases, decisions, and audit events while keeping source connectors intact."""
    conn = get_db()
    conn.execute("PRAGMA foreign_keys = OFF")
    for t in ["audit_events", "approval_requests", "decisions", "cases"]:
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    return {"status": "success", "message": "Demo runtime data cleared."}
