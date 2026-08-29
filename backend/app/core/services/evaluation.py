"""
evaluation.py

Runs structured evaluation fixtures against:
  - OKI agent (two-pass extraction + weighted resolution)
  - Baseline: most-recent-wins
  - Baseline: authority-only
  - Baseline: corroboration-only

Returns structured comparison results for the Evaluation page.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "fixtures"


def load_fixtures(fixture_file: str = "eval_cases.json") -> list[dict]:
    path = FIXTURES_DIR / fixture_file
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_evaluation(conn, fixture_file: str = "eval_cases.json") -> dict:
    """
    Run the evaluation suite. Each fixture has:
      case_input: dict of case_fields
      process: str
      expected_decision: str
      expected_confidence_min: float
      expected_escalated: bool
    """
    fixtures = load_fixtures(fixture_file)
    if not fixtures:
        return {"error": "No fixtures found", "fixture_file": fixture_file}

    from app.core.services.decide_case import decide_case
    from app.adapters.storage.sqlite.repositories import insert_case

    results: dict[str, list[dict]] = {
        "oki_agent": [],
        "baseline_most_recent": [],
        "baseline_authority": [],
        "baseline_corroboration": [],
    }

    for fx in fixtures:
        process = fx["process"]
        case_fields = fx["case_input"]

        # ── OKI Agent ─────────────────────────────────────────────────────
        case_id = insert_case(conn, process=process, source="evaluation", payload=case_fields)
        output = decide_case(conn, case_id, process, case_fields)
        results["oki_agent"].append(_eval_result(fx, output, "oki_agent"))

        # ── Naive baselines (no LLM — pure rule selection heuristics) ─────
        for strategy in ("most_recent", "authority", "corroboration"):
            baseline_output = _run_naive_baseline(conn, process, case_fields, strategy)
            results[f"baseline_{strategy}"].append(
                _eval_result(fx, baseline_output, f"baseline_{strategy}")
            )

    summary = _compute_summary(results, fixtures)

    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "fixture_file": fixture_file,
        "fixture_count": len(fixtures),
        "results": results,
        "summary": summary,
    }


def _build_baseline_rules(conn, strategy: str, process: str) -> list[dict]:
    """
    Resolve raw candidate_rules for `process` using only the single naive heuristic:
      - most_recent   : picks newest candidate rule in each cluster
      - authority     : picks highest authority candidate rule in each cluster
      - corroboration : picks most frequently corroborated candidate rule in each cluster
    """
    from app.core.services.resolve_conflicts import _cluster_rules
    from app.adapters.retrieval.tfidf_retriever import TFIDFRetriever
    from app.db.json_compat import extract_json_array_element

    rows = conn.execute(
        "SELECT cr.* FROM candidate_rules cr "
        "WHERE cr.process = ?",
        (process,),
    ).fetchall()

    if not rows:
        return []

    rows_as_dicts = [dict(r) for r in rows]
    for row_dict in rows_as_dicts:
        doc_id = extract_json_array_element(row_dict, "source_document_ids_json", 0)
        if doc_id:
            doc_row = conn.execute(
                "SELECT timestamp, metadata_json FROM documents WHERE id = ?",
                (int(doc_id),),
            ).fetchone()
            if doc_row:
                row_dict.update(dict(doc_row))
    groups = _cluster_rules(rows_as_dicts, TFIDFRetriever())

    resolved = []
    for g in groups:
        if strategy == "most_recent":
            winner = max(g, key=lambda r: r.get("timestamp") or "2020-01-01")
            resolved.append(winner)
        elif strategy == "authority":
            def _get_auth(r):
                meta = json.loads(r.get("metadata_json") or "{}")
                return float(r.get("authority_score") or meta.get("authority_score") or 0.5)
            winner = max(g, key=_get_auth)
            resolved.append(winner)
        elif strategy == "corroboration":
            counts = {}
            for r in g:
                k = r.get("trigger_text", "")
                counts[k] = counts.get(k, 0) + 1
            winner = max(g, key=lambda r: counts.get(r.get("trigger_text", ""), 1))
            resolved.append(winner)
    return resolved


def _run_naive_baseline(conn, process: str, case_fields: dict, strategy: str):
    """
    Evaluate a case against rules resolved purely by the naive baseline strategy.
    """
    from app.core.domain.entities import DecisionOutput
    from app.core.services.decide_case import _eval_condition, _normalize_decision
    from app.core.domain.risk import classify_risk

    b_rules = _build_baseline_rules(conn, strategy, process)

    match = None
    for r in b_rules:
        if _eval_condition(r.get("trigger_text", ""), case_fields) is True:
            match = r
            break

    if not match:
        return DecisionOutput(
            case_id="baseline",
            escalated=True,
            escalation_reason=f"No matching rule resolved by {strategy} baseline",
            decision=None,
            confidence=0.40,
        )

    raw_action = match.get("action", "")
    confidence = float(match.get("confidence", 0.70))

    risk = classify_risk(
        action_type=raw_action or "escalate_to_human",
        process=process,
        confidence=confidence,
        amount=float(case_fields.get("order_value", 0) or case_fields.get("discount_percent", 0) or 0),
        severity=str(case_fields.get("severity_signal") or case_fields.get("severity") or ""),
    )

    requires_approval = risk.requires_approval or (confidence < 0.55)
    norm_decision = _normalize_decision(raw_action, requires_approval=requires_approval, is_escalated=False)
    escalated = requires_approval or (risk.level == "high") or (norm_decision == "escalate") or ("escalat" in raw_action.lower())

    return DecisionOutput(
        case_id="baseline",
        decision=norm_decision,
        matched_rule_id=str(match.get("id", "")),
        source_citation=match.get("trigger_text", ""),
        confidence=round(confidence, 4),
        escalated=escalated,
        escalation_reason=risk.reason if escalated else None,
        best_guess=norm_decision,
    )


def _is_decision_match(actual: str | None, expected: str | None, expected_escalated: bool = False) -> bool:
    if actual == expected:
        return True
    # Both 'escalate' and 'requires_approval' represent the same human escalation outcome
    if expected_escalated and actual in ("escalate", "requires_approval") and expected in ("escalate", "requires_approval"):
        return True
    return False


def _eval_result(fx: dict, output, strategy: str) -> dict:
    expected = fx.get("expected_decision")
    expected_escalated = fx.get("expected_escalated", False)
    correct = _is_decision_match(output.decision, expected, expected_escalated)
    confidence_ok = (output.confidence or 0) >= float(fx.get("expected_confidence_min", 0))
    escalation_ok = output.escalated == expected_escalated
    return {
        "case_id": str(output.case_id),
        "process": fx["process"],
        "strategy": strategy,
        "expected_decision": expected,
        "actual_decision": output.decision,
        "correct": correct,
        "expected_confidence_min": fx.get("expected_confidence_min"),
        "actual_confidence": output.confidence,
        "confidence_ok": confidence_ok,
        "expected_escalated": fx.get("expected_escalated"),
        "actual_escalated": output.escalated,
        "escalation_ok": escalation_ok,
    }


def _compute_summary(results: dict, fixtures: list[dict]) -> dict:
    summary = {}
    for strategy, cases in results.items():
        n = len(cases)
        if n == 0:
            continue
        correct = sum(1 for c in cases if c["correct"] is True)
        confidence_ok = sum(1 for c in cases if c.get("confidence_ok"))
        escalation_ok = sum(1 for c in cases if c.get("escalation_ok"))
        summary[strategy] = {
            "n": n,
            "accuracy": round(correct / n, 3) if n else 0,
            "confidence_pass_rate": round(confidence_ok / n, 3) if n else 0,
            "escalation_accuracy": round(escalation_ok / n, 3) if n else 0,
        }
    return summary
