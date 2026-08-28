"""
slack_connector.py

Real Slack ingestion connector.  Implements SourceConnector.extract() by
fetching messages from one or more Slack channels via the Web API.
Requires SLACK_BOT_TOKEN in .env with scopes:
    channels:history, channels:read, groups:history, groups:read, users:read

Config keys (stored in sources.config_json):
    channels      — list of channel names or IDs to ingest, e.g. ["#ops", "C04XXXX"]
                    Falls back to SLACK_CHANNELS env var (comma-separated).
    oldest        — optional Unix timestamp lower bound (float as str)
    process       — OKI process name for labelling

Each Slack message is normalised into a NormalizedDocument:
    source_type   = SourceType.CHAT
    source_id     = "slack-<channel_id>-<ts>"
    content       = message text
    author        = user display name (resolved via users.info)
    author_role   = "Unknown" (inferred downstream)
    timestamp     = message ts converted to datetime
    thread_context= channel name
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

from app.adapters.connectors.base import SourceConnector
from app.core.domain.entities import NormalizedDocument, SourceType

SLACK_API = "https://slack.com/api"


class SlackConnector(SourceConnector):
    """
    Fetches messages from Slack channels as NormalizedDocuments.

    config = {
        "channels": ["ops-alerts", "C0123ABCDEF"],   # names or IDs
        "process": "incident_triage"
    }
    """

    def __init__(self, config: Optional[dict] = None, **kwargs):
        super().__init__(config=config or kwargs)
        self.token = os.getenv("SLACK_BOT_TOKEN", "")
        raw_channels = self.config.get("channels") or os.getenv("SLACK_CHANNELS", "")
        if isinstance(raw_channels, str):
            self.channel_names = [c.strip().lstrip("#") for c in raw_channels.split(",") if c.strip()]
        else:
            self.channel_names = [c.lstrip("#") for c in raw_channels]

        self._user_cache: dict[str, str] = {}
        self._channels_cache: dict[str, str] = {}

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def _fetch_channels_map(self) -> dict[str, str]:
        """Fetch all public channels and map name -> id."""
        if self._channels_cache:
            return self._channels_cache
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{SLACK_API}/conversations.list",
                    headers=self._headers(),
                    params={"limit": 200, "types": "public_channel", "exclude_archived": "true"},
                )
                resp.raise_for_status()
                data = resp.json()
            if data.get("ok"):
                for ch in data.get("channels", []):
                    self._channels_cache[ch["name"]] = ch["id"]
                    self._channels_cache[ch["id"]] = ch["id"]
        except Exception as e:
            print(f"[SlackConnector] Error listing channels: {e}")
        return self._channels_cache

    def _resolve_channel_id(self, name: str) -> Optional[str]:
        """Resolve channel name → ID. If name looks like an ID already, return as-is."""
        if name.startswith("C") and len(name) > 8:
            return name
        ch_map = self._fetch_channels_map()
        return ch_map.get(name)

    def _resolve_user_details(self, user_id: str) -> dict:
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        details = {
            "name": user_id,
            "title": "Staff",
            "is_admin": False,
            "is_owner": False,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{SLACK_API}/users.info",
                    headers=self._headers(),
                    params={"user": user_id},
                )
                resp.raise_for_status()
                u = resp.json().get("user", {})
                profile = u.get("profile", {})
                details["name"] = profile.get("real_name") or u.get("real_name") or u.get("name") or user_id
                details["title"] = profile.get("title") or ("Workspace Admin" if u.get("is_admin") else "Staff")
                details["is_admin"] = bool(u.get("is_admin"))
                details["is_owner"] = bool(u.get("is_owner") or u.get("is_primary_owner"))
        except Exception as e:
            print(f"[SlackConnector] Error resolving user '{user_id}': {e}")
        self._user_cache[user_id] = details
        return details

    def extract(self, since: Optional[datetime] = None) -> list[NormalizedDocument]:
        if not self.token:
            print("[SlackConnector] SLACK_BOT_TOKEN not set — skipping")
            return []

        # If no explicit channel configured, use all discoverable public channels
        target_channels = self.channel_names
        if not target_channels:
            ch_map = self._fetch_channels_map()
            target_channels = list(set(ch_map.keys()))

        if not target_channels:
            print("[SlackConnector] No channels found — skipping")
            return []

        docs: list[NormalizedDocument] = []
        oldest_ts = str(since.timestamp() - 15.0) if since else None

        seen_channel_ids = set()
        for name in target_channels:
            channel_id = self._resolve_channel_id(name)
            if not channel_id or channel_id in seen_channel_ids:
                continue
            seen_channel_ids.add(channel_id)

            cursor = None
            while True:
                params: dict = {"channel": channel_id, "limit": 200}
                if oldest_ts:
                    params["oldest"] = oldest_ts
                if cursor:
                    params["cursor"] = cursor

                try:
                    with httpx.Client(timeout=30.0) as client:
                        resp = client.get(
                            f"{SLACK_API}/conversations.history",
                            headers=self._headers(),
                            params=params,
                        )
                        resp.raise_for_status()
                        data = resp.json()
                except Exception as e:
                    print(f"[SlackConnector] Error fetching '{name}': {e}")
                    break

                if not data.get("ok"):
                    print(f"[SlackConnector] Slack API error for '{name}': {data.get('error')}")
                    break

                for msg in data.get("messages", []):
                    text = msg.get("text", "").strip()
                    if not text or msg.get("subtype"):  # skip bot messages, joins, etc.
                        continue

                    ts_raw = msg.get("ts", "0")
                    try:
                        ts = datetime.fromtimestamp(float(ts_raw), tz=timezone.utc)
                    except Exception:
                        ts = datetime(2020, 1, 1, tzinfo=timezone.utc)

                    user_id = msg.get("user", "unknown")
                    u_details = self._resolve_user_details(user_id) if user_id != "unknown" else {"name": "unknown", "title": "Staff"}
                    author = u_details.get("name", user_id)
                    author_title = u_details.get("title", "Staff")

                    docs.append(
                        NormalizedDocument(
                            source_id=f"slack-{channel_id}-{ts_raw}",
                            source_type=SourceType.CHAT,
                            content=text,
                            author=author,
                            author_role=author_title,
                            timestamp=ts,
                            thread_context=f"#{name}",
                            metadata={
                                "author_id": user_id,
                                "author_role": author_title,
                                "is_admin": u_details.get("is_admin", False),
                                "is_owner": u_details.get("is_owner", False),
                            },
                        )
                    )

                meta = data.get("response_metadata", {})
                next_cursor = meta.get("next_cursor", "")
                if not next_cursor or not data.get("has_more"):
                    break
                cursor = next_cursor

        print(f"[SlackConnector] Fetched {len(docs)} messages from Slack channels: {list(seen_channel_ids)}")
        return docs


