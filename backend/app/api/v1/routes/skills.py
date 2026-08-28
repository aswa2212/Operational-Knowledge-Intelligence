"""
skills.py — Skills file management routes.

GET  /skills                  → list all skill versions
GET  /skills/{process}        → active skill version YAML
POST /skills/build            → build new skill version for a process
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.db.connection import get_db

router = APIRouter(prefix="/skills", tags=["Skills"])


class BuildRequest(BaseModel):
    process: str


@router.get("")
def list_skill_versions(process: str | None = Query(None)):
    conn = get_db()
    if process:
        rows = conn.execute(
            "SELECT * FROM skill_versions WHERE process = ? ORDER BY version DESC", (process,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM skill_versions ORDER BY generated_at DESC").fetchall()
    return [dict(r) for r in rows]


@router.get("/{process}")
def get_active_skill(process: str):
    conn = get_db()
    from app.core.services.build_skills import get_active_skills
    skills = get_active_skills(conn, process)
    if not skills:
        raise HTTPException(status_code=404, detail=f"No active skill version for process '{process}'")
    return skills


@router.post("/build", status_code=201)
def build_skill(body: BuildRequest):
    conn = get_db()
    from app.core.services.build_skills import build_skills_file
    return build_skills_file(conn, body.process)
