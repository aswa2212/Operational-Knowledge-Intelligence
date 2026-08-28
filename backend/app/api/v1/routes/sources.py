"""
sources.py — Source management routes.

GET  /sources           → list all sources
POST /sources           → register a new source
POST /sources/{id}/sync → trigger sync for one source
GET  /sources/{id}/sync-history → past sync audit events
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.connection import get_db

router = APIRouter(prefix="/sources", tags=["Sources"])


class SourceCreate(BaseModel):
    type: str  # synthetic | github | notion | slack
    name: str
    config: dict = {}


@router.get("")
def list_sources():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sources ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_source(body: SourceCreate):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO sources (type, name, config_json, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
        (body.type, body.name, json.dumps(body.config), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return {"id": cur.lastrowid, "name": body.name, "type": body.type}


class SourceSyncRequest(BaseModel):
    process: str | None = None
    source_id: int | None = None


@router.post("/sync")
def sync_source_by_process(body: SourceSyncRequest):
    conn = get_db()

    if body.source_id is not None:
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (body.source_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Source not found")
        source_dict = dict(row)
    elif body.process:
        sources = conn.execute("SELECT * FROM sources").fetchall()
        matched = None
        for s in sources:
            cfg = json.loads(s["config_json"] or "{}")
            if cfg.get("process") == body.process or s["name"] == f"demo_{body.process}" or s["name"] == body.process:
                matched = s
                break
        if not matched:
            cur = conn.execute(
                "INSERT INTO sources (type, name, config_json, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
                ("synthetic", f"demo_{body.process}", json.dumps({"process": body.process}), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            matched = conn.execute("SELECT * FROM sources WHERE id = ?", (cur.lastrowid,)).fetchone()
        source_dict = dict(matched)
    else:
        raise HTTPException(status_code=400, detail="Either 'process' or 'source_id' must be provided in request body")

    from app.core.services.sync_source import run_sync
    result = run_sync(conn, source_dict)
    return result


@router.post("/{source_id}/sync")
def sync_source(source_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Source not found")

    from app.core.services.sync_source import run_sync
    result = run_sync(conn, dict(row))
    return result


@router.get("/{source_id}/sync-history")
def sync_history(source_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_events WHERE entity_type = 'sync' AND entity_id = ? ORDER BY created_at DESC LIMIT 50",
        (str(source_id),),
    ).fetchall()
    return [dict(r) for r in rows]
