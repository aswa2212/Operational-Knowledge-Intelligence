"""
audit.py — Audit event timeline.

GET /audit → list all audit events, filterable by entity_type and date
"""

from fastapi import APIRouter, Query
from app.db.connection import get_db
import json

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
def list_audit_events(
    entity_type: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    conn = get_db()
    filters, params = [], []
    if entity_type:
        filters.append("entity_type = ?"); params.append(entity_type)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    rows = conn.execute(
        f"SELECT * FROM audit_events {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    results = []
    for r in rows:
        row_dict = dict(r)
        row_dict["payload"] = json.loads(row_dict.get("payload_json") or "{}")
        results.append(row_dict)
    return results
