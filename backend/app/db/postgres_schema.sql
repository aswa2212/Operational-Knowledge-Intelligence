-- PostgreSQL Schema for OKI (Supabase)
-- Creates all 9 tables + author profiles + indexes

CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    config_json TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    external_id TEXT,
    source_type TEXT NOT NULL,
    author_handle TEXT,
    channel_or_space TEXT,
    timestamp TEXT NOT NULL,
    title TEXT,
    text TEXT NOT NULL,
    url TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS candidate_rules (
    id SERIAL PRIMARY KEY,
    process TEXT NOT NULL,
    trigger_text TEXT,
    conditions_json TEXT,
    action TEXT,
    exceptions_json TEXT,
    temporal_scope TEXT,
    source_document_ids_json TEXT,
    authority_score REAL,
    confidence REAL,
    raw_quote TEXT,
    extraction_method TEXT,
    status TEXT DEFAULT 'candidate'
);

CREATE TABLE IF NOT EXISTS resolved_rules (
    id SERIAL PRIMARY KEY,
    process TEXT NOT NULL,
    trigger_text TEXT,
    conditions_json TEXT,
    action TEXT,
    exceptions_json TEXT,
    temporal_scope TEXT,
    status TEXT DEFAULT 'active',
    score REAL,
    provenance_json TEXT,
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_versions (
    id SERIAL PRIMARY KEY,
    process TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT DEFAULT 'active',
    generated_at TEXT NOT NULL,
    artifact_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    id SERIAL PRIMARY KEY,
    process TEXT NOT NULL,
    source TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT DEFAULT 'new',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    skill_version_id INTEGER REFERENCES skill_versions(id) ON DELETE SET NULL,
    decision TEXT,
    confidence REAL,
    matched_rule_id INTEGER,
    risk_level TEXT,
    escalated INTEGER DEFAULT 0,
    reason TEXT,
    trace_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_requests (
    id SERIAL PRIMARY KEY,
    decision_id INTEGER REFERENCES decisions(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    requested_action_json TEXT,
    reason TEXT,
    summary_card_json TEXT,
    case_fields_json TEXT,
    requested_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS author_profiles (
    id SERIAL PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT,
    source_platform TEXT NOT NULL,
    job_title TEXT,
    inferred_role_tier TEXT DEFAULT 'staff',
    base_authority REAL DEFAULT 0.50,
    is_verified INTEGER DEFAULT 0,
    metadata_json TEXT,
    updated_at TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_timestamp ON documents(timestamp);
CREATE INDEX IF NOT EXISTS idx_candidate_rules_process ON candidate_rules(process);
CREATE INDEX IF NOT EXISTS idx_resolved_rules_process ON resolved_rules(process);
CREATE INDEX IF NOT EXISTS idx_cases_process ON cases(process);
CREATE INDEX IF NOT EXISTS idx_decisions_case_id ON decisions(case_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at);
