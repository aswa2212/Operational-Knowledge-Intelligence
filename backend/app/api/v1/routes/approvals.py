"""
approvals.py — Human approval center routes.

GET  /approvals           → list pending approvals
GET  /approvals/{id}      → approval detail (LLM summary card cached after first load)
POST /approvals/{id}/approve → approve (triggers action execution)
POST /approvals/{id}/reject  → reject with reason

Performance fix: The LLM summary_card is generated once in a background thread
and cached as summary_card_json in the DB row.  Subsequent GET calls return the
cached card instantly — no LLM wait.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Thread

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.connection import get_db

router = APIRouter(prefix="/approvals", tags=["Approvals"])


class ApprovalAction(BaseModel):
    resolved_by: str = "human"
    reason: str = ""


# ── Ensure summary_card_json column exists (idempotent) ───────────────────────

def _ensure_summary_card_col(conn) -> None:
    try:
        conn.execute("ALTER TABLE approval_requests ADD COLUMN summary_card_json TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists


# ── Background LLM summary generator ─────────────────────────────────────────

def _generate_summary_card(approval_id: int, result: dict) -> None:
    """Run in a daemon thread — generates the AI card and caches it in the DB."""
    try:
        from app.adapters.llm.ollama_provider import get_llm_provider
        from app.prompts.approval_summary_v1 import (
            APPROVAL_SUMMARY_SYSTEM,
            APPROVAL_SUMMARY_USER,
        )

        llm = get_llm_provider()
        prompt = (
            APPROVAL_SUMMARY_SYSTEM
            + "\n\n"
            + APPROVAL_SUMMARY_USER.format(
                approval_type=result.get("type", "action"),
                case_fields=json.dumps(result.get("case_fields", {}), indent=2),
                decision=result.get("decision", ""),
                confidence=result.get("confidence", 0),
                matched_rule_id="",
                risk_level=result.get("risk_level", "medium"),
                escalation_reason=result.get("escalation_reason", ""),
            )
        )
        card = llm.complete_json(prompt, temperature=0.0)
        card_json = json.dumps(card if isinstance(card, dict) else {})

        conn = get_db()
        _ensure_summary_card_col(conn)
        conn.execute(
            "UPDATE approval_requests SET summary_card_json = ? WHERE id = ?",
            (card_json, approval_id),
        )
        conn.commit()
    except Exception:
        pass  # silently fail — summary card is optional UI enhancement


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
def list_approvals(status: str = "pending"):
    conn = get_db()
    rows = conn.execute(
        "SELECT ap.id, ap.decision_id, ap.type, ap.status, ap.requested_action_json, "
        "ap.reason, ap.requested_at, ap.resolved_at, ap.resolved_by, "
        "d.decision, d.confidence, d.risk_level, d.reason as decision_reason "
        "FROM approval_requests ap "
        "LEFT JOIN decisions d ON d.id = ap.decision_id "
        "WHERE ap.status = ? ORDER BY ap.requested_at DESC",
        (status,),
    ).fetchall()
    results = []
    for r in rows:
        row_dict = dict(r)
        row_dict["requested_action"] = json.loads(row_dict.get("requested_action_json") or "{}")
        # Expose escalation_reason for UI from the decision's reason field
        row_dict["escalation_reason"] = row_dict.pop("decision_reason", None)
        results.append(row_dict)
    return results


@router.get("/{approval_id}")
def get_approval(approval_id: int):
    conn = get_db()
    _ensure_summary_card_col(conn)

    row = conn.execute(
        "SELECT ap.id, ap.decision_id, ap.type, ap.status, ap.requested_action_json, "
        "ap.reason, ap.requested_at, ap.resolved_at, ap.resolved_by, ap.summary_card_json, "
        "d.decision, d.confidence, d.risk_level, d.trace_json, d.reason as decision_reason, "
        "c.payload_json as case_payload, c.process "
        "FROM approval_requests ap "
        "LEFT JOIN decisions d ON d.id = ap.decision_id "
        "LEFT JOIN cases c ON c.id = d.case_id "
        "WHERE ap.id = ?",
        (approval_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")

    result = dict(row)
    result["requested_action"] = json.loads(result.get("requested_action_json") or "{}")
    result["trace"] = json.loads(result.get("trace_json") or "{}")
    result["case_fields"] = json.loads(result.get("case_payload") or "{}")
    result["escalation_reason"] = result.pop("decision_reason", None)

    # ── Fast path: return cached summary card ─────────────────────────────────
    cached = result.get("summary_card_json")
    if cached:
        try:
            result["summary_card"] = json.loads(cached)
        except Exception:
            result["summary_card"] = {}
        return result

    # ── No cache yet: return immediately, generate card in background ─────────
    result["summary_card"] = {}
    Thread(
        target=_generate_summary_card,
        args=(approval_id, dict(result)),
        daemon=True,
    ).start()
    return result


@router.post("/{approval_id}/approve")
def approve(approval_id: int, body: ApprovalAction):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM approval_requests WHERE id = ?", (approval_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Approval is already {row['status']}")

    decision_id = row["decision_id"]
    resolved_by = body.resolved_by

    if row["type"] == "action" and decision_id:
        # ── Mark as 'approved' immediately so UI unblocks ─────────────────
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE approval_requests SET status = 'approved', resolved_at = ?, resolved_by = ? WHERE id = ?",
            (now, resolved_by, approval_id),
        )
        conn.commit()

        # ── Execute the real action in a background thread ─────────────────
        # This avoids blocking the HTTP response on slow external calls
        # (GitHub/Slack can each take up to their timeout to respond).
        def _run_action():
            try:
                from app.db.connection import get_db as _get_db
                from app.core.services.execute_action import execute_action
                bg_conn = _get_db()
                execute_action(bg_conn, decision_id, approval_id=approval_id)
            except Exception:
                pass  # errors are captured inside execute_action as audit events

        Thread(target=_run_action, daemon=True).start()
        return {"status": "approved", "queued": True, "approval_id": approval_id, "decision_id": decision_id}
    else:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE approval_requests SET status = 'approved', resolved_at = ?, resolved_by = ? WHERE id = ?",
            (now, resolved_by, approval_id),
        )
        conn.commit()
        return {"status": "approved", "type": row["type"]}


@router.post("/{approval_id}/reject")
def reject(approval_id: int, body: ApprovalAction):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE approval_requests SET status = 'rejected', resolved_at = ?, resolved_by = ?, reason = ? WHERE id = ?",
        (now, body.resolved_by, body.reason, approval_id),
    )
    conn.commit()
    return {"status": "rejected", "approval_id": approval_id}
