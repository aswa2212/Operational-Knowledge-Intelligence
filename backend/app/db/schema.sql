-- schema.sql
-- The 9-table MVP schema. Run once via scripts/init_db.py.
-- These are plain SQL tables read/written by repository FUNCTIONS in
-- adapters/storage/sqlite/ — no ORM class hierarchy for the MVP.

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,             -- github | notion | slack | synthetic
    name TEXT NOT NULL,
    config_json TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    external_id TEXT,
    source_type TEXT NOT NULL,
    author_handle TEXT,
    channel_or_space TEXT,
    timestamp TEXT NOT NULL,
    title TEXT,
    text TEXT NOT NULL,
    url TEXT,
    metadata_json TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS candidate_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process TEXT NOT NULL,
    trigger_text TEXT,
    conditions_json TEXT,
    action TEXT,
    exceptions_json TEXT,
    temporal_scope TEXT,             -- permanent | temporary | unclear
    source_document_ids_json TEXT,
    authority_score REAL,
    confidence REAL,
    raw_quote TEXT,
    extraction_method TEXT,          -- two_pass | single_pass
    status TEXT DEFAULT 'candidate'
);

CREATE TABLE IF NOT EXISTS resolved_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process TEXT NOT NULL,
    trigger_text TEXT,
    conditions_json TEXT,
    action TEXT,
    exceptions_json TEXT,
    temporal_scope TEXT,
    status TEXT DEFAULT 'active',    -- active | superseded | conflict_unresolved | stale | deprecated
    score REAL,
    provenance_json TEXT,
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT DEFAULT 'active',
    generated_at TEXT NOT NULL,
    artifact_path TEXT
);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process TEXT NOT NULL,
    source TEXT,                      -- dashboard | api | github_issue
    payload_json TEXT NOT NULL,
    status TEXT DEFAULT 'new',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    skill_version_id INTEGER,
    decision TEXT,
    confidence REAL,
    matched_rule_id INTEGER,
    risk_level TEXT,                  -- low | medium | high
    escalated INTEGER DEFAULT 0,
    reason TEXT,
    trace_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id)
);

CREATE TABLE IF NOT EXISTS approval_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER,
    type TEXT NOT NULL,               -- knowledge | action
    status TEXT DEFAULT 'pending',    -- pending | approved | rejected
    requested_action_json TEXT,
    reason TEXT,
    requested_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,        -- sync | extraction | decision | approval | action
    entity_id TEXT,
    event_type TEXT NOT NULL,
    actor TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS author_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    handle TEXT UNIQUE NOT NULL,       -- e.g. "aswa2212", "U04XXXX", "aswaj@company.com"
    display_name TEXT,
    source_platform TEXT,              -- slack | github | notion | manual
    job_title TEXT,                    -- "VP of Operations", "Support Lead"
    inferred_role_tier TEXT,           -- executive | manager | senior | staff | guest
    base_authority REAL NOT NULL,      -- 0.0 to 1.0
    is_verified INTEGER DEFAULT 0,     -- 1 if manually confirmed or verified admin
    metadata_json TEXT,
    updated_at TEXT NOT NULL
);

-- Performance indexes for hot query paths
CREATE INDEX IF NOT EXISTS idx_audit_events_entity_type ON audit_events(entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_created_at  ON audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_decisions_case_id        ON decisions(case_id);

