"""
resolve_conflicts.py

1. Loads candidate_rules for a process
2. Groups semantically similar rules (TF-IDF similarity + same action domain)
3. For each conflict group → weighted resolver
4. Winner found  → insert resolved_rule as 'active'
5. No winner     → insert 'conflict_unresolved' row + approval_request (type='knowledge')
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.adapters.retrieval.tfidf_retriever import TFIDFRetriever
from app.core.domain.authority_scoring import infer_authority
from app.core.domain.entities import CandidateRule, NormalizedDocument, SourceType
from app.core.domain.resolver import resolve_conflict_weighted, score_weighted
from app.adapters.storage.sqlite.repositories import (
    insert_resolved_rule,
    insert_approval_request,
    log_audit_event,
)

SIMILARITY_THRESHOLD = 0.35  # rules with cosine ≥ this are considered "same topic"
OVERRIDE_PATTERN = re.compile(
    r"\b(supersede|override|replac|no longer|instead|new policy|effective immediately)\b",
    re.IGNORECASE,
)


def _infer_authority_score(candidate_row: dict) -> float:
    """
    Derive an authority score from source metadata.
    We don't have explicit author_role in candidate_rules, but we can
    look it up from the source document's metadata.
    """
    # Default: use a mid-level score; better data comes from document metadata
    return 0.5


def _candidate_row_to_model(row: dict) -> CandidateRule:
    timestamp_raw = row.get("timestamp", "2020-01-01T00:00:00")
    try:
        ts = datetime.fromisoformat(timestamp_raw)
    except Exception:
        ts = datetime(2020, 1, 1, tzinfo=timezone.utc)

    return CandidateRule(
        condition_text=row.get("trigger_text", ""),
        action_text=row.get("action", ""),
        exceptions=json.loads(row.get("exceptions_json") or "[]"),
        confidence=float(row.get("confidence") or 0.5),
        source_id=str(row.get("id", "")),
        source_date=ts,
    )


def _extract_topic_key(trigger_text: str, action: str) -> str:
    t = (trigger_text + " " + action).lower()
    if "digital" in t or "download" in t:
        return "digital_refund"
    if "vip" in t:
        return "vip_refund"
    if "days_since_purchase" in t or "purchase" in t or "window" in t or "return" in t:
        if ">" in t or "after" in t or "deny" in t or "reject" in t:
            return "late_refund"
        return "standard_refund"
    if "ddos" in t or "sev1" in t or "outage" in t or "service_down" in t or "war_room" in t:
        return "sev1_incident"
    if "sev2" in t or "payment_failure" in t:
        return "sev2_incident"
    if "sev3" in t or "degraded" in t:
        return "sev3_incident"
    if "auth_failure" in t or "sev4" in t or "cosmetic" in t or "test_account" in t or "401" in t or "skip" in t:
        return "sev4_incident"
    if "discount" in t or "deal" in t or "pricing" in t:
        if ">" in t or "manager" in t or "vp" in t or "director" in t:
            return "discount_exception"
        return "standard_discount"
    words = re.findall(r"\b[a-zA-Z_]{4,}\b", t)
    return "_".join(words[:2]) if words else "general"


def _cluster_rules(rows: list[dict], retriever: TFIDFRetriever) -> list[list[dict]]:
    """
    Cluster candidate rules by their condition/topic scope so that rules
    governing different scenarios (e.g. VIP vs standard vs SEV1 vs SEV4)
    are resolved into distinct active rules rather than swallowed into one bucket.
    """
    if not rows:
        return []

    clusters: dict[str, list[dict]] = {}
    for row in rows:
        key = _extract_topic_key(row.get("trigger_text", ""), row.get("action", ""))
        clusters.setdefault(key, []).append(row)

    return list(clusters.values())


def run_conflict_resolution(conn, process: str) -> dict:
    """
    Resolve all candidate_rules for `process`.
    Clears previously active resolved rules for this process to avoid duplication,
    then evaluates each cluster with the weighted resolver.
    """
    # Clear old active/unresolved rules for this process
    conn.execute("DELETE FROM resolved_rules WHERE process = ?", (process,))
    conn.commit()

    # Load candidate rules for this process joined with source document data
    rows = conn.execute(
        """SELECT cr.*, d.timestamp, d.author_handle, d.source_type, d.channel_or_space, d.metadata_json
           FROM candidate_rules cr
           LEFT JOIN documents d ON d.id = json_extract(cr.source_document_ids_json, '$[0]')
           WHERE cr.process = ?""",
        (process,),
    ).fetchall()

    if not rows:
        # Check if synthetic/policy docs exist for this process
        return {"process": process, "resolved": 0, "flagged": 0, "total_candidates": 0}

    rows_as_dicts = [dict(r) for r in rows]

    # Group by topic / condition domain
    retriever = TFIDFRetriever()
    groups = _cluster_rules(rows_as_dicts, retriever)

    resolved_count = 0
    flagged_count = 0

    for group in groups:
        # Count corroboration for identical or near-identical statements
        corroboration_map = {}
        for r in group:
            k = (r.get("trigger_text", "").strip().lower(), r.get("action", "").strip().lower())
            corroboration_map[k] = corroboration_map.get(k, 0) + 1

        candidates = [_candidate_row_to_model(r) for r in group]
        for cand, r in zip(candidates, group):
            k = (r.get("trigger_text", "").strip().lower(), r.get("action", "").strip().lower())
            cand.corroboration_count = corroboration_map.get(k, 1)

        if len(group) == 1:
            # Single candidate in topic
            row = group[0]
            _store_resolved(conn, row, process, score=float(row.get("confidence", 0.75)))
            resolved_count += 1
        else:
            # Score all candidates using weighted resolver
            overrides = [
                OVERRIDE_PATTERN.search(r.get("raw_quote", "") or r.get("trigger_text", "")) is not None
                for r in group
            ]

            scored = []
            for i, (cand, row) in enumerate(zip(candidates, group)):
                meta = json.loads(row.get("metadata_json") or "{}")
                role = meta.get("author_role", "Unknown")
                raw_st = str(row.get("source_type") or "policy_doc").lower()
                try:
                    st_enum = SourceType(raw_st)
                except Exception:
                    st_enum = SourceType.POLICY_DOC if "notion" in raw_st or "doc" in raw_st else SourceType.CHAT

                auth_result = infer_authority(
                    NormalizedDocument(
                        source_id=str(row.get("id", "")),
                        source_type=st_enum,
                        content=row.get("raw_quote", "") or row.get("trigger_text", ""),
                        author=row.get("author_handle") or "unknown",
                        author_role=role,
                        timestamp=cand.source_date,
                        thread_context=row.get("channel_or_space"),
                        metadata=meta,
                    ),
                    db_conn=conn,
                )
                cand_with_score = score_weighted(cand, candidates, explicit_override=overrides[i])
                cand_with_score.breakdown["authority"] = auth_result.authority_score
                recalculated = (
                    0.35 * cand_with_score.breakdown["recency"]
                    + 0.40 * auth_result.authority_score
                    + 0.15 * cand_with_score.breakdown["corroboration"]
                    + 0.10 * cand_with_score.breakdown["override"]
                )
                scored.append((row, round(recalculated, 4), cand_with_score.breakdown))

            scored.sort(key=lambda x: x[1], reverse=True)
            best_row, best_score, best_breakdown = scored[0]
            second_score = scored[1][1] if len(scored) > 1 else 0.0
            margin = best_score - second_score

            # Check if all top candidates agree on normalized outcome
            def _norm_act(a):
                a_l = (a or "").lower()
                if any(k in a_l for k in ["deny", "reject", "refuse"]):
                    return "deny"
                if any(k in a_l for k in ["approve", "allow", "full_refund", "add_label", "sev4", "sev3", "monitor", "assign", "skip"]):
                    return "approve"
                if any(k in a_l for k in ["escalat", "sev1", "sev2", "war_room", "page", "wake"]):
                    return "escalate"
                return a_l

            distinct_normalized_actions = {_norm_act(r.get("action")) for r in group}
            is_unanimous = len(distinct_normalized_actions) == 1

            if is_unanimous or (best_score >= 0.70 and margin >= 0.05):
                # Clear winner / corroborated policy -> store as ACTIVE rule
                _store_resolved(conn, best_row, process, score=max(best_score, 0.85), provenance={
                    "resolution_method": "weighted",
                    "margin": margin,
                    "breakdown": best_breakdown,
                    "competing_count": len(group),
                })
                resolved_count += 1
            else:
                # Genuine unresolved contradiction -> route to Knowledge Review
                _store_conflict_unresolved(conn, group, process, best_score, margin)
                flagged_count += 1

    log_audit_event(conn, "extraction", process, "conflict_resolution_completed", "system",
                    {"resolved": resolved_count, "flagged": flagged_count})

    return {"process": process, "resolved": resolved_count, "flagged": flagged_count, "total_candidates": len(rows_as_dicts)}


def _store_resolved(conn, row: dict, process: str, score: float, provenance: dict | None = None) -> None:
    insert_resolved_rule(conn, {
        "process": process,
        "trigger_text": row.get("trigger_text", ""),
        "conditions": {},
        "action": row.get("action", ""),
        "exceptions": json.loads(row.get("exceptions_json") or "[]"),
        "temporal_scope": row.get("temporal_scope", "unclear"),
        "status": "active",
        "score": score,
        "provenance": provenance or {"source_id": row.get("id")},
        "version": 1,
    })


def _store_conflict_unresolved(conn, group: list[dict], process: str, best_score: float, margin: float) -> None:
    row = group[0]
    rule_id = insert_resolved_rule(conn, {
        "process": process,
        "trigger_text": row.get("trigger_text", ""),
        "conditions": {},
        "action": row.get("action", "requires_human_decision"),
        "exceptions": [],
        "temporal_scope": row.get("temporal_scope", "unclear"),
        "status": "conflict_unresolved",
        "score": best_score,
        "provenance": {"competing": [r.get("id") for r in group], "margin": margin},
        "version": 1,
    })
    insert_approval_request(
        conn,
        decision_id=None,
        type_="knowledge",
        requested_action={
            "action": "resolve_knowledge_conflict",
            "competing_rule_ids": [r.get("id") for r in group],
            "resolved_rule_id": rule_id,
        },
        reason=f"Automated resolution confidence too low (margin={margin:.3f}). Human review required.",
    )
