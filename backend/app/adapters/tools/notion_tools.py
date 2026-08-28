"""
notion_tools.py

Real Notion actions via NOTION_TOKEN in .env. Phase 5 in the build order.
"""

import os

import httpx

from app.adapters.tools.base import ActionContext, Tool, ToolResult, register_tool

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionCreatePageTool(Tool):
    name = "notion_create_page"

    def execute(self, args: dict, ctx: ActionContext) -> ToolResult:
        parent_id: str = args["parent_id"]
        title: str = args["title"]
        body: str = args["body"]
        token = os.getenv("NOTION_TOKEN")
        if not token:
            return ToolResult(success=False, error="NOTION_TOKEN not set in .env")

        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        payload = {
            "parent": {"page_id": parent_id},
            "properties": {"title": [{"text": {"content": title}}]},
            "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": body}}]}}],
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{NOTION_API_BASE}/pages", headers=headers, json=payload)
                response.raise_for_status()
                page_url = response.json().get("url")
            return ToolResult(success=True, data={"page_url": page_url})
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


register_tool(NotionCreatePageTool())
