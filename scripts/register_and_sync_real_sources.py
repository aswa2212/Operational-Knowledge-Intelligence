"""
register_and_sync_real_sources.py

Registers the 3 real external connectors (GitHub, Notion, Slack) into oki.db
and runs an initial sync to ingest documents immediately.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.db.connection import get_db
from app.core.services.sync_source import run_sync

conn = get_db()

real_sources = [
    {
        "type": "github",
        "name": f"GitHub ({os.getenv('GITHUB_REPO', 'aswa2212/OKI')})",
        "config": {
            "repo": os.getenv("GITHUB_REPO", "aswa2212/OKI"),
            "process": "incident_triage",
        },
    },
    {
        "type": "notion",
        "name": "Notion Knowledge Base",
        "config": {
            "process": "refund_handling",
        },
    },
    {
        "type": "slack",
        "name": "Slack Workspace",
        "config": {
            "process": "pricing_exceptions",
        },
    },
]

now = datetime.now(timezone.utc).isoformat()

for s in real_sources:
    existing = conn.execute(
        "SELECT id FROM sources WHERE type = ?", (s["type"],)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO sources (type, name, config_json, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
            (s["type"], s["name"], json.dumps(s["config"]), now),
        )
        print(f"Registered real connector: {s['type']} - {s['name']}")
    else:
        conn.execute(
            "UPDATE sources SET name = ?, config_json = ?, enabled = 1 WHERE id = ?",
            (s["name"], json.dumps(s["config"]), existing["id"]),
        )
        print(f"Updated connector: {s['type']} - {s['name']}")

conn.commit()

print("\n--- Running Sync for Real Connectors ---")
sources = conn.execute("SELECT * FROM sources WHERE enabled = 1").fetchall()
for s in sources:
    s_dict = dict(s)
    try:
        res = run_sync(conn, s_dict)
        print(f"Synced {s_dict['type']} ({s_dict['name']}): {res.get('inserted', 0)} documents.")
    except Exception as e:
        print(f"Sync note for {s_dict['name']}: {e}")

# Check total documents in DB
doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
print(f"\nTotal documents in DB: {doc_count}")

# Verify sources table
all_sources = conn.execute("SELECT id, type, name, enabled FROM sources").fetchall()
print("\nAll registered sources in DB:")
for r in all_sources:
    print(f"  ID {r['id']}: [{r['type'].upper()}] {r['name']} (enabled={r['enabled']})")
