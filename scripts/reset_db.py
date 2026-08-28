"""
reset_db.py — Clears all data from oki.db and re-creates clean tables.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "oki.db"
SCHEMA_PATH = Path(__file__).parent.parent / "backend" / "app" / "db" / "schema.sql"

def reset():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=OFF")
    
    tables = [
        "audit_events",
        "approval_requests",
        "decisions",
        "cases",
        "skill_versions",
        "resolved_rules",
        "candidate_rules",
        "documents",
        "sources"
    ]
    
    for t in tables:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
        print(f"  Dropped {t}")
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    
    conn.commit()
    conn.close()
    print("Database reset complete. All 9 tables are now empty.")

if __name__ == "__main__":
    reset()
