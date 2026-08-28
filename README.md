# Operational Knowledge Intelligence (OKI)

Folder structure follows Section 22 of the consolidated report. Heavy
infra (Postgres, SQLAlchemy, Alembic, Celery) is intentionally NOT
included yet — see the Upgrade Path in the Master MVP Report for when
to add each piece.

## What's working right now (tested, 8/8 passing)

- `backend/app/core/domain/entities.py` — Pydantic schema for every artifact
- `backend/app/core/domain/authority_scoring.py` — heuristic authority inference (Bucket B, versioned code not YAML)
- `backend/app/core/domain/risk.py` — risk classification matrix (Bucket B)
- `backend/app/core/domain/resolver.py` — weighted conflict resolution + 3 naive ablation variants + confidence formula
- `backend/app/adapters/connectors/` — SourceConnector interface + working synthetic connector
- `backend/app/adapters/llm/` — Groq/Ollama provider interface + factory
- `backend/app/adapters/tools/` — Tool interface + registry + working mock refund tool (real before/after state change) + GitHub/Notion/Slack tool stubs (real signatures, need API tokens to actually call out)
- `backend/app/adapters/storage/sqlite/repositories.py` — plain repository functions for all 9 tables
- `backend/app/db/schema.sql` — the 9-table schema
- `backend/app/config/config.yaml` + `loader.py` — operational knobs ONLY (thresholds, weights-as-numbers, allowed tools) — the heuristic logic that uses them lives in code, not here

## What's not built yet

- `backend/app/core/services/` — the use-case orchestration functions (sync_source, extract_rules, resolve_conflicts, build_skills, decide_case, execute_action) — these wire together what already exists
- `backend/app/api/` — FastAPI routes
- `backend/app/adapters/retrieval/` — TF-IDF baseline retriever
- `backend/app/evaluation/` — evaluation harness
- `frontend/` — React dashboard
- Real GitHub/Notion/Slack connector `.extract()` implementations (tool call signatures exist; the connector `.extract()` methods that pull real data don't yet)

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY at minimum
python scripts/init_db.py
cd backend && pytest tests/ -v   # should show 8 passed
```

## Build order (matches the phased plan in the master report)

1. ✅ Contracts and skeleton (this scaffold)
2. Storage and domain core — mostly done; add `core/services/` next
3. Synthetic test harness — connector done, need extraction/resolution wired to it
4. Real connector #1: GitHub — tool signatures done, need `.extract()` implementation
5. Real connector #2: Notion
6. Real connector #3: Slack
7. Agent orchestrator (ties risk.py + resolver.py + tool registry together)
8. Dashboard (React)
9. Evaluation and hardening

## Design rule to preserve

Every external dependency (LLM, connector, storage, tool) sits behind
the interfaces in `adapters/`. Nothing in `core/domain/` imports
`httpx`, `sqlite3`, or a specific LLM SDK — that's what keeps the
Postgres/Celery/etc. upgrade path a swap instead of a rewrite.
