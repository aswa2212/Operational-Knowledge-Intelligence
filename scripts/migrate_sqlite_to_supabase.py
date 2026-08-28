"""
migrate_sqlite_to_supabase.py

Migrates OKI database from SQLite (oki.db) to Supabase PostgreSQL.
1. Creates PostgreSQL tables & indexes.
2. Migrates all data cleanly with sequence alignment.
"""

import os
import sys
import json
import sqlite3
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

import psycopg2
from psycopg2.extras import RealDictCursor

SUPABASE_URL = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL")
if not SUPABASE_URL or not (SUPABASE_URL.startswith("postgres://") or SUPABASE_URL.startswith("postgresql://")):
    password = urllib.parse.quote("Aswajith@001")
    SUPABASE_URL = f"postgresql://postgres.cwrqoavdywqbudnkqiba:{password}@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"

print("=" * 70)
print("MIGRATING OKI FROM SQLITE TO SUPABASE POSTGRESQL")
print("=" * 70)
print(f"Connecting to Supabase PostgreSQL...")

pg_conn = psycopg2.connect(SUPABASE_URL)
pg_cur = pg_conn.cursor()

# 1. Apply Schema
schema_path = Path(__file__).parent.parent / "backend" / "app" / "db" / "postgres_schema.sql"
with open(schema_path, "r", encoding="utf-8") as f:
    schema_sql = f.read()

print("\n[1] Applying PostgreSQL Schema to Supabase...")
pg_cur.execute(schema_sql)
pg_conn.commit()
print("  [OK] Schema and indexes created.")

# 2. Connect to SQLite
sqlite_path = Path(__file__).parent.parent / "oki.db"
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row

TABLES_IN_ORDER = [
    ("sources", ["id", "type", "name", "config_json", "enabled", "created_at"]),
    ("documents", ["id", "source_id", "external_id", "source_type", "author_handle", "channel_or_space", "timestamp", "title", "text", "url", "metadata_json"]),
    ("candidate_rules", ["id", "process", "trigger_text", "conditions_json", "action", "exceptions_json", "temporal_scope", "source_document_ids_json", "authority_score", "confidence", "raw_quote", "extraction_method", "status"]),
    ("resolved_rules", ["id", "process", "trigger_text", "conditions_json", "action", "exceptions_json", "temporal_scope", "status", "score", "provenance_json", "version", "created_at"]),
    ("skill_versions", ["id", "process", "version", "status", "generated_at", "artifact_path"]),
    ("cases", ["id", "process", "source", "payload_json", "status", "created_at"]),
    ("decisions", ["id", "case_id", "skill_version_id", "decision", "confidence", "matched_rule_id", "risk_level", "escalated", "reason", "trace_json", "created_at"]),
    ("approval_requests", ["id", "decision_id", "type", "status", "requested_action_json", "reason", "summary_card_json", "case_fields_json", "requested_at", "resolved_at", "resolved_by"]),
    ("audit_events", ["id", "entity_type", "entity_id", "event_type", "actor", "payload_json", "created_at"]),
    ("author_profiles", ["id", "handle", "display_name", "source_platform", "job_title", "inferred_role_tier", "base_authority", "is_verified", "metadata_json", "updated_at"]),
]

print("\n[2] Migrating Data from SQLite to Supabase...")

for table, cols in TABLES_IN_ORDER:
    # Check if table exists in SQLite
    chk = sqlite_conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()
    if not chk:
        print(f"  - Table {table}: not in SQLite, skipping.")
        continue

    # Get actual columns present in SQLite table
    pragma_cols = [col[1] for col in sqlite_conn.execute(f"PRAGMA table_info({table})").fetchall()]
    valid_cols = [c for c in cols if c in pragma_cols]

    rows = sqlite_conn.execute(f"SELECT {', '.join(valid_cols)} FROM {table}").fetchall()
    if not rows:
        print(f"  - Table {table}: 0 rows.")
        continue

    # Clean existing in Supabase
    pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
    
    col_str = ", ".join(valid_cols)
    val_placeholders = ", ".join(["%s"] * len(valid_cols))
    insert_sql = f"INSERT INTO {table} ({col_str}) VALUES ({val_placeholders})"

    data_to_insert = [tuple(r[c] for c in valid_cols) for r in rows]
    pg_cur.executemany(insert_sql, data_to_insert)
    pg_conn.commit()

    # Reset sequence to max ID
    pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table};")
    pg_conn.commit()

    print(f"  [OK] {table:20s}: {len(rows)} rows migrated and sequence aligned.")

print("\n[3] Verifying Supabase Tables...")
for table, _ in TABLES_IN_ORDER:
    pg_cur.execute(f"SELECT COUNT(*) FROM {table};")
    cnt = pg_cur.fetchone()[0]
    print(f"  - {table:20s}: {cnt} rows in Supabase")

pg_conn.close()
sqlite_conn.close()

print("\n" + "=" * 70)
print("MIGRATION TO SUPABASE POSTGRESQL COMPLETE!")
print("=" * 70)
