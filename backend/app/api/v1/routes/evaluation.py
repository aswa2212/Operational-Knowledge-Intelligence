"""
evaluation.py — Evaluation routes.

POST /evaluation/run  → run evaluation suite
GET  /evaluation/runs → list past evaluation audit events
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.db.connection import get_db

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class EvalRunRequest(BaseModel):
    fixture_file: str = "eval_cases.json"


@router.post("/run")
def run_evaluation(body: EvalRunRequest):
    conn = get_db()
    from app.core.services.evaluation import run_evaluation as _run
    return _run(conn, body.fixture_file)


@router.get("/runs")
def list_evaluation_runs(limit: int = 20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_events WHERE entity_type = 'evaluation' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
