"""
background_sync.py

Automatic background scheduler that periodically polls and syncs all enabled
external sources (GitHub, Notion, Slack, Synthetic) without requiring manual triggers.

Fixes vs v1/v2:
  - Strict pure ASCII logs (no unicode characters like arrows or checkmarks)
    to prevent Windows cp1252 charmap encoding crashes in background tasks.
  - Re-reads sources from DB each cycle so new sources or config changes are picked up.
  - Notion sources always synced regardless of last_synced_at (hash-based detection).
  - Separate per-source error isolation so one bad source doesn't skip the rest.
"""

from __future__ import annotations

import asyncio
import os
import traceback
from datetime import datetime, timezone
from app.db.connection import get_db
from app.core.services.sync_source import run_sync

_sync_task: asyncio.Task | None = None
_running: bool = False


async def auto_sync_worker(interval_seconds: int = 5) -> None:
    """Continuous background loop syncing all enabled sources."""
    global _running
    _running = True
    print(f"[OKI AutoSync] Worker started - polling every {interval_seconds}s")

    # Initial small delay so DB & server finish booting
    await asyncio.sleep(2)

    cycle = 0
    while _running:
        cycle += 1
        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        try:
            conn = get_db()
            sources = conn.execute("SELECT * FROM sources WHERE enabled = 1").fetchall()

            for s in sources:
                s_dict = dict(s)
                src_label = f"#{s_dict['id']} {s_dict['type']}({s_dict['name']})"
                try:
                    res = await asyncio.to_thread(run_sync, conn, s_dict)
                    inserted = res.get("inserted", 0)
                    updated = res.get("updated", 0)
                    total = res.get("total_extracted", 0)
                    if inserted > 0 or updated > 0:
                        print(
                            f"[OKI AutoSync] [{now}] SUCCESS {src_label}: "
                            f"+{inserted} new, ~{updated} updated "
                            f"(scanned {total} items)"
                        )
                except Exception as e:
                    print(f"[OKI AutoSync] [{now}] ERROR {src_label}: {e}")

        except Exception as e:
            print(f"[OKI AutoSync] Worker exception in cycle #{cycle}: {e}")

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break

    print("[OKI AutoSync] Worker stopped.")


def start_auto_sync(interval_seconds: int | None = None) -> None:
    """Start background sync task if not already running."""
    global _sync_task
    if _sync_task is not None and not _sync_task.done():
        return  # already running

    interval = interval_seconds or int(os.getenv("AUTO_SYNC_INTERVAL_SECONDS", "5"))
    print(f"[OKI AutoSync] Scheduling background sync every {interval}s")
    _sync_task = asyncio.create_task(auto_sync_worker(interval_seconds=interval))


def stop_auto_sync() -> None:
    """Cancel and stop the background sync task."""
    global _running, _sync_task
    _running = False
    if _sync_task is not None and not _sync_task.done():
        _sync_task.cancel()
        _sync_task = None
    print("[OKI AutoSync] Stop requested.")
