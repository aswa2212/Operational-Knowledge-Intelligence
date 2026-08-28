"""
sync_source.py

Orchestrates: connector → normalize → store.
Accepts a source row from the DB, instantiates the right connector,
calls extract(), stores NormalizedDocuments, and logs an audit event.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.adapters.storage.sqlite.repositories import (
    insert_document,
    log_audit_event,
)


def run_sync(conn, source_row: dict) -> dict:
    """
    Sync one source. Returns a summary dict.

    source_row keys: id, type, name, config_json
    """
    source_id = source_row["id"]
    source_type = source_row["type"]
    config = json.loads(source_row["config_json"] or "{}")

    connector = _get_connector(source_type, config)

    # For Notion we pass since=None — the connector uses its own content-hash
    # cache (known_page_ids) to detect changes so it doesn't rely on the
    # minute-rounded last_synced_at timestamp which misses same-minute edits.
    if source_type == "notion":
        docs = connector.extract(since=None)
    else:
        since = config.get("last_synced_at")
        since_dt = datetime.fromisoformat(since) if since else None
        docs = connector.extract(since=since_dt)

    inserted = 0
    updated = 0
    for doc in docs:
        ts_str = doc.timestamp.isoformat() if isinstance(doc.timestamp, datetime) else str(doc.timestamp)
        doc_meta = {"author_role": doc.author_role}
        if hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
            doc_meta.update(doc.metadata)
        meta_json = json.dumps(doc_meta)

        # Automatically learn / update author profile in org directory
        if doc.author and doc.author != "unknown":
            from app.core.domain.authority_scoring import classify_title_tier, evaluate_platform_metadata
            p_tier, p_score, _ = evaluate_platform_metadata(doc_meta)
            if p_score is None:
                p_tier, p_score, _ = classify_title_tier(doc.author_role)
            from app.adapters.storage.sqlite.repositories import upsert_author_profile
            upsert_author_profile(
                conn,
                handle=doc.author,
                display_name=doc.author,
                source_platform=doc.source_type.value,
                job_title=doc.author_role,
                inferred_role_tier=p_tier or "staff",
                base_authority=p_score or 0.50,
                is_verified=1 if doc_meta.get("is_owner") or doc_meta.get("author_association") == "OWNER" else 0,
                metadata=doc_meta,
            )

        # Check if this document already exists in OKI by external_id (globally or by source)
        existing = conn.execute(
            "SELECT id, text FROM documents WHERE external_id = ?",
            (doc.source_id,),
        ).fetchone()

        if existing:
            if existing["text"] != doc.content:
                conn.execute(
                    "UPDATE documents SET text = ?, timestamp = ?, metadata_json = ?, source_id = ? WHERE id = ?",
                    (doc.content, ts_str, meta_json, source_id, existing["id"]),
                )
                updated += 1

        else:
            insert_document(
                conn,
                source_id=source_id,
                doc={
                    "source_type": doc.source_type.value,
                    "author_handle": doc.author,
                    "channel_or_space": doc.thread_context,
                    "timestamp": ts_str,
                    "text": doc.content,
                    "external_id": doc.source_id,
                    "metadata": doc_meta,
                },
            )
            inserted += 1

    # ── Always persist Notion page cache so hash/ts state survives restarts ──
    # This must happen BEFORE updating last_synced_at so the next run
    # sees the correct cache regardless of whether any docs changed.
    if source_type == "notion" and hasattr(connector, "known_page_times"):
        # Merge rather than overwrite so pages not seen this run aren't lost
        existing_cache = config.get("known_page_ids") or {}
        existing_cache.update(connector.known_page_times)
        config["known_page_ids"] = existing_cache

    # Update last_synced_at in the source config
    config["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE sources SET config_json = ? WHERE id = ?",
        (json.dumps(config), source_id),
    )
    conn.commit()

    log_audit_event(
        conn,
        entity_type="sync",
        entity_id=str(source_id),
        event_type="sync_completed",
        actor="system",
        payload={"source_type": source_type, "inserted": inserted, "updated": updated, "total_extracted": len(docs)},
    )

    return {
        "source_id": source_id,
        "source_type": source_type,
        "inserted": inserted,
        "updated": updated,
        "total_extracted": len(docs),
    }



def _get_connector(source_type: str, config: dict):
    """Instantiate the right connector for this source type."""
    from pathlib import Path

    data_base = Path(__file__).parent.parent.parent.parent.parent / "data" / "synthetic"

    if source_type == "synthetic":
        process = config.get("process", "refund_handling")
        from app.adapters.connectors.synthetic_connector import load_all_sources
        # Return a simple duck-typed wrapper
        class _SyntheticWrapper:
            def extract(self, since=None):
                return load_all_sources(data_base / process)
        return _SyntheticWrapper()

    elif source_type == "github":
        from app.adapters.connectors.github_connector import GitHubConnector
        return GitHubConnector(config)

    elif source_type == "notion":
        from app.adapters.connectors.notion_connector import NotionConnector
        return NotionConnector(config)

    elif source_type == "slack":
        from app.adapters.connectors.slack_connector import SlackConnector
        return SlackConnector(config)

    else:
        raise ValueError(f"Unknown source type: {source_type}")
