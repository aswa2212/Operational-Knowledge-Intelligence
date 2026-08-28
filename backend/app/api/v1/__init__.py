"""
api/v1/__init__.py — Wire all routers into a single APIRouter.
main.py includes this with prefix="/api/v1".
"""

from fastapi import APIRouter

from app.api.v1.routes import (
    sources,
    documents,
    extraction,
    conflicts,
    skills,
    cases,
    approvals,
    actions,
    evaluation,
    audit,
    config,
    authors,
    demo,
)

api_router = APIRouter()

api_router.include_router(sources.router)
api_router.include_router(documents.router)
api_router.include_router(extraction.router)
api_router.include_router(conflicts.router)
api_router.include_router(skills.router)
api_router.include_router(cases.router)
api_router.include_router(approvals.router)
api_router.include_router(actions.router)
api_router.include_router(evaluation.router)
api_router.include_router(audit.router)
api_router.include_router(config.router)
api_router.include_router(authors.router)
api_router.include_router(demo.router)

