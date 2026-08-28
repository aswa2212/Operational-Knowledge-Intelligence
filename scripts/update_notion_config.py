import sqlite3
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "backend"))

conn = sqlite3.connect(str(_ROOT / "oki.db"))
conn.row_factory = sqlite3.Row

source = conn.execute("SELECT * FROM sources WHERE type = 'notion'").fetchone()
if source:
    cfg = json.loads(source["config_json"] or "{}")
    cfg["page_ids"] = "3c6112b959ae80038a5eeba43d6a6a24"
    conn.execute(
        "UPDATE sources SET config_json = ? WHERE id = ?",
        (json.dumps(cfg), source["id"])
    )
    conn.commit()
    print("Updated Notion source config to direct page ID mode:", cfg)
