"""
conflicts.py — Knowledge conflict review routes.

GET  /conflicts         → list unresolved (or all) conflicts
GET  /conflicts/{id}    → conflict detail
POST /conflicts/{id}/resolve → human picks resolution
POST /conflicts/resolve-run  → run the automated resolver for a process
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.connection import get_db

router = APIRouter(prefix="/conflicts", tags=["Conflicts"])


class ResolveRequest(BaseModel):
    resolution_note: str
    winning_rule_id: int | None = None
    resolved_by: str = "human"


@router.get("")
def list_conflicts(process: str | None = Query(None), status: str = "conflict_unresolved"):
    conn = get_db()
    filters, params = ["rr.status = ?"], [status]
    if process:
        filters.append("rr.process = ?"); params.append(process)
    where = "WHERE " + " AND ".join(filters)
    rows = conn.execute(
        f"SELECT rr.*, ap.id as approval_id, ap.status as approval_status "
        f"FROM resolved_rules rr "
        f"LEFT JOIN approval_requests ap ON ap.requested_action_json LIKE '%\"resolved_rule_id\": ' || rr.id || '%' "
        f"{where} ORDER BY rr.created_at DESC",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{rule_id}")
def get_conflict(rule_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM resolved_rules WHERE id = ?", (rule_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Conflict not found")
    r = dict(row)
    provenance = json.loads(r.get("provenance_json") or "{}")
    competing_ids = provenance.get("competing", [])
    competing = []
    for cid in competing_ids:
        c = conn.execute("SELECT * FROM candidate_rules WHERE id = ?", (cid,)).fetchone()
        if c:
            competing.append(dict(c))
    r["competing_rules"] = competing
    return r


@router.post("/{rule_id}/resolve")
def resolve_conflict(rule_id: int, body: ResolveRequest):
    conn = get_db()
    row = conn.execute("SELECT * FROM resolved_rules WHERE id = ?", (rule_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE resolved_rules SET status = 'active', score = 0.80 WHERE id = ?",
        (rule_id,),
    )
    conn.execute(
        "UPDATE approval_requests SET status = 'approved', resolved_at = ?, resolved_by = ? "
        "WHERE requested_action_json LIKE '%\"resolved_rule_id\": ' || ? || '%'",
        (now, body.resolved_by, rule_id),
    )
    conn.commit()
    return {"status": "resolved", "rule_id": rule_id, "note": body.resolution_note}


class ResolveRunRequest(BaseModel):
    process: str


@router.post("/resolve-run")
def run_resolver(body: ResolveRunRequest):
    conn = get_db()
    from app.core.services.resolve_conflicts import run_conflict_resolution
    return run_conflict_resolution(conn, body.process)

