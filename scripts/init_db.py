"""
init_db.py — run with: python scripts/init_db.py
Creates oki.db with the 9-table schema if it doesn't already exist.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.adapters.storage.sqlite.repositories import get_connection, init_db

if __name__ == "__main__":
    conn = get_connection("oki.db")
    init_db(conn)
    print("Initialized oki.db with the 9-table schema.")
    conn.close()
