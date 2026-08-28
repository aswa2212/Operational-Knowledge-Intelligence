"""
close_demo_issues.py

Utility script to find and close GitHub issues created during rehearsals
or evaluation with the 'demo-artifact' label.

Usage:
    python scripts/close_demo_issues.py
"""

import os
import sys
from pathlib import Path

# Load .env
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

import httpx

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "aswa2212/OKI")

if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN not found in environment.")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

print(f"Checking for open issues with 'demo-artifact' in {GITHUB_REPO}...")

with httpx.Client(timeout=10.0) as client:
    resp = client.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        headers=headers,
        params={"labels": "demo-artifact", "state": "open"},
    )
    if resp.status_code != 200:
        print(f"Failed to query issues: {resp.status_code} {resp.text}")
        sys.exit(1)

    issues = resp.json()
    print(f"Found {len(issues)} open demo issues.")

    for issue in issues:
        num = issue["number"]
        title = issue["title"]
        print(f"Closing issue #{num}: {title}...")
        close_resp = client.patch(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues/{num}",
            headers=headers,
            json={"state": "closed", "state_reason": "completed"},
        )
        if close_resp.status_code == 200:
            print(f"  Closed #{num} successfully.")
        else:
            print(f"  Failed to close #{num}: {close_resp.status_code}")

print("Done.")
