# OKI — Full Real-Product Implementation Plan

## What We're Building

**Operational Knowledge Intelligence (OKI)** — a bounded autonomous system that ingests scattered company knowledge from real apps (GitHub, Notion, Slack), resolves contradictions into versioned executable rules (skills), and uses those rules to drive an agent orchestrator that either acts automatically or asks a human for approval before executing.

This is not a demo. It is a real, modular product built to be upgraded without rewriting.

---

## Current State Assessment

The architectural skeleton is already correct and well-designed. What exists:

| Component | Status |
|---|---|
| Domain entities (`entities.py`) | ✅ Complete |
| Conflict resolver (`resolver.py`) | ✅ Complete |
| Authority scoring (`authority_scoring.py`) | ✅ Complete |
| Risk engine (`risk.py`) | ✅ Complete |
| Connector interface (`base.py`) | ✅ Complete |
| Synthetic connector (`synthetic_connector.py`) | ✅ Complete |
| LLM providers (Groq + Ollama) | ✅ Complete |
| Tool registry + interfaces (`base.py`) | ✅ Complete |
| GitHub tools | ✅ Complete |
| Slack/Notion/mock tools (signatures only) | ✅ Stubs present |
| SQLite repositories | ✅ Complete |
| DB schema (9 tables) | ✅ Complete |
| Config system | ✅ Complete |
| API scaffold (`/api/v1/`) | ⬜ Empty — no routes |
| Core services (use cases) | ⬜ Not written |
| GitHub connector | ⬜ Not written |
| Notion connector | ⬜ Not written |
| Slack connector | ⬜ Not written |
| Extraction service | ⬜ Not written |
| Skills builder service | ⬜ Not written |
| Agent orchestrator | ⬜ Not written |
| Retrieval layer (TF-IDF) | ⬜ Not written |
| Frontend | ⬜ Empty src/ |
| Synthetic data fixtures | ⬜ Not written |
| Prompts | ⬜ Not written |
| Tests | ⬜ Not written |

**Bottom line:** The foundation is solid. We now build everything on top of it systematically, in dependency order.

---

## Open Questions

> [!IMPORTANT]
> **LLM Provider**: Groq is wired for interactive use. Do you have a working `GROQ_API_KEY`? We can start with Groq and add Ollama fallback later, or start with Ollama if you prefer local-first.

> [!IMPORTANT]
> **Real App Credentials**: The full demo requires GitHub, Notion, and Slack credentials. These are built incrementally — Phases 4–6. For Phases 1–3 (the foundation), only the LLM key is needed. Do you want to set up the demo workspaces now or later?

> [!IMPORTANT]
> **Database**: Current schema is SQLite via raw repositories (no ORM). The design is upgrade-safe. We will keep SQLite but wire it correctly through the application. PostgreSQL migration is not in scope for MVP — the repository pattern makes it a later swap.

> [!IMPORTANT]
> **Frontend Framework**: The document recommends React + Vite + Tailwind. Since you specified React is needed for this complex dashboard, shall we use Vite + React + Tailwind (per your doc recommendation)? This is the one case where Tailwind makes sense given the scale.

---

## Proposed Changes

### Phase 1: Service Layer (Use Cases) — Backend Logic Core

This is the most critical phase. Services coordinate domain logic and adapters.

---

#### [NEW] `backend/app/core/services/sync_source.py`
Orchestrates connector → normalize → store pipeline. Accepts a `source_id` from the DB, looks up its config, instantiates the right connector, calls `.extract()`, stores `NormalizedDocument`s into `documents` table, logs a sync audit event.

#### [NEW] `backend/app/core/services/extract_rules.py`
Two-pass LLM extraction pipeline:
- **Pass 1**: LLM reads document text and identifies *candidate rule mentions* (raw quotes)
- **Pass 2**: LLM converts each raw quote into a structured `CandidateRule` with `trigger_text`, `conditions_json`, `action`, `temporal_scope`, `confidence`
- Stores `candidate_rules` rows
- Also runs single-pass baseline and stores separately for ablation comparison
- Uses versioned prompts from `app/prompts/`

#### [NEW] `backend/app/core/services/resolve_conflicts.py`
- Loads `candidate_rules` for a process
- Groups semantically similar rules (TF-IDF similarity + same action domain)
- For each conflict group, calls `resolve_conflict_weighted()` from domain resolver
- If winner found → insert into `resolved_rules` as `active`
- If no clear winner → insert `conflict_unresolved` row + create `approval_request` of type `knowledge`

#### [NEW] `backend/app/core/services/build_skills.py`
- Loads all `active` resolved rules for a process
- Constructs a `SkillsFile` Pydantic model
- Serializes to `skills_artifacts/<process>/v<N>.yaml`
- Inserts a `skill_versions` row
- Returns the version number

#### [NEW] `backend/app/core/services/decide_case.py`
The agent orchestrator service (pure decision logic, no tool calls):
1. Load case fields
2. Retrieve active skill version for the process
3. Rule matching: deterministic match first, fuzzy/LLM match if needed
4. Check for conflicts in active rules
5. Compute confidence (using `compute_confidence()` from resolver)
6. Call `classify_risk()` from domain risk module
7. Return `DecisionOutput` with: decision, matched_rule_id, confidence, risk_level, escalated flag, trace dict

#### [NEW] `backend/app/core/services/execute_action.py`
- Accepts a `decision_id` and `approval_id` (or None for auto-execute)
- Looks up the decision's proposed action
- Calls `get_tool(action_name)` from TOOL_REGISTRY
- Captures before-state
- Calls `tool.execute(args, ctx)`
- Captures after-state
- Inserts `action_executions` row
- Logs audit event

#### [NEW] `backend/app/core/services/evaluation.py`
- Loads evaluation fixtures from `data/fixtures/`
- Runs `decide_case` against the OKI agent (two-pass extraction + weighted resolution)
- Runs same fixtures against three baselines: most-recent-wins, authority-only, corroboration-only
- Runs against single-pass extraction baseline
- Computes: accuracy, coverage, escalation rate, conflict resolution rate
- Returns structured comparison results

---

### Phase 2: Real Connectors

#### [NEW] `backend/app/adapters/connectors/github_connector.py`
- Reads `GITHUB_TOKEN` and `GITHUB_REPO` from env
- `extract(since)` → calls GitHub REST API `/repos/{repo}/issues?state=all&since={since}`
- Paginates via `Link` header
- Normalizes each issue to `NormalizedDocument`:
  - `source_type = TICKET`
  - `author_handle = issue.user.login`
  - `channel_or_space = {repo}/issues`
  - `title = issue.title`
  - `text = issue.body + concatenated comments`
  - `url = issue.html_url`
  - `timestamp = issue.created_at`

#### [NEW] `backend/app/adapters/connectors/notion_connector.py`
- Reads `NOTION_TOKEN` from env
- Calls Notion API `/search` to list pages, then `/blocks/{id}/children` to get text
- Normalizes to `NormalizedDocument`:
  - `source_type = POLICY_DOC`
  - `channel_or_space = database/page title`

#### [NEW] `backend/app/adapters/connectors/slack_connector.py`
- Reads `SLACK_BOT_TOKEN` from env
- Calls Slack API `conversations.list` → `conversations.history` per channel
- Normalizes to `NormalizedDocument`:
  - `source_type = CHAT`
  - `channel_or_space = channel_name`
  - `author_handle = user.name`

---

### Phase 3: Retrieval Layer

#### [NEW] `backend/app/adapters/retrieval/tfidf_retriever.py`
- Implements `BaseRetriever` interface: `retrieve(query: str, docs: list[ResolvedRule], top_k: int) → list[ResolvedRule]`
- Uses scikit-learn `TfidfVectorizer` + cosine similarity
- Used by `decide_case.py` for fuzzy rule matching when deterministic match fails

#### [NEW] `backend/app/adapters/retrieval/base.py`
- Abstract `BaseRetriever` interface (so vector store can be swapped in later)

---

### Phase 4: Prompts

#### [NEW] `backend/app/prompts/extraction_two_pass_v1.py`
System + user prompt templates for pass-1 (identify mentions) and pass-2 (structure rules). Versioned — version string stored in extraction run logs.

#### [NEW] `backend/app/prompts/extraction_single_pass_v1.py`
Ablation baseline: single LLM call to extract all rules at once.

#### [NEW] `backend/app/prompts/decision_v1.py`
Prompt for fuzzy/LLM-assisted rule matching in `decide_case`.

#### [NEW] `backend/app/prompts/approval_summary_v1.py`
Prompt for generating a human-readable approval summary card.

---

### Phase 5: API Routes

All routes are thin — they receive request, call a service, return response. No business logic in routes.

#### [MODIFY] `backend/app/api/v1/routes/` — Add all route modules

**`sources.py`**
```
GET  /api/v1/sources           → list all sources
POST /api/v1/sources           → register a new source (type, name, config)
POST /api/v1/sources/{id}/sync → trigger sync for one source
GET  /api/v1/sources/{id}/sync-history → list past sync runs
```

**`documents.py`**
```
GET /api/v1/documents          → list documents (filterable by source, process)
GET /api/v1/documents/{id}     → get one document with full text
```

**`extraction.py`**
```
POST /api/v1/extraction/run    → run extraction on all/specific documents for a process
GET  /api/v1/extraction/runs   → list extraction runs
GET  /api/v1/candidate-rules   → list candidate rules (filterable by process, status)
```

**`conflicts.py`**
```
GET  /api/v1/conflicts         → list all unresolved conflicts
GET  /api/v1/conflicts/{id}    → get conflict detail with both rules and scores
POST /api/v1/conflicts/{id}/resolve → human picks rule A or B (knowledge approval)
```

**`skills.py`**
```
GET  /api/v1/skills            → list all skill versions across processes
GET  /api/v1/skills/{process}  → get active skill version for process
POST /api/v1/skills/build      → build/publish a new skill version for a process
```

**`cases.py`**
```
POST /api/v1/cases             → submit a new case
GET  /api/v1/cases             → list cases
GET  /api/v1/cases/{id}        → get case with decision trace
POST /api/v1/cases/{id}/decide → run agent orchestrator on this case
```

**`approvals.py`**
```
GET  /api/v1/approvals         → list pending approvals (knowledge + action types)
GET  /api/v1/approvals/{id}    → get approval detail
POST /api/v1/approvals/{id}/approve → approve (triggers tool execution for action type)
POST /api/v1/approvals/{id}/reject  → reject with reason
```

**`actions.py`**
```
GET /api/v1/actions            → list all action executions
GET /api/v1/actions/{id}       → get action with before/after state
```

**`evaluation.py`**
```
POST /api/v1/evaluation/run    → run evaluation suite
GET  /api/v1/evaluation/runs   → list past evaluation runs with results
```

**`audit.py`**
```
GET /api/v1/audit              → list audit events (filterable by entity_type, date)
```

#### [NEW] `backend/app/api/v1/schemas/` — Pydantic request/response schemas
One schema file per route group. Request schemas validate incoming data; response schemas ensure clean API contracts.

#### [MODIFY] `backend/app/api/v1/__init__.py` — Wire FastAPI app
Create `FastAPI` app, include all routers, configure CORS for frontend dev server.

---

### Phase 6: Synthetic Data Fixtures

#### [NEW] `data/synthetic/refund_handling/` — populate all 4 subdirs
Realistic messy documents: emails with conflicting refund policies, chat messages with temporary exceptions, tickets with escalation precedents, policy docs with formal rules.

#### [NEW] `data/synthetic/pricing_exceptions/` — populate
Discount approval threads, manager override messages, conflicting pricing rules.

#### [NEW] `data/synthetic/incident_triage/` — populate
GitHub-style incident reports, on-call escalation chats, severity classification precedents.

#### [NEW] `data/fixtures/` — evaluation test cases with ground-truth answers
JSON fixture files: `{case_input, expected_decision, expected_confidence_min, expected_escalated}`. Used by `evaluation.py` service.

---

### Phase 7: Frontend — React + Vite Dashboard

#### [NEW] `frontend/` — Full React + Vite + Tailwind app

**Pages / Feature Areas:**

| Page | Route | Purpose |
|---|---|---|
| Sources | `/sources` | List connected sources, trigger sync, view sync history |
| Documents | `/documents` | Browse ingested documents, search, view full text |
| Extraction | `/extraction` | Run extraction, view candidate rules per process |
| Skills Browser | `/skills` | View active skill versions, rules, flagged conflicts |
| Conflict Review | `/conflicts` | Review unresolved conflicts, side-by-side diff, approve winner |
| Approval Center | `/approvals` | Pending action approvals with proposed action + evidence |
| Cases | `/cases` | Submit cases, view case history |
| Case Runner | `/cases/new` | Interactive case form per process |
| Decision Trace | `/cases/{id}` | Full agent trace: rule matched, confidence, risk, actions taken |
| Evaluation | `/evaluation` | Run evaluation suite, view comparison charts |
| Audit Log | `/audit` | Timeline of all system events |

**Component Architecture:**
- `src/app/` — Router, layout, app shell
- `src/components/` — Shared UI: Button, Badge, Card, Table, Modal, Timeline, Diff viewer, JsonTree, ConfidenceBar
- `src/features/{feature}/` — Feature-specific components + API hooks
- `src/lib/api.ts` — Typed API client (fetch wrapper, all endpoints)
- `src/lib/queryClient.ts` — TanStack Query configuration

**Design system:** Dark mode, glassmorphism cards, animated transitions, Recharts for evaluation metrics.

---

### Phase 8: Additional Backend Files

#### [MODIFY] `backend/app/adapters/tools/slack_tools.py` — Complete real implementation
Currently stub. Wire real Slack `chat.postMessage` API call.

#### [MODIFY] `backend/app/adapters/tools/notion_tools.py` — Complete real implementation
Currently stub. Wire real Notion `pages.create` API call.

#### [MODIFY] `backend/app/adapters/tools/mock_payment_tools.py` — Complete mock ledger
Mock refund ledger stored in SQLite. Records payment state before/after.

#### [NEW] `backend/app/db/connection.py` — Connection management
Singleton connection pool helper. Reads `DATABASE_URL` from env (defaults to `oki.db`).

#### [MODIFY] `requirements.txt` — Add missing dependencies
Add: `groq`, `scikit-learn` (already present), `python-multipart`, `aiofiles`

#### [MODIFY] `.env.example` — Add missing env vars
Add: `DATABASE_URL`, `FRONTEND_ORIGIN`, `OKI_ENV` (development/production)

#### [NEW] `backend/main.py` — Application entry point
FastAPI app factory, startup event (init DB, register tools), uvicorn runner.

#### [NEW] `scripts/seed_sources.py` — Register demo sources in DB
Seeds the `sources` table with github/notion/slack/synthetic entries. Run once after `init_db.py`.

#### [NEW] `scripts/run_demo.py` — End-to-end demo script
Runs the three demo scenarios from the document: incident from GitHub, policy update conflict, case execution with approval.

---

### Phase 9: Tests

#### [NEW] `backend/tests/test_resolver.py` — Unit tests for conflict resolver
Tests for weighted scoring, margin checking, naïve ablations, sample-agreement formula.

#### [NEW] `backend/tests/test_authority_scoring.py` — Unit tests for authority inference
Tests for each source type, phrasing cues, temporal detection.

#### [NEW] `backend/tests/test_risk.py` — Unit tests for risk classification
Tests for refund thresholds, incident severity, pricing exceptions, fail-safe behavior.

#### [NEW] `backend/tests/test_extraction.py` — Integration tests for extraction service
Uses synthetic fixtures + mocked LLM responses.

#### [NEW] `backend/tests/test_decide_case.py` — Integration tests for agent orchestrator
Tests auto-execute path, approval path, escalation path.

---

## Verification Plan

### Automated Tests
```bash
cd backend
pytest tests/ -v
```

### Manual Verification Steps

1. **Backend health**: `GET /api/v1/health` returns `{"status": "ok"}`
2. **Synthetic sync**: POST sync on synthetic source → documents appear in `/documents`
3. **Extraction**: POST extraction run → candidate rules appear with correct process/status
4. **Conflict resolution**: Run resolver → conflicts go to `/conflicts` OR get auto-resolved into `resolved_rules`
5. **Skills build**: POST `/skills/build` → YAML artifact written to `skills_artifacts/`
6. **Case submission**: POST case → decision returned with trace
7. **Auto-execute path**: Low-risk case → action executed without approval, appears in `/actions`
8. **Approval path**: High-risk case → appears in `/approvals` as pending → approve → action executes
9. **Frontend**: All 10 pages render without console errors, data loads from API

### Demo Scenarios (from master document)
1. GitHub incident issue → agent triage → Sev-1 approval → label + comment + Slack notify
2. Notion policy + Slack override → conflict detection → human knowledge review → skills update
3. Refund case $450 outage-affected → temporary exception match → human approval → mock refund

---

## Build Order

```
Phase 1: DB connection + main.py + health endpoint           (1 day)
Phase 2: Core services (sync → extract → resolve → skills)   (3 days)
Phase 3: API routes (all 10 route groups)                    (2 days)
Phase 4: Real connectors (GitHub → Notion → Slack)           (2 days)
Phase 5: Retrieval layer + prompts                           (1 day)
Phase 6: Synthetic fixtures + evaluation fixtures            (1 day)
Phase 7: Frontend — all 10 pages + API client                (4 days)
Phase 8: Tool implementations (Slack/Notion/mock complete)   (1 day)
Phase 9: Tests + demo scripts                                (2 days)
```

Total: ~17 working days for complete MVP.

> [!NOTE]
> We can deliver a working demo earlier — after Phases 1–3 the backend is fully functional with synthetic data. After Phase 7 the full UI is working. Real connector demos (GitHub/Notion/Slack) come in Phase 4.
