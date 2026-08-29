"""
main.py — OKI Backend Application Entry Point.

Usage:
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Docs: http://localhost:8000/api/v1/docs
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend package root is on sys.path so `app.*` imports work
# whether launched as `uvicorn main:app` from /backend or from the repo root.
_BACKEND_DIR = Path(__file__).parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv

# Try multiple candidate locations so the server boots correctly regardless
# of which directory uvicorn is invoked from.
_ENV_CANDIDATES = [
    Path(__file__).parent.parent / ".env",   # repo root  (uvicorn from OKI/)
    Path(__file__).parent / ".env",           # backend/   (uvicorn from backend/)
    Path.cwd() / ".env",                      # wherever cwd happens to be
]
_loaded = False
for _env_path in _ENV_CANDIDATES:
    if _env_path.exists():
        load_dotenv(_env_path, override=True)
        print(f"[OKI] Loaded .env from: {_env_path}")
        _loaded = True
        break
if not _loaded:
    print("[OKI] WARNING: No .env file found. Set GROQ_API_KEY etc. as environment variables.")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os

from app.api.v1 import api_router
from app.db.connection import get_db, close_db
from app.adapters.storage.sqlite.repositories import init_db
import app.adapters.tools  # noqa: F401 — triggers all register_tool() calls
from app.adapters.tools.base import TOOL_REGISTRY


def create_app() -> FastAPI:
    app = FastAPI(
        title="OKI — Operational Knowledge Intelligence",
        description=(
            "Ingests organisational knowledge from GitHub, Notion, and Slack, "
            "resolves contradictions into versioned executable rules, and drives "
            "an agent orchestrator that acts or escalates to humans."
        ),
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    raw_origins = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://localhost:3000,http://localhost:4173")
    allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    
    # Ensure default local development origins are always present
    for default_origin in ["http://localhost:5173", "http://localhost:3000", "http://localhost:4173", "http://127.0.0.1:5173"]:
        if default_origin not in allowed_origins:
            allowed_origins.append(default_origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Startup / Shutdown ────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup() -> None:
        conn = get_db()
        init_db(conn)
        print(f"[OKI] DB ready. Tools registered: {list(TOOL_REGISTRY.keys())}")
        from app.core.services.background_sync import start_auto_sync
        start_auto_sync()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        from app.core.services.background_sync import stop_auto_sync
        stop_auto_sync()
        close_db()


    # ── Health ────────────────────────────────────────────────────────────
    @app.get("/api/v1/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok", "service": "OKI", "version": "1.0.0"}

    @app.get("/", tags=["health"])
    async def root() -> dict:
        return {"service": "OKI", "docs": "/api/v1/docs", "health": "/api/v1/health"}

    return app


app = create_app()
