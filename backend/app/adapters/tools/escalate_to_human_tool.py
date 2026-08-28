"""
escalate_to_human_tool.py

The escalation tool — always available, no external API. Writes a row
to approval_requests so the case appears in the dashboard's queue. This
is the explicit callable tool version of escalation (not a silent
status flag), matching the design decided earlier in the project.
"""

import sqlite3
from datetime import datetime, timezone

from app.adapters.tools.base import ActionContext, Tool, ToolResult, register_tool


class EscalateToHumanTool(Tool):
    name = "escalate_to_human"

    def __init__(self, db_path: str = "oki.db"):
        self.db_path = db_path

    def execute(self, args: dict, ctx: ActionContext) -> ToolResult:
        reason: str = args["reason"]

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """INSERT INTO approval_requests
                   (decision_id, type, status, requested_action_json, reason, requested_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ctx.decision_id, "action", "pending", "{}", reason, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            approval_id = cursor.lastrowid
        finally:
            conn.close()

        return ToolResult(success=True, data={"approval_id": approval_id, "status": "pending_review"})


register_tool(EscalateToHumanTool())
