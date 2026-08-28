"""
slack_tools.py

Real Slack actions via SLACK_BOT_TOKEN in .env.
Automatically resolves channel names to channel IDs and falls back to
the connected OKI channel if a specific channel is not found.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Optional

import httpx

from app.adapters.tools.base import ActionContext, Tool, ToolResult, register_tool

SLACK_API_BASE = "https://slack.com/api"
DEFAULT_FALLBACK_CHANNEL = "C0BRA59UYJK"  # all-oki


def _get_connected_slack_channels() -> list[str]:
    """Retrieve configured Slack channel names/IDs from oki.db."""
    try:
        conn = sqlite3.connect("oki.db")
        row = conn.execute("SELECT config_json FROM sources WHERE type='slack'").fetchone()
        conn.close()
        if row and row[0]:
            cfg = json.loads(row[0])
            channels = cfg.get("channels") or []
            if isinstance(channels, list) and channels:
                return channels
    except Exception:
        pass
    return [DEFAULT_FALLBACK_CHANNEL]


def _resolve_slack_channel(client: httpx.Client, token: str, channel_input: str) -> str:
    """Resolve channel name/ID to a valid channel ID."""
    clean = channel_input.strip().lstrip("#")
    if clean.startswith("C") and len(clean) >= 9:
        return clean

    # Check known mapped channels
    if clean == "all-oki":
        return "C0BRA59UYJK"
    if clean == "new-channel":
        return "C0BRV6EHA8L"

    # Try listing channels if bot has scope
    try:
        resp = client.get(
            f"{SLACK_API_BASE}/conversations.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"types": "public_channel,private_channel", "limit": 100},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                for ch in data.get("channels", []):
                    if ch.get("name") == clean or ch.get("id") == clean:
                        return ch["id"]
    except Exception:
        pass

    # Default fallback
    return DEFAULT_FALLBACK_CHANNEL


class SlackNotifyTool(Tool):
    name = "slack_notify"

    def execute(self, args: dict, ctx: ActionContext) -> ToolResult:
        raw_channel: str = str(args.get("channel") or "all-oki")
        message: str = str(args.get("message") or args.get("body") or "🤖 OKI Alert")
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return ToolResult(success=False, error="SLACK_BOT_TOKEN not set in .env")

        try:
            with httpx.Client(timeout=8.0) as client:
                target_channel = _resolve_slack_channel(client, token, raw_channel)

                # Attempt post
                response = client.post(
                    f"{SLACK_API_BASE}/chat.postMessage",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"channel": target_channel, "text": message},
                )
                response.raise_for_status()
                result = response.json()

                if not result.get("ok"):
                    err = result.get("error", "unknown_slack_error")
                    # If channel not found, retry on default fallback
                    if err in ("channel_not_found", "not_in_channel") and target_channel != DEFAULT_FALLBACK_CHANNEL:
                        retry_resp = client.post(
                            f"{SLACK_API_BASE}/chat.postMessage",
                            headers={"Authorization": f"Bearer {token}"},
                            json={"channel": DEFAULT_FALLBACK_CHANNEL, "text": message},
                        )
                        retry_data = retry_resp.json()
                        if retry_data.get("ok"):
                            return ToolResult(
                                success=True,
                                data={
                                    "ts": retry_data.get("ts"),
                                    "channel": DEFAULT_FALLBACK_CHANNEL,
                                    "note": f"Posted to default #{raw_channel} fallback channel",
                                },
                            )
                    return ToolResult(success=False, error=err)

                return ToolResult(
                    success=True,
                    data={
                        "ts": result.get("ts"),
                        "channel": target_channel,
                        "channel_name": raw_channel,
                    },
                )
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


register_tool(SlackNotifyTool())
