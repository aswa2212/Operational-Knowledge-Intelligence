"""reset_notion_cache.py — clears stale known_page_ids so next sync re-baselines with hashes."""
import sqlite3
import json

conn = sqlite3.connect("oki.db")
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT id, type, name, config_json FROM sources WHERE type='notion'").fetchall()
if not rows:
    print("No Notion sources found.")
else:
    for r in rows:
        cfg = json.loads(r["config_json"] or "{}")
        cache = cfg.get("known_page_ids", {})
        print(f"Source #{r['id']} ({r['name']}): clearing {len(cache)} cache entries, last_synced={cfg.get('last_synced_at','never')}")
        # Remove old cache so next sync re-fetches all pages fresh (new hash format)
        cfg.pop("known_page_ids", None)
        cfg.pop("last_synced_at", None)   # also reset so no timestamp filter interferes
        conn.execute("UPDATE sources SET config_json = ? WHERE id = ?", (json.dumps(cfg), r["id"]))

conn.commit()
conn.close()
print("Done — next auto-sync will re-baseline all Notion pages with content hashes.")
