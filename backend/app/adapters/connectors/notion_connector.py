"""
notion_connector.py

Incremental Notion ingestion connector.

Change detection strategy (v3):
  - We do NOT use the `since` timestamp to filter pages at the API level
    for the single-page / workspace-search modes.  Notion's `last_edited_time`
    is minute-rounded, which causes edits that happen within the same minute
    as the last sync to be silently skipped.
  - Instead we fetch EVERY accessible page's metadata (cheap — no blocks),
    compare its `last_edited_time` against our stored cache (`known_page_ids`),
    and only re-download blocks for pages that have actually changed.
  - Block DELETIONS are caught because Notion bumps `last_edited_time` on the
    parent page whenever any child block is added, modified, or removed.
  - We also store a content hash alongside the edit time so even if the
    timestamp doesn't change (Notion caches it for ~1 min) we still detect
    actual content diffs.

Config keys (stored in sources.config_json):
    database_id        — Notion database ID (without dashes)
    page_ids           — comma-separated explicit page IDs (overrides database_id)
    process            — OKI process label (logging only)
    known_page_ids     — auto-maintained dict of
                         {notion_page_id: {"ts": last_edited_time, "hash": content_hash}}
                         written back to config by sync_source after each run
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

from app.adapters.connectors.base import SourceConnector
from app.core.domain.entities import NormalizedDocument, SourceType

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
_MAX_RETRIES = 3


class NotionConnector(SourceConnector):
    """
    Fetches ONLY new/changed Notion pages as NormalizedDocuments.

    Uses a two-field cache per page:
      - "ts":   Notion's last_edited_time string (minute-rounded)
      - "hash": SHA-256 of the last-fetched block content

    A page is re-processed when EITHER the ts OR the hash differs.
    This catches both normal edits (ts change) and same-minute edits
    like deletions where Notion hasn't updated the ts yet.
    """

    def __init__(self, config: Optional[dict] = None, **kwargs):
        super().__init__(config=config or kwargs)
        self.database_id = self.config.get("database_id", "")
        self.token = os.getenv("NOTION_TOKEN", "")

        # Cache: {page_id: {"ts": str, "hash": str}}
        # Loaded from config; supports old format {page_id: ts_str} for migration
        raw_cache = self.config.get("known_page_ids") or {}
        self.known_page_cache: dict[str, dict] = {}
        for pid, val in raw_cache.items():
            if isinstance(val, dict):
                self.known_page_cache[pid] = val
            else:
                # migrate old {page_id: ts_str} format
                self.known_page_cache[pid] = {"ts": str(val), "hash": ""}

    # ── Headers ───────────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    # ── Public property so sync_source can persist the updated cache ──────────

    @property
    def known_page_times(self) -> dict:
        """Expose the full cache dict for persistence by sync_source."""
        return self.known_page_cache

    # ── Main entry point ──────────────────────────────────────────────────────

    def extract(self, since: Optional[datetime] = None) -> list[NormalizedDocument]:
        if not self.token:
            print("[NotionConnector] NOTION_TOKEN not set — skipping")
            return []

        docs: list[NormalizedDocument] = []

        # Single client for the entire sync run → connection reuse
        with httpx.Client(
            timeout=30.0,
            headers=self._headers(),
            http2=False,
        ) as client:

            # ── Mode A: Explicit page_ids ────────────────────────────────────
            page_ids = self.config.get("page_ids")
            if page_ids:
                if isinstance(page_ids, str):
                    page_ids = [p.strip() for p in page_ids.split(",") if p.strip()]
                for pid in page_ids:
                    doc = self._fetch_single_page(client, pid)
                    if doc:
                        docs.append(doc)
                print(f"[NotionConnector] Fetched {len(docs)} explicit pages (change-detected)")
                return docs

            # ── Mode B: Database query ───────────────────────────────────────
            if self.database_id:
                docs = self._query_database(client)
                print(
                    f"[NotionConnector] Database {self.database_id}: "
                    f"{len(docs)} new/changed pages fetched"
                )
                return docs

            # ── Mode C: Workspace search (auto-discover) ─────────────────────
            docs = self._search_workspace(client)
            print(f"[NotionConnector] Auto-discovered {len(docs)} new/changed pages")
            return docs

    # ── Database mode ─────────────────────────────────────────────────────────

    def _query_database(self, client: httpx.Client) -> list[NormalizedDocument]:
        docs: list[NormalizedDocument] = []
        cursor = None
        has_more = True

        # Fetch ALL pages — change detection handled by our cache, not by
        # Notion's `last_edited_time` filter (which is minute-rounded and
        # misses same-minute deletions).
        body: dict = {"page_size": 100}

        while has_more:
            if cursor:
                body["start_cursor"] = cursor

            data = self._post(
                client,
                f"{NOTION_API}/databases/{self.database_id}/query",
                body,
            )
            if data is None:
                break

            for page in data.get("results", []):
                doc = self._process_page(client, page)
                if doc:
                    docs.append(doc)

            has_more = data.get("has_more", False)
            cursor = data.get("next_cursor")

        return docs

    # ── Workspace search mode ─────────────────────────────────────────────────

    def _search_workspace(self, client: httpx.Client) -> list[NormalizedDocument]:
        docs: list[NormalizedDocument] = []
        body: dict = {
            "filter": {"value": "page", "property": "object"},
            "page_size": 100,
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        }
        try:
            resp = client.post(f"{NOTION_API}/search", json=body)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[NotionConnector] Auto-discovery search error: {e}")
            return []

        for page in data.get("results", []):
            doc = self._process_page(client, page)
            if doc:
                docs.append(doc)
        return docs

    # ── Single explicit page ──────────────────────────────────────────────────

    def _fetch_single_page(
        self, client: httpx.Client, page_id: str
    ) -> Optional[NormalizedDocument]:
        try:
            resp = client.get(f"{NOTION_API}/pages/{page_id}")
            resp.raise_for_status()
            page = resp.json()
        except Exception as e:
            print(f"[NotionConnector] Error fetching page {page_id}: {e}")
            return None
        return self._process_page(client, page)

    # ── Core page processor ───────────────────────────────────────────────────

    def _process_page(
        self,
        client: httpx.Client,
        page: dict,
    ) -> Optional[NormalizedDocument]:
        """
        Normalizes one Notion page using two-stage change detection:
          1. Compare Notion's last_edited_time (cheap — already in page metadata).
          2. If ts matches cached ts, still fetch blocks and compare content hash.
             This catches block deletions that don't always bump the minute-rounded ts.

        Only returns None (skip) if BOTH the timestamp AND the content hash match.
        """
        page_id = page["id"]
        edited_raw = (
            page.get("last_edited_time")
            or page.get("created_time")
            or "2020-01-01T00:00:00Z"
        )

        try:
            ts = datetime.fromisoformat(edited_raw.replace("Z", "+00:00"))
        except Exception:
            ts = datetime(2020, 1, 1, tzinfo=timezone.utc)

        cached = self.known_page_cache.get(page_id, {})
        cached_ts = cached.get("ts", "")
        cached_hash = cached.get("hash", "")

        # ── Stage 1: timestamp changed → definitely re-fetch blocks ──────────
        ts_changed = (edited_raw != cached_ts)

        if not ts_changed and cached_hash:
            # ── Stage 2: ts same (minute-rounded) → still check content hash ─
            # Fetch blocks to get actual content and compare hashes.
            # This is the key fix for block deletions that don't bump the ts.
            title = _extract_title(page)
            body_text = self._fetch_blocks(client, page_id)
            content = f"{title}\n\n{body_text}".strip() if body_text else title
            new_hash = _content_hash(content)

            if new_hash == cached_hash:
                # Nothing changed — skip
                return None

            # Content changed even though ts didn't — update cache and return doc
            print(f"[NotionConnector] Page {page_id[:8]}… content changed (same ts, hash diff) — updating")
            self.known_page_cache[page_id] = {"ts": edited_raw, "hash": new_hash}
            return self._make_doc(page, page_id, ts, content)

        # ── Fetch blocks (ts changed or no cache yet) ─────────────────────────
        title = _extract_title(page)
        body_text = self._fetch_blocks(client, page_id)
        content = f"{title}\n\n{body_text}".strip() if body_text else title
        new_hash = _content_hash(content)

        if not ts_changed and new_hash == cached_hash:
            # Both ts and hash match — nothing to do
            return None

        action = "new" if not cached_ts else "updated"
        print(f"[NotionConnector] Page {page_id[:8]}… {action} (ts_changed={ts_changed})")

        # Update cache
        self.known_page_cache[page_id] = {"ts": edited_raw, "hash": new_hash}

        return self._make_doc(page, page_id, ts, content)

    def _make_doc(
        self,
        page: dict,
        page_id: str,
        ts: datetime,
        content: str,
    ) -> NormalizedDocument:
        creator = page.get("created_by", {})
        author = creator.get("name") or creator.get("id") or "Notion Workspace"
        edited_raw = page.get("last_edited_time") or page.get("created_time") or ""

        return NormalizedDocument(
            source_id=f"notion-{page_id}",
            source_type=SourceType.POLICY_DOC,
            content=content,
            author=author,
            author_role="Documentation Author",
            timestamp=ts,
            thread_context=self.database_id or "notion-workspace",
            metadata={
                "page_id": page_id,
                "last_edited_time": edited_raw,
                "workspace_role": (
                    "workspace_admin"
                    if "admin" in str(creator).lower()
                    else "editor"
                ),
                "author_role": "Documentation Author",
            },
        )

    # ── Block fetcher ─────────────────────────────────────────────────────────

    def _fetch_blocks(self, client: httpx.Client, page_id: str) -> str:
        """
        Fetch ALL text blocks from a Notion page recursively.
        Handles pagination + nested blocks (toggle, callout, etc.)
        so block deletions at any depth are captured.
        """
        return self._fetch_block_children(client, page_id)

    def _fetch_block_children(self, client: httpx.Client, block_id: str, depth: int = 0) -> str:
        """Recursively fetch block text, including children of container blocks."""
        texts: list[str] = []
        cursor = None
        has_more = True
        indent = "  " * depth

        while has_more:
            url = f"{NOTION_API}/blocks/{block_id}/children?page_size=100"
            if cursor:
                url += f"&start_cursor={cursor}"
            try:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                break

            for block in data.get("results", []):
                btype = block.get("type", "")
                block_data = block.get(btype, {})
                rich_text = block_data.get("rich_text", [])
                fragment = "".join(r.get("plain_text", "") for r in rich_text)
                if fragment.strip():
                    texts.append(f"{indent}{fragment}")

                # Recurse into container block types (toggle, callout, quote, etc.)
                if block.get("has_children") and depth < 3:
                    child_text = self._fetch_block_children(client, block["id"], depth + 1)
                    if child_text:
                        texts.append(child_text)

            has_more = data.get("has_more", False)
            cursor = data.get("next_cursor")

        return "\n".join(texts)

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _post(
        self, client: httpx.Client, url: str, body: dict
    ) -> Optional[dict]:
        """POST with exponential back-off on 429 rate-limit errors."""
        delay = 1.0
        for attempt in range(_MAX_RETRIES):
            try:
                resp = client.post(url, json=body)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", delay))
                    print(
                        f"[NotionConnector] Rate limited — waiting {retry_after:.1f}s "
                        f"(attempt {attempt + 1}/{_MAX_RETRIES})"
                    )
                    time.sleep(retry_after)
                    delay *= 2
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                print(f"[NotionConnector] HTTP error {e.response.status_code}: {e}")
                return None
            except Exception as e:
                print(f"[NotionConnector] API error: {e}")
                return None
        return None


# ── Standalone helpers ────────────────────────────────────────────────────────

def _extract_title(page: dict) -> str:
    """Extract the plain-text title from a Notion page's properties."""
    props = page.get("properties", {})
    for _name, prop in props.items():
        if prop.get("type") == "title":
            rich = prop.get("title", [])
            return "".join(r.get("plain_text", "") for r in rich)
    return "(untitled)"


def _content_hash(content: str) -> str:
    """SHA-256 of content (first 8 hex chars for compactness in logs)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
