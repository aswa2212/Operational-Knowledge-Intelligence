"""
authors.py — Author Directory & Role Verification API.

GET  /authors              → List all detected and verified authors with their authority levels
GET  /authors/{handle}     → Get specific author profile
POST /authors              → Add or update an author profile
PUT  /authors/{id}/verify  → Set/override verified role tier and base authority score
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from app.db.connection import get_db
from app.adapters.storage.sqlite.repositories import (
    upsert_author_profile,
    get_author_profile,
    list_author_profiles,
    verify_author_profile,
    log_audit_event,
)
from app.core.domain.authority_scoring import classify_title_tier, ROLE_TIER_SCORES

router = APIRouter(prefix="/authors", tags=["Authors & Authority"])


class AuthorUpsertRequest(BaseModel):
    handle: str
    display_name: Optional[str] = None
    source_platform: str = "manual"
    job_title: Optional[str] = None
    inferred_role_tier: Optional[str] = None
    base_authority: Optional[float] = None
    is_verified: bool = False


class AuthorVerifyRequest(BaseModel):
    inferred_role_tier: str = Field(..., description="executive | manager | senior | staff | guest")
    base_authority: float = Field(..., ge=0.0, le=1.0)
    job_title: Optional[str] = None


@router.get("")
def list_authors(
    platform: Optional[str] = Query(None),
    verified_only: bool = Query(False),
):
    """
    List all detected and verified authors in the OKI knowledge directory.
    """
    conn = get_db()
    
    # Ensure table exists
    conn.execute(
        """CREATE TABLE IF NOT EXISTS author_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT UNIQUE NOT NULL,
            display_name TEXT,
            source_platform TEXT,
            job_title TEXT,
            inferred_role_tier TEXT,
            base_authority REAL NOT NULL,
            is_verified INTEGER DEFAULT 0,
            metadata_json TEXT,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.commit()

    rows = list_author_profiles(conn)
    result = []
    for r in rows:
        d = dict(r)
        if platform and d.get("source_platform") != platform:
            continue
        if verified_only and not d.get("is_verified"):
            continue
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        result.append(d)
    return result


@router.get("/{handle}")
def get_author(handle: str):
    conn = get_db()
    row = get_author_profile(conn, handle)
    if not row:
        raise HTTPException(status_code=404, detail=f"Author '{handle}' not found")
    d = dict(row)
    try:
        d["metadata"] = json.loads(d.get("metadata_json") or "{}")
    except Exception:
        d["metadata"] = {}
    return d


@router.post("")
def create_or_update_author(req: AuthorUpsertRequest):
    conn = get_db()
    
    # If role_tier not provided, infer from title
    tier = req.inferred_role_tier
    score = req.base_authority
    if not tier or score is None:
        inferred_t, inferred_s, _ = classify_title_tier(req.job_title)
        tier = tier or inferred_t
        score = score if score is not None else inferred_s

    auth_id = upsert_author_profile(
        conn,
        handle=req.handle,
        display_name=req.display_name or req.handle,
        source_platform=req.source_platform,
        job_title=req.job_title,
        inferred_role_tier=tier,
        base_authority=score,
        is_verified=1 if req.is_verified else 0,
    )
    return {"id": auth_id, "handle": req.handle, "inferred_role_tier": tier, "base_authority": score}


@router.put("/{author_id}/verify")
def verify_author(author_id: int, req: AuthorVerifyRequest):
    """
    Manually confirm or override an author's verified role tier and authority score.
    """
    conn = get_db()
    row = conn.execute("SELECT * FROM author_profiles WHERE id = ?", (author_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Author ID {author_id} not found")

    verify_author_profile(
        conn,
        author_id=author_id,
        inferred_role_tier=req.inferred_role_tier,
        base_authority=req.base_authority,
        job_title=req.job_title,
    )

    log_audit_event(
        conn,
        entity_type="author_profile",
        entity_id=str(author_id),
        event_type="author_verified",
        actor="supervisor",
        payload={
            "handle": row["handle"],
            "previous_authority": row["base_authority"],
            "new_authority": req.base_authority,
            "new_role_tier": req.inferred_role_tier,
        },
    )

    return {
        "status": "success",
        "author_id": author_id,
        "handle": row["handle"],
        "is_verified": True,
        "inferred_role_tier": req.inferred_role_tier,
        "base_authority": req.base_authority,
    }
