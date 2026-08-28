"""
github_tools.py

Real GitHub Issues actions. Requires GITHUB_TOKEN and GITHUB_REPO in
.env. This is Phase 4 in the build order (see master report Section
19/Team roles) — signatures are final now so the agent orchestrator can
be built against them immediately, even before the token is wired up.
"""

import os

import httpx

from app.adapters.tools.base import ActionContext, Tool, ToolResult, register_tool

GITHUB_API_BASE = "https://api.github.com"


def _github_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set in .env")
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


class GitHubAddLabelTool(Tool):
    name = "github_add_label"

    def execute(self, args: dict, ctx: ActionContext) -> ToolResult:
        issue_id = int(args.get("issue_id") or args.get("issue_number") or 1)
        label = str(args.get("label", "oki-reviewed"))
        repo = os.getenv("GITHUB_REPO", "aswa2212/OKI")

        url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{issue_id}/labels"
        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.post(url, headers=_github_headers(), json={"labels": [label]})
                response.raise_for_status()
            return ToolResult(success=True, data={"label_url": f"{url}", "label": label})
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


class GitHubCommentTool(Tool):
    name = "github_comment"

    def execute(self, args: dict, ctx: ActionContext) -> ToolResult:
        issue_id = int(args.get("issue_id") or args.get("issue_number") or 1)
        body = str(
            args.get("body")
            or args.get("message")
            or f"🤖 **OKI Autonomous Agent Execution**\n- Case ID: #{ctx.case_id}\n- Decision ID: #{ctx.decision_id}\n- Status: Action Executed Live"
        )
        repo = os.getenv("GITHUB_REPO", "aswa2212/OKI")

        url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{issue_id}/comments"
        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.post(url, headers=_github_headers(), json={"body": body})
                if response.status_code == 404:
                    # Issue doesn't exist yet — create a new issue for this case
                    create_url = f"{GITHUB_API_BASE}/repos/{repo}/issues"
                    create_resp = client.post(
                        create_url,
                        headers=_github_headers(),
                        json={
                            "title": f"🤖 OKI Agent Execution — Case #{ctx.case_id}",
                            "body": body,
                            "labels": ["oki-reviewed", "autonomous-action", "demo-artifact"],
                        },
                    )
                    create_resp.raise_for_status()
                    created_issue = create_resp.json()
                    new_num = created_issue.get("number")
                    return ToolResult(
                        success=True,
                        data={
                            "issue_number": new_num,
                            "url": created_issue.get("html_url", f"https://github.com/{repo}/issues/{new_num}"),
                            "note": f"Created new GitHub issue #{new_num}",
                        },
                    )

                response.raise_for_status()
                comment_id = response.json().get("id")
            return ToolResult(
                success=True,
                data={
                    "comment_id": comment_id,
                    "url": f"https://github.com/{repo}/issues/{issue_id}#issuecomment-{comment_id}",
                },
            )
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


register_tool(GitHubAddLabelTool())
register_tool(GitHubCommentTool())
