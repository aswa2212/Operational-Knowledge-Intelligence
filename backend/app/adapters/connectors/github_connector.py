"""
github_connector.py

Real GitHub Issues ingestion connector.  Implements SourceConnector.extract()
by fetching open (and optionally closed) issues from any GitHub repo via the
public REST API.  Requires GITHUB_TOKEN and GITHUB_REPO in .env.

Config keys (stored in sources.config_json):
    repo          — e.g. "owner/repo-name"  (falls back to $GITHUB_REPO)
    state         — "open" | "closed" | "all"  (default: "open")
    process       — the OKI process name for labelling documents
    labels        — comma-separated label filter (optional)

Each GitHub Issue is normalised into a NormalizedDocument:
    source_type = SourceType.TICKET
    source_id   = "gh-issue-<number>"
    content     = "{title}\\n\\n{body}"
    author      = issue.user.login
    author_role = inferred from CODEOWNERS or left as "Unknown"
    timestamp   = issue.created_at
    thread_context = repo name
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

GITHUB_API = "https://api.github.com"


class GitHubConnector(SourceConnector):
    """
    Fetches GitHub Issues as NormalizedDocuments.

    config = {
        "repo": "owner/repo",          # required (or GITHUB_REPO env var)
        "state": "open",               # open | closed | all
        "labels": "",                  # optional comma-separated label filter
        "process": "refund_handling"   # used for logging only
    }
    """

    def __init__(self, config: Optional[dict] = None, **kwargs):
        super().__init__(config=config or kwargs)
        self.repo = self.config.get("repo") or os.getenv("GITHUB_REPO", "")
        self.state = self.config.get("state", "open")
        self.labels = self.config.get("labels", "")
        self.token = os.getenv("GITHUB_TOKEN", "")

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def extract(self, since: Optional[datetime] = None) -> list[NormalizedDocument]:
        if not self.repo:
            print("[GitHubConnector] GITHUB_REPO not configured — skipping")
            return []

        docs: list[NormalizedDocument] = []
        page = 1

        params: dict = {"state": self.state, "per_page": 100, "page": page}
        if self.labels:
            params["labels"] = self.labels
        if since:
            from datetime import timedelta
            params["since"] = (since - timedelta(seconds=15)).isoformat()


        while True:
            params["page"] = page
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(
                        f"{GITHUB_API}/repos/{self.repo}/issues",
                        headers=self._headers(),
                        params=params,
                    )
                    resp.raise_for_status()
                    issues = resp.json()
            except Exception as e:
                print(f"[GitHubConnector] API error on page {page}: {e}")
                break

            if not issues:
                break

            for issue in issues:
                # Skip pull requests (they appear in /issues too)
                if issue.get("pull_request"):
                    continue

                created_raw = issue.get("created_at", "2020-01-01T00:00:00Z")
                try:
                    ts = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime(2020, 1, 1, tzinfo=timezone.utc)

                body = issue.get("body") or ""
                title = issue.get("title", "")
                content = f"{title}\n\n{body}".strip()

                labels_list = [lb["name"] for lb in issue.get("labels", [])]
                author_login = issue.get("user", {}).get("login", "unknown")
                assoc = issue.get("author_association", "NONE")
                
                # Map author_association to a human-readable role
                assoc_role_map = {
                    "OWNER": "Repository Owner",
                    "MEMBER": "Organization Member",
                    "COLLABORATOR": "Collaborator",
                    "CONTRIBUTOR": "Contributor",
                    "FIRST_TIME_CONTRIBUTOR": "First-Time Contributor",
                    "NONE": "External User",
                }
                author_role = assoc_role_map.get(assoc, "External User")

                docs.append(
                    NormalizedDocument(
                        source_id=f"gh-issue-{issue['number']}",
                        source_type=SourceType.TICKET,
                        content=content,
                        author=author_login,
                        author_role=author_role,
                        timestamp=ts,
                        thread_context=self.repo,
                        metadata={
                            "author_association": assoc,
                            "author_role": author_role,
                            "issue_number": issue.get("number"),
                            "labels": labels_list,
                        },
                    )
                )

            # Check for next page via Link header
            link_header = resp.headers.get("Link", "")
            if 'rel="next"' not in link_header:
                break
            page += 1

        print(f"[GitHubConnector] Fetched {len(docs)} issues from {self.repo}")
        return docs
