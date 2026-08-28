"""
mock_payment_tools.py

The one tool that's fully functional today — no external API needed.
Writes a before/after state row so the dashboard can show the visible
state change (Risk 5 mitigation from the master report).
"""

import sqlite3
import uuid
from datetime import datetime, timezone

from app.adapters.tools.base import ActionContext, Tool, ToolResult, register_tool


class MockRefundPaymentTool(Tool):
    name = "mock_refund_payment"

    def __init__(self, db_path: str = "oki.db"):
        self.db_path = db_path

    def execute(self, args: dict, ctx: ActionContext) -> ToolResult:
        customer_id = str(args.get("customer_id") or args.get("customer_tier") or "cust_auto")
        amount = float(args.get("amount") or args.get("order_value") or 0.0)
        refund_id = str(uuid.uuid4())[:8]

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS mock_refund_state (
                    refund_id TEXT PRIMARY KEY,
                    customer_id TEXT,
                    amount REAL,
                    status_before TEXT,
                    status_after TEXT,
                    case_id TEXT,
                    executed_at TEXT
                )"""
            )
            conn.execute(
                "INSERT INTO mock_refund_state VALUES (?, ?, ?, ?, ?, ?, ?)",
                (refund_id, customer_id, amount, "PENDING", "REFUNDED", ctx.case_id, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

        return ToolResult(success=True, data={"refund_id": refund_id, "before_state": "PENDING", "after_state": "REFUNDED"})


register_tool(MockRefundPaymentTool())
