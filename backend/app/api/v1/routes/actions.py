"""
actions.py — Action execution history.

GET /actions      → list all action executions (from audit_events)
GET /actions/{id} → get action with before/after state
"""

import json
from fastapi import APIRouter, Query
from app.db.connection import get_db

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.get("")
def list_actions(limit: int = Query(100, le=500)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_events WHERE entity_type = 'action' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    results = []
    for r in rows:
        row_dict = dict(r)
        row_dict["payload"] = json.loads(row_dict.get("payload_json") or "{}")
        results.append(row_dict)
    return results


@router.get("/{event_id}")
def get_action(event_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM audit_events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Action not found")
    r = dict(row)
    r["payload"] = json.loads(r.get("payload_json") or "{}")
    return r
