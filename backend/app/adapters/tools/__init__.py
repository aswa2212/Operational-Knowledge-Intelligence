"""
Import all concrete tool modules here so their register_tool() calls fire
at startup, populating TOOL_REGISTRY before any request is served.
"""

from app.adapters.tools import (  # noqa: F401
    escalate_to_human_tool,
    github_tools,
    mock_payment_tools,
    notion_tools,
    slack_tools,
)
