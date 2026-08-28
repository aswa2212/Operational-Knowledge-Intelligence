"""
base.py (tool interface + registry)

Every action the agent can take — real (GitHub/Notion/Slack) or mock
(refund ledger) — implements this exact interface and is registered
here by name. The agent orchestrator NEVER hardcodes
`if action == "refund": call_refund_function()`; it always looks the
tool up by name in TOOL_REGISTRY and calls .execute(). This is what
makes new actions pluggable rather than requiring agent code changes.

Exact signatures (MVP Readiness Check item #7):
    github_add_label(issue_id: int, label: str) -> ToolResult
    github_comment(issue_id: int, body: str) -> ToolResult
    slack_notify(channel: str, message: str) -> ToolResult
    notion_create_page(parent_id: str, title: str, body: str) -> ToolResult
    mock_refund_payment(customer_id: str, amount: float) -> ToolResult
    escalate_to_human(case_id: str, reason: str) -> ToolResult
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionContext:
    """Passed to every tool call — carries the decision/case this action
    is executing on behalf of, for audit logging."""
    case_id: str
    decision_id: int
    approval_id: int | None = None


@dataclass
class ToolResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Tool(ABC):
    name: str

    @abstractmethod
    def execute(self, args: dict, ctx: ActionContext) -> ToolResult:
        raise NotImplementedError


# Populated by register_tool() calls in each concrete tool module
# (adapters/tools/github_tools.py, slack_tools.py, etc.) at import time.
TOOL_REGISTRY: dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    TOOL_REGISTRY[tool.name] = tool


def get_tool(name: str) -> Tool:
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Unknown tool: {name}. Registered tools: {list(TOOL_REGISTRY.keys())}")
    return TOOL_REGISTRY[name]
