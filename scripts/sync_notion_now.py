import sqlite3
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from app.core.services.sync_source import run_sync

conn = sqlite3.connect(str(_ROOT / "oki.db"))
conn.row_factory = sqlite3.Row

source = conn.execute("SELECT * FROM sources WHERE type = 'notion'").fetchone()
if source:
    res = run_sync(conn, dict(source))
    conn.commit()
    print("Notion Sync Result:", res)

    doc = conn.execute("SELECT id, external_id, source_type, text FROM documents WHERE source_type = 'policy_doc' AND external_id LIKE '%notion%'").fetchone()
    if doc:
        print(f"\n[OK] Document #{doc['id']} Content in DB:")
        print(doc['text'])
