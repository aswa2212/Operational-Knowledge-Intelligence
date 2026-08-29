"""
extraction.py — Rule extraction routes.

POST /extraction/run    → run extraction for a process
GET  /extraction/runs   → list extraction audit events
GET  /candidate-rules   → list candidate rules
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.connection import get_db

router = APIRouter(tags=["Extraction"])


class ExtractionRunRequest(BaseModel):
    process: str
    method: str = "two_pass"  # two_pass | single_pass | both


@router.post("/extraction/run")
def run_extraction(body: ExtractionRunRequest):
    conn = get_db()
    from app.db.json_compat import extract_json_path

    # Load documents for this process's synthetic/synced sources
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
        if proc == body.process or s_name == body.process or s_name == f"demo_{body.process}":
            docs_list.append(d_dict)

    if not docs_list:
        docs = conn.execute("SELECT * FROM documents ORDER BY timestamp DESC LIMIT 500").fetchall()
        docs_list = [dict(d) for d in docs]

    if not docs_list:
        raise HTTPException(status_code=400, detail="No documents found. Sync a source first.")

    # Deduplicate documents with identical source_type and external_id (e.g. across multiple syncs)
    seen = set()
    deduped_docs = []
    for d in docs_list:
        key = (d.get("source_type"), d.get("external_id") or d.get("title") or d.get("id"))
        if key not in seen:
            seen.add(key)
            deduped_docs.append(d)
    docs_list = deduped_docs

    from app.core.services.extract_rules import run_two_pass_extraction, run_single_pass_extraction

    results = {}
    try:
        if body.method in ("two_pass", "both"):
            results["two_pass"] = run_two_pass_extraction(conn, body.process, docs_list)
        if body.method in ("single_pass", "both"):
            results["single_pass"] = run_single_pass_extraction(conn, body.process, docs_list)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM extraction failed: {exc}. Check GROQ_API_KEY and GROQ_MODEL in .env"
        ) from exc

    return results



@router.get("/extraction/runs")
def list_extraction_runs(limit: int = Query(50, le=200)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_events WHERE entity_type = 'extraction' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/candidate-rules")
def list_candidate_rules(
    process: str | None = Query(None),
    status: str = "candidate",
    method: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    conn = get_db()
    filters, params = ["status = ?"], [status]
    if process:
        filters.append("process = ?"); params.append(process)
    if method:
        filters.append("extraction_method = ?"); params.append(method)
    where = "WHERE " + " AND ".join(filters)
    rows = conn.execute(
        f"SELECT * FROM candidate_rules {where} ORDER BY id DESC LIMIT ?",
        params + [limit],
    ).fetchall()
    return [dict(r) for r in rows]
