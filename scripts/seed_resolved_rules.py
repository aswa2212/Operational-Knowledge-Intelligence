"""
seed_resolved_rules.py

Run the conflict resolver for all three OKI processes and then rebuild
skills files.  This populates resolved_rules and skill_versions so the
agent decision loop has actual rules to match against.

Usage:
    cd "C:\\PROJECT WORKS\\OKI"
    python scripts/seed_resolved_rules.py
"""

import sys
import os
from pathlib import Path

BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.db.connection import get_db

PROCESSES = ["refund_handling", "incident_triage", "pricing_exceptions"]


def main():
    print("=" * 60)
    print("OKI -- Seeding resolved_rules for all processes")
    print("=" * 60)

    conn = get_db()

    cand_count = conn.execute("SELECT COUNT(*) FROM candidate_rules").fetchone()[0]
    resolved_before = conn.execute("SELECT COUNT(*) FROM resolved_rules").fetchone()[0]
    print(f"\nBefore: candidate_rules={cand_count}, resolved_rules={resolved_before}")

    if cand_count == 0:
        print("\n[ERROR] No candidate_rules found.")
        print("Run extraction first via the dashboard or demo script.")
        sys.exit(1)

    from app.core.services.resolve_conflicts import run_conflict_resolution

    total_resolved = 0
    total_flagged = 0

    for process in PROCESSES:
        cand_for_process = conn.execute(
            "SELECT COUNT(*) FROM candidate_rules WHERE process = ? AND status = 'candidate'",
            (process,),
        ).fetchone()[0]

        if cand_for_process == 0:
            print(f"\n[SKIP] {process} -- no candidate_rules with status='candidate'")
            continue

        print(f"\n[RESOLVING] {process} ({cand_for_process} candidates) ...")
        result = run_conflict_resolution(conn, process)
        total_resolved += result["resolved"]
        total_flagged += result["flagged"]
        print(
            f"  -> resolved={result['resolved']}  "
            f"flagged={result['flagged']}  "
            f"total_candidates={result['total_candidates']}"
        )

    print("\n[BUILDING SKILLS] ...")
    from app.core.services.build_skills import build_skills_file

    for process in PROCESSES:
        active_rules = conn.execute(
            "SELECT COUNT(*) FROM resolved_rules WHERE process = ? AND status = 'active'",
            (process,),
        ).fetchone()[0]

        if active_rules == 0:
            print(f"  [SKIP] {process} -- 0 active resolved rules")
            continue

        result = build_skills_file(conn, process)
        print(
            f"  {process}: v{result['version']} -- "
            f"{result['rule_count']} rules -> {result['artifact_path']}"
        )

    resolved_after = conn.execute("SELECT COUNT(*) FROM resolved_rules").fetchone()[0]
    skill_versions = conn.execute("SELECT COUNT(*) FROM skill_versions").fetchone()[0]

    print("\n" + "=" * 60)
    print(f"Done.  resolved_rules: {resolved_before} -> {resolved_after}")
    print(f"       skill_versions in DB: {skill_versions}")
    print(f"       total resolved this run: {total_resolved}")
    print(f"       total flagged (human review): {total_flagged}")
    print("=" * 60)

    if resolved_after == 0:
        print("\n[WARNING] resolved_rules is still 0.")
        print("Check candidate_rules.status -- run extraction first if needed.")


if __name__ == "__main__":
    main()
