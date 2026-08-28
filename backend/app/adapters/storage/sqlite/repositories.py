"""
repositories.py

Plain repository FUNCTIONS (not a class hierarchy) for reading/writing
the 9 tables. Every function takes a sqlite3.Connection as its first
argument. This is the boundary that makes the future Postgres swap a
function-body change, not a caller change — nothing outside this file
should ever write raw SQL against these tables.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "db" / "schema.sql"


def get_connection(db_path: str = "oki.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn) -> None:
    from app.db.connection import _is_postgres
    if _is_postgres:
        schema_file = Path(__file__).parent.parent.parent.parent / "db" / "postgres_schema.sql"
    else:
        schema_file = SCHEMA_PATH

    if schema_file.exists():
        with open(schema_file, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- sources -------------------------------------------------------------

def insert_source(conn: sqlite3.Connection, type_: str, name: str, config: dict) -> int:
    cur = conn.execute(
        "INSERT INTO sources (type, name, config_json, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
        (type_, name, json.dumps(config), _now()),
    )
    conn.commit()
    return cur.lastrowid


# --- documents -------------------------------------------------------------

def insert_document(conn: sqlite3.Connection, source_id: int | None, doc: dict) -> int:
    cur = conn.execute(
        """INSERT INTO documents
           (source_id, external_id, source_type, author_handle, channel_or_space,
            timestamp, title, text, url, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            source_id, doc.get("external_id"), doc["source_type"], doc.get("author_handle"),
            doc.get("channel_or_space"), doc["timestamp"], doc.get("title"), doc["text"],
            doc.get("url"), json.dumps(doc.get("metadata", {})),
        ),
    )
    conn.commit()
    return cur.lastrowid


# --- resolved_rules --------------------------------------------------------

def list_rules(conn: sqlite3.Connection, process: str, status: str = "active") -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM resolved_rules WHERE process = ? AND status = ? ORDER BY version DESC",
        (process, status),
    ).fetchall()


def insert_resolved_rule(conn: sqlite3.Connection, rule: dict) -> int:
    cur = conn.execute(
        """INSERT INTO resolved_rules
           (process, trigger_text, conditions_json, action, exceptions_json,
            temporal_scope, status, score, provenance_json, version, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            rule["process"], rule.get("trigger_text"), json.dumps(rule.get("conditions", {})),
            rule.get("action"), json.dumps(rule.get("exceptions", [])), rule.get("temporal_scope", "unclear"),
            rule.get("status", "active"), rule.get("score"), json.dumps(rule.get("provenance", {})),
            rule.get("version", 1), _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


# --- cases / decisions -------------------------------------------------------

def insert_case(conn: sqlite3.Connection, process: str, source: str, payload: dict) -> int:
    cur = conn.execute(
        "INSERT INTO cases (process, source, payload_json, status, created_at) VALUES (?, ?, ?, 'new', ?)",
        (process, source, json.dumps(payload), _now()),
    )
    conn.commit()
    return cur.lastrowid


def insert_decision(conn: sqlite3.Connection, decision: dict) -> int:
    cur = conn.execute(
        """INSERT INTO decisions
           (case_id, skill_version_id, decision, confidence, matched_rule_id,
            risk_level, escalated, reason, trace_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            decision["case_id"], decision.get("skill_version_id"), decision.get("decision"),
            decision.get("confidence"), decision.get("matched_rule_id"), decision.get("risk_level"),
            int(decision.get("escalated", False)), decision.get("reason"),
            json.dumps(decision.get("trace", {})), _now(),
        ),
    )
    conn.commit()
    return cur.lastrowid


# --- approval_requests --------------------------------------------------------

def insert_approval_request(conn: sqlite3.Connection, decision_id: int, type_: str, requested_action: dict, reason: str) -> int:
    cur = conn.execute(
        """INSERT INTO approval_requests
           (decision_id, type, status, requested_action_json, reason, requested_at)
           VALUES (?, ?, 'pending', ?, ?, ?)""",
        (decision_id, type_, json.dumps(requested_action), reason, _now()),
    )
    conn.commit()
    return cur.lastrowid


def list_pending_approvals(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM approval_requests WHERE status = 'pending'").fetchall()


def resolve_approval(conn: sqlite3.Connection, approval_id: int, status: str, resolved_by: str) -> None:
    conn.execute(
        "UPDATE approval_requests SET status = ?, resolved_at = ?, resolved_by = ? WHERE id = ?",
        (status, _now(), resolved_by, approval_id),
    )
    conn.commit()


# --- audit_events --------------------------------------------------------

def log_audit_event(conn: sqlite3.Connection, entity_type: str, entity_id: str, event_type: str, actor: str, payload: dict) -> int:
    cur = conn.execute(
        "INSERT INTO audit_events (entity_type, entity_id, event_type, actor, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (entity_type, entity_id, event_type, actor, json.dumps(payload), _now()),
    )
    conn.commit()
    return cur.lastrowid


# --- author_profiles -----------------------------------------------------

def upsert_author_profile(
    conn: sqlite3.Connection,
    handle: str,
    display_name: str | None = None,
    source_platform: str = "manual",
    job_title: str | None = None,
    inferred_role_tier: str = "staff",
    base_authority: float = 0.50,
    is_verified: int = 0,
    metadata: dict | None = None,
) -> int:
    existing = conn.execute("SELECT id, is_verified, base_authority FROM author_profiles WHERE handle = ?", (handle,)).fetchone()
    now = _now()
    meta_json = json.dumps(metadata or {})
    
    if existing:
        # Don't overwrite manually verified profiles with lower automatic scores
        if existing["is_verified"] and not is_verified:
            conn.execute(
                "UPDATE author_profiles SET display_name = COALESCE(?, display_name), updated_at = ? WHERE id = ?",
                (display_name, now, existing["id"])
            )
        else:
            conn.execute(
                """UPDATE author_profiles
                   SET display_name = COALESCE(?, display_name),
                       source_platform = ?,
                       job_title = COALESCE(?, job_title),
                       inferred_role_tier = ?,
                       base_authority = ?,
                       is_verified = ?,
                       metadata_json = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (display_name, source_platform, job_title, inferred_role_tier, base_authority, is_verified, meta_json, now, existing["id"])
            )
        conn.commit()
        return existing["id"]
    else:
        cur = conn.execute(
            """INSERT INTO author_profiles
               (handle, display_name, source_platform, job_title, inferred_role_tier, base_authority, is_verified, metadata_json, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (handle, display_name, source_platform, job_title, inferred_role_tier, base_authority, is_verified, meta_json, now)
        )
        conn.commit()
        return cur.lastrowid


def get_author_profile(conn: sqlite3.Connection, handle: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM author_profiles WHERE handle = ?", (handle,)).fetchone()


def list_author_profiles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM author_profiles ORDER BY base_authority DESC, updated_at DESC").fetchall()


def verify_author_profile(
    conn: sqlite3.Connection,
    author_id: int,
    inferred_role_tier: str,
    base_authority: float,
    job_title: str | None = None
) -> None:
    conn.execute(
        """UPDATE author_profiles
           SET inferred_role_tier = ?,
               base_authority = ?,
               job_title = COALESCE(?, job_title),
               is_verified = 1,
               updated_at = ?
           WHERE id = ?""",
        (inferred_role_tier, base_authority, job_title, _now(), author_id)
    )
    conn.commit()

