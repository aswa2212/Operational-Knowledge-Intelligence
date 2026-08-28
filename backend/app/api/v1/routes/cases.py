"""
cases.py — Case submission and decision routes.

POST /cases             → submit a new case
GET  /cases             → list cases
GET  /cases/{id}        → case detail with decision trace
POST /cases/{id}/decide → run agent orchestrator
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.connection import get_db

router = APIRouter(prefix="/cases", tags=["Cases"])


class CaseSubmit(BaseModel):
    process: str
    fields: dict
    source: str = "api"


@router.post("", status_code=201)
def submit_case(body: CaseSubmit):
    conn = get_db()
    from app.core.services.decide_case import submit_and_decide
    case_id, output = submit_and_decide(conn, body.process, body.fields, source=body.source)
    return {
        "case_id": case_id,
        "decision": output.decision,
        "confidence": output.confidence,
        "matched_rule_id": output.matched_rule_id,
        "escalated": output.escalated,
        "escalation_reason": output.escalation_reason,
        "best_guess": output.best_guess,
    }


@router.get("")
def list_cases(
    process: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    conn = get_db()
    filters, params = [], []
    if process:
        filters.append("c.process = ?"); params.append(process)
    if status:
        filters.append("c.status = ?"); params.append(status)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    query = f"""
        SELECT c.*,
               d.id as dec_id, d.decision, d.confidence, d.matched_rule_id,
               d.risk_level, d.escalated, d.reason as dec_reason,
               d.trace_json, d.created_at as dec_created_at
        FROM cases c
        LEFT JOIN decisions d ON d.id = (
            SELECT id FROM decisions WHERE case_id = c.id ORDER BY created_at DESC LIMIT 1
        )
        {where}
        ORDER BY c.created_at DESC
        LIMIT ?
    """
    rows = conn.execute(query, params + [limit]).fetchall()
    results = []
    for r in rows:
        row_dict = dict(r)
        if row_dict.get("dec_id"):
            row_dict["decision"] = {
                "id": row_dict["dec_id"],
                "case_id": row_dict["id"],
                "decision": row_dict.get("decision"),
                "confidence": row_dict.get("confidence"),
                "matched_rule_id": row_dict.get("matched_rule_id"),
                "risk_level": row_dict.get("risk_level"),
                "escalated": row_dict.get("escalated"),
                "reason": row_dict.get("dec_reason"),
                "trace_json": row_dict.get("trace_json"),
                "created_at": row_dict.get("dec_created_at"),
            }
        results.append(row_dict)
    return results


@router.get("/{case_id}")
def get_case(case_id: int):
    conn = get_db()
    case_row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not case_row:
        raise HTTPException(status_code=404, detail="Case not found")
    result = dict(case_row)

    # Attach decision
    dec_row = conn.execute(
        "SELECT * FROM decisions WHERE case_id = ? ORDER BY created_at DESC LIMIT 1", (case_id,)
    ).fetchone()
    if dec_row:
        d = dict(dec_row)
        d["trace"] = json.loads(d.get("trace_json") or "{}")
        result["decision"] = d

    return result


@router.post("/{case_id}/decide")
def decide_existing_case(case_id: int):
    conn = get_db()
    case_row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not case_row:
        raise HTTPException(status_code=404, detail="Case not found")

    from app.core.services.decide_case import decide_case
    case_fields = json.loads(case_row["payload_json"] or "{}")
    output = decide_case(conn, case_id, case_row["process"], case_fields)

    return {
        "case_id": case_id,
        "decision": output.decision,
        "confidence": output.confidence,
        "matched_rule_id": output.matched_rule_id,
        "escalated": output.escalated,
        "escalation_reason": output.escalation_reason,
    }
