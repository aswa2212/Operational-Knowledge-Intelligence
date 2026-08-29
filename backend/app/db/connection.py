"""
db/connection.py

Universal DB connection helper supporting both:
1. Supabase PostgreSQL (when DATABASE_URL starts with postgresql:// or postgres://)
2. SQLite (local fallback)
"""

from __future__ import annotations

import os
import re
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Any

_ROOT_DIR = Path(__file__).parent.parent.parent.parent
_raw_db = os.getenv("DATABASE_URL", "oki.db")

_connection: Any = None
_is_postgres = False


def _get_pg_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return url
    # Fallback to Supabase credentials if configured
    password = urllib.parse.quote(os.getenv("SUPABASE_DB_PASSWORD", "Aswajith@001"))
    return f"postgresql://postgres.cwrqoavdywqbudnkqiba:{password}@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"


class PgCursorWrapper:
    def __init__(self, cur, conn):
        self._cur = cur
        self._conn = conn
        self.lastrowid = None

    def execute(self, query: str, params: tuple | list | None = None):
        # Escape any literal % when params are used, then convert SQLite ? placeholders to PostgreSQL %s
        if params is not None:
            escaped_query = query.replace('%', '%%')
            converted_query = re.sub(r'(?<!\?)\?(?!\?)', '%s', escaped_query)
        else:
            converted_query = re.sub(r'(?<!\?)\?(?!\?)', '%s', query)
        
        # If INSERT statement without RETURNING, append RETURNING id to capture lastrowid
        is_insert = converted_query.strip().upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in converted_query.upper()
        
        if is_insert and not has_returning and "ON CONFLICT" not in converted_query.upper():
            converted_query += " RETURNING id"

        try:
            if params is not None and len(params) > 0:
                self._cur.execute(converted_query, params)
            else:
                self._cur.execute(converted_query)

            if is_insert and not has_returning:
                try:
                    res = self._cur.fetchone()
                    if res:
                        self.lastrowid = res[0]
                except Exception:
                    pass
        except Exception:
            self._conn.rollback()
            raise

        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)


class PgConnectionWrapper:
    """Wraps psycopg2 connection to mimic sqlite3.Connection API used by repositories."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def execute(self, query: str, params: tuple | list | None = None):
        import psycopg2.extras
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        wrapper = PgCursorWrapper(cur, self._conn)
        return wrapper.execute(query, params)

    def executescript(self, script_str: str):
        # Apply PostgreSQL schema script
        with self._conn.cursor() as cur:
            cur.execute(script_str)
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_db():
    """Return (and lazily create) the active DB connection."""
    global _connection, _is_postgres

    db_url = os.getenv("DATABASE_URL", "")
    use_pg = db_url.startswith("postgresql://") or db_url.startswith("postgres://") or os.getenv("USE_SUPABASE", "true").lower() == "true"

    if _connection is None:
        if use_pg:
            import psycopg2
            pg_url = _get_pg_url()
            raw_conn = psycopg2.connect(pg_url)
            raw_conn.autocommit = False
            _connection = PgConnectionWrapper(raw_conn)
            _is_postgres = True
            print("[OKI DB] Connected to Supabase PostgreSQL.")
        else:
            _db_path_obj = Path(_raw_db)
            if not _db_path_obj.is_absolute():
                db_path = str((_ROOT_DIR / _db_path_obj).resolve())
            else:
                db_path = str(_db_path_obj.resolve())

            _connection = sqlite3.connect(db_path, check_same_thread=False)
            _connection.row_factory = sqlite3.Row
            _connection.execute("PRAGMA journal_mode=WAL")
            _connection.execute("PRAGMA foreign_keys=ON")
            _is_postgres = False
            print(f"[OKI DB] Connected to local SQLite: {db_path}")

    return _connection


def close_db() -> None:
    """Close connection on shutdown."""
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None
