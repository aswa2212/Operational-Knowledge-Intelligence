"""
extract_rules.py

Two-pass LLM extraction pipeline (main method) + single-pass baseline.

Two-pass (Ablation 1a):
  Pass 1 — identify candidate rule mentions (free-text)
  Pass 2 — structure each mention into a CandidateRule dict

Single-pass (Ablation 1b):
  One LLM call per document; extracts all rules at once.

Both paths write rows to the candidate_rules table with extraction_method tagged.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from app.adapters.llm.ollama_provider import get_llm_provider
from app.adapters.storage.sqlite.repositories import log_audit_event
from app.prompts import extraction_two_pass_v1 as two_pass_p
from app.prompts import extraction_single_pass_v1 as single_pass_p


def _insert_candidate_rule(conn, rule: dict, process: str, source_doc_id: int, method: str) -> int:
    cur = conn.execute(
        """INSERT INTO candidate_rules
           (process, trigger_text, conditions_json, action, exceptions_json,
            temporal_scope, source_document_ids_json, authority_score, confidence,
            raw_quote, extraction_method, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate')""",
        (
            process,
            rule.get("condition_text", ""),
            json.dumps({}),  # structured later by resolve_conflicts
            rule.get("action_text", ""),
            json.dumps(rule.get("exceptions", [])),
            rule.get("temporal_scope", "unclear"),
            json.dumps([source_doc_id]),
            None,  # authority_score filled during resolution
            float(rule.get("confidence", 0.5)),
            rule.get("raw_quote", rule.get("condition_text", ""))[:2000],
            method,
        ),
    )
    conn.commit()
    return cur.lastrowid


def run_two_pass_extraction(conn, process: str, documents: list[dict]) -> dict:
    """
    documents: list of sqlite3.Row-like dicts with keys: id, text, source_type, author_handle, timestamp
    Returns summary dict.
    """
    llm = get_llm_provider()
    total_inserted = 0
    total_docs = len(documents)

    for doc in documents:
        doc_id = doc["id"]
        text = doc["text"]
        source_type = doc["source_type"]
        author = doc["author_handle"] or "unknown"
        timestamp = doc["timestamp"]

        # ── Pass 1: identify mentions ──────────────────────────────────
        pass1_prompt = (
            two_pass_p.PASS1_SYSTEM + "\n\n"
            + two_pass_p.PASS1_USER.format(
                source_id=str(doc_id),
                source_type=source_type,
                author=author,
                timestamp=timestamp,
                content=text[:6000],
            )
        )
        try:
            mentions_raw = llm.complete_json(pass1_prompt, temperature=0.0)
            mentions: list[str] = mentions_raw if isinstance(mentions_raw, list) else []
        except Exception as e:
            log_audit_event(conn, "extraction", str(doc_id), "pass1_error", "system", {"error": str(e)})
            continue

        # ── Pass 2: structure each mention ─────────────────────────────
        for mention in mentions[:6]:  # cap at 6 key mentions per doc
            pass2_prompt = (
                two_pass_p.PASS2_SYSTEM + "\n\n"
                + two_pass_p.PASS2_USER.format(
                    source_id=str(doc_id),
                    source_type=source_type,
                    timestamp=timestamp,
                    process=process,
                    mention=mention[:500],
                    content=text[:4000],
                )
            )
            try:
                rule = llm.complete_json(pass2_prompt, temperature=0.0)
                if isinstance(rule, dict) and "condition_text" in rule and "action_text" in rule:
                    rule["raw_quote"] = mention
                    _insert_candidate_rule(conn, rule, process, doc_id, "two_pass")
                    total_inserted += 1
            except Exception as e:
                log_audit_event(conn, "extraction", str(doc_id), "pass2_error", "system", {"error": str(e), "mention": mention[:100]})

    log_audit_event(conn, "extraction", process, "two_pass_completed", "system",
                    {"process": process, "docs_processed": total_docs, "rules_inserted": total_inserted})

    return {"method": "two_pass", "process": process, "docs_processed": total_docs, "rules_inserted": total_inserted}


def run_single_pass_extraction(conn, process: str, documents: list[dict]) -> dict:
    """Single-pass baseline — Ablation 1b."""
    llm = get_llm_provider()
    total_inserted = 0

    for doc in documents:
        doc_id = doc["id"]
        text = doc["text"]

        prompt = (
            single_pass_p.SINGLE_PASS_SYSTEM + "\n\n"
            + single_pass_p.SINGLE_PASS_USER.format(
                source_id=str(doc_id),
                source_type=doc["source_type"],
                author=doc["author_handle"] or "unknown",
                timestamp=doc["timestamp"],
                process=process,
                content=text[:8000],
            )
        )
        try:
            rules_raw = llm.complete_json(prompt, temperature=0.0)
            rules: list[dict] = rules_raw if isinstance(rules_raw, list) else []
            for rule in rules[:20]:
                if isinstance(rule, dict) and "condition_text" in rule and "action_text" in rule:
                    _insert_candidate_rule(conn, rule, process, doc_id, "single_pass")
                    total_inserted += 1
        except Exception as e:
            log_audit_event(conn, "extraction", str(doc_id), "single_pass_error", "system", {"error": str(e)})

    log_audit_event(conn, "extraction", process, "single_pass_completed", "system",
                    {"process": process, "rules_inserted": total_inserted})

    return {"method": "single_pass", "process": process, "docs_processed": len(documents), "rules_inserted": total_inserted}
