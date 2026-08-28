"""
build_skills.py

Loads all active resolved_rules for a process and serialises them into
a versioned YAML artifact in skills_artifacts/<process>/v<N>.yaml.
Also inserts a skill_versions row and logs an audit event.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.adapters.storage.sqlite.repositories import log_audit_event

SKILLS_BASE = Path(__file__).parent.parent.parent.parent.parent / "skills_artifacts"


def build_skills_file(conn, process: str) -> dict:
    """
    Build and persist a new skill version for `process`.
    Returns a dict with version, path, rule_count.
    """
    # Load active resolved rules
    rows = conn.execute(
        "SELECT * FROM resolved_rules WHERE process = ? AND status = 'active' ORDER BY score DESC",
        (process,),
    ).fetchall()

    # Also load flagged conflicts for the manifest
    conflicts = conn.execute(
        "SELECT * FROM resolved_rules WHERE process = ? AND status = 'conflict_unresolved'",
        (process,),
    ).fetchall()

    # Determine next version number
    last_version_row = conn.execute(
        "SELECT MAX(version) as v FROM skill_versions WHERE process = ?", (process,)
    ).fetchone()
    version = (last_version_row["v"] or 0) + 1

    # Build the skills YAML document
    skills_doc = {
        "meta": {
            "process": process,
            "version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rule_count": len(rows),
            "flagged_conflict_count": len(conflicts),
            "schema_version": "1.0",
        },
        "rules": [_row_to_rule(r) for r in rows],
        "flagged_conflicts": [_row_to_conflict(c) for c in conflicts],
        "escalation_rules": _default_escalation_rules(process),
    }

    # Write artifact
    output_dir = SKILLS_BASE / process
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"v{version:03d}.yaml"
    with open(artifact_path, "w", encoding="utf-8") as f:
        yaml.dump(skills_doc, f, allow_unicode=True, sort_keys=False)

    # Record in DB
    cur = conn.execute(
        "INSERT INTO skill_versions (process, version, status, generated_at, artifact_path) VALUES (?, ?, 'active', ?, ?)",
        (process, version, datetime.now(timezone.utc).isoformat(), str(artifact_path)),
    )
    conn.commit()

    log_audit_event(conn, "skills", process, "skills_built", "system",
                    {"version": version, "rule_count": len(rows), "path": str(artifact_path)})

    return {
        "process": process,
        "version": version,
        "rule_count": len(rows),
        "flagged_conflict_count": len(conflicts),
        "artifact_path": str(artifact_path),
    }


def get_active_skills(conn, process: str) -> dict | None:
    """Load the most recent active skill version's YAML as a dict."""
    row = conn.execute(
        "SELECT * FROM skill_versions WHERE process = ? AND status = 'active' ORDER BY version DESC LIMIT 1",
        (process,),
    ).fetchone()
    if not row:
        return None
    path = Path(row["artifact_path"])
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _row_to_rule(row) -> dict:
    return {
        "id": row["id"],
        "trigger_text": row["trigger_text"],
        "action": row["action"],
        "conditions": json.loads(row["conditions_json"] or "{}"),
        "exceptions": json.loads(row["exceptions_json"] or "[]"),
        "temporal_scope": row["temporal_scope"],
        "status": row["status"],
        "score": round(float(row["score"] or 0), 4),
        "provenance": json.loads(row["provenance_json"] or "{}"),
    }


def _row_to_conflict(row) -> dict:
    return {
        "id": row["id"],
        "trigger_text": row["trigger_text"],
        "action": row["action"],
        "provenance": json.loads(row["provenance_json"] or "{}"),
    }


def _default_escalation_rules(process: str) -> list[dict]:
    return [
        {"id": "ESC-001", "trigger": "no_rule_matches", "action": "escalate_to_human", "target_role": "Manager", "reason": "No matching rule found"},
        {"id": "ESC-002", "trigger": "confidence_below_threshold", "action": "escalate_to_human", "target_role": "Manager", "reason": "Confidence below 0.55", "threshold": 0.55},
        {"id": "ESC-003", "trigger": "conflicting_rules_active", "action": "escalate_to_human", "target_role": "Director", "reason": "Conflicting rules require human arbitration"},
    ]
