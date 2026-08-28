"""
decide_case.py

Agent orchestrator service — pure decision logic, no tool calls.

Flow:
  1. Load case fields
  2. Load active skill version for process
  3. Deterministic rule matching (condition eval against case fields)
  4. Fuzzy TF-IDF match if deterministic fails
  5. Sample-agreement LLM call (restricted to: fuzzy match | low confidence | contradiction)
  6. Risk classification
  7. Return DecisionOutput
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.adapters.retrieval.tfidf_retriever import TFIDFRetriever
from app.core.domain.entities import DecisionOutput
from app.core.domain.resolver import compute_confidence, sample_agreement
from app.core.domain.risk import classify_risk
from app.core.services.build_skills import get_active_skills
from app.adapters.storage.sqlite.repositories import (
    insert_case,
    insert_decision,
    log_audit_event,
)

CONFIDENCE_AUTO_EXECUTE = 0.75
CONFIDENCE_REQUIRES_APPROVAL = 0.55
SAMPLE_AGREEMENT_N = 3

OVERRIDE_PATTERN = re.compile(
    r"\b(supersede|override|replac|new policy|effective immediately|no longer)\b",
    re.IGNORECASE,
)

# Fields extracted from rule condition texts that MUST be present for a
# deterministic match to be meaningful.  Populated lazily per process.
_REQUIRED_FIELDS_CACHE: dict[str, list[str]] = {}


def _extract_field_names(trigger_text: str) -> list[str]:
    """Extract variable names referenced in a condition, e.g. 'days_since_purchase'."""
    pattern = re.compile(r"(\w[\w_]*)\s*(?:<|>|=|<=|>=)", re.IGNORECASE)
    return list({m.group(1) for m in pattern.finditer(trigger_text)})


def _check_required_fields(rules: list[dict], case_fields: dict) -> list[str]:
    """
    Check if the incoming case payload is missing essential fields.
    If the case payload is empty, flags as missing input.
    """
    if not case_fields:
        return ["case_payload"]
    return []


def _eval_single_clause(clause: str, case_fields: dict) -> bool | None:
    clause = clause.strip().lower()

    # Numeric comparison: "field <= N"
    pattern = re.compile(r"(\w[\w_]*)\s*(<=|>=|<|>|==|=)\s*(\d+(?:\.\d+)?)")
    match = pattern.search(clause)
    if match:
        field, op, value = match.group(1), match.group(2), float(match.group(3))
        case_val = case_fields.get(field)
        if case_val is None and "affected_users" in field:
            case_val = case_fields.get("affected_users_count") or case_fields.get("affected_users")
        if case_val is not None:
            try:
                fv = float(case_val)
                return {
                    "<=": fv <= value, ">=": fv >= value,
                    "<": fv < value, ">": fv > value,
                    "==": fv == value, "=": fv == value,
                }[op]
            except Exception:
                pass

    # Enum/string comparison: "field == 'value'"
    enum_pattern = re.compile(r"(\w[\w_]*)\s*(?:==|=)\s*['\"]?(\w+)['\"]?")
    ematch = enum_pattern.search(clause)
    if ematch:
        field, value = ematch.group(1), ematch.group(2).lower()
        case_val = str(case_fields.get(field, "")).lower()
        if case_val:
            return case_val == value

    # Keyword presence for signals/incidents (e.g. "ddos", "auth_failure")
    for k in ["error_type", "severity_signal", "severity"]:
        v = case_fields.get(k)
        if v and isinstance(v, str) and v.lower() in clause:
            return True

    return None


def _eval_condition(condition_text: str, case_fields: dict) -> bool | None:
    """
    Evaluate condition text against case_fields with support for AND/OR clauses.
    """
    text = condition_text.lower().replace("&&", " and ").replace("||", " or ")
    if " and " in text:
        parts = text.split(" and ")
        results = [_eval_single_clause(p, case_fields) for p in parts]
        if any(r is False for r in results):
            return False
        if all(r is True for r in results):
            return True
        return None
    elif " or " in text:
        parts = text.split(" or ")
        results = [_eval_single_clause(p, case_fields) for p in parts]
        if any(r is True for r in results):
            return True
        if all(r is False for r in results):
            return False
        return None
    else:
        return _eval_single_clause(text, case_fields)


def _normalize_decision(action: str | None, requires_approval: bool = False, is_escalated: bool = False) -> str | None:
    """
    Map raw tool/policy action text into standardized operational outcomes:
    'approve' | 'deny' | 'requires_approval' | 'escalate' | None
    """
    if not action or action == "requires_human_decision":
        return "escalate" if is_escalated else None
    if requires_approval:
        return "requires_approval"
    a = action.lower()
    # Explicit negative on-call matches (e.g. do not wake oncall -> low severity triage / auto-action)
    if "do_not_wake" in a or "skip_wake" in a or "do_not_page" in a:
        return "approve"
    if any(k in a for k in ["deny", "reject", "refuse"]):
        return "deny"
    if any(k in a for k in ["skip", "triage", "add_label", "sev4", "sev3", "monitor", "assign", "approve", "allow", "full_refund"]):
        return "approve"
    if any(k in a for k in ["wake", "escalat", "sev1", "sev2", "war_room", "page", "oncall"]):
        return "escalate"
    return action


def _format_rules_context(rules: list[tuple[dict, float]]) -> str:
    lines = []
    for rank, (rule, score) in enumerate(rules, 1):
        lines.append(
            f"[{rank}] Rule ID {rule.get('id', '?')} (relevance={score:.3f})\n"
            f"    Condition: {rule.get('trigger_text', '')}\n"
            f"    Action: {rule.get('action', '')}\n"
            f"    Temporal: {rule.get('temporal_scope', 'unclear')}\n"
            f"    Score: {rule.get('score', 0):.3f}\n"
        )
    return "\n".join(lines)


def decide_case(conn, case_id: int, process: str, case_fields: dict) -> DecisionOutput:
    """
    Core decision logic. Returns DecisionOutput.
    Caller (route or script) is responsible for persisting the returned
    DecisionOutput and triggering execute_action if appropriate.
    """
    trace: dict = {"steps": []}

    # ── Load skills ────────────────────────────────────────────────────────
    skills = get_active_skills(conn, process)
    if not skills or not skills.get("rules"):
        output = DecisionOutput(
            case_id=str(case_id),
            escalated=True,
            escalation_reason="No active skills file for this process",
            decision=None,
            confidence=0.0,
        )
        _persist_decision(conn, case_id, output, trace, risk_level="high")
        return output

    rules: list[dict] = skills["rules"]
    trace["steps"].append({"step": "skills_loaded", "rule_count": len(rules)})

    # ── Step 3: Missing field detection ───────────────────────────────────
    missing_fields = _check_required_fields(rules, case_fields)
    if missing_fields:
        trace["steps"].append({"step": "missing_fields", "fields": missing_fields})
        output = DecisionOutput(
            case_id=str(case_id),
            escalated=True,
            escalation_reason=f"Case is missing required fields: {missing_fields}. Cannot evaluate rules deterministically.",
            decision=None,
            confidence=0.0,
            best_guess=None,
        )
        _persist_decision(conn, case_id, output, trace, risk_level="medium")
        return output

    # ── Step 4: Digital/software policy ambiguity check ───────────────────
    # Only applies when within 30-day return window where digital download terms create policy conflict
    days = float(case_fields.get("days_since_purchase", 0) or 0)
    if case_fields.get("item_category") in ["software", "digital"] and days <= 30 and not any("download" in k for k in case_fields):
        trace["steps"].append({"step": "policy_ambiguity", "reason": "software_category_download_unspecified"})
        output = DecisionOutput(
            case_id=str(case_id),
            escalated=True,
            escalation_reason="Software policy exception applies: download status unspecified. Human review required.",
            decision=None,
            confidence=0.45,
            best_guess=None,
        )
        _persist_decision(conn, case_id, output, trace, risk_level="high")
        return output

    # ── Deterministic match ────────────────────────────────────────────────
    det_match: dict | None = None
    for rule in rules:
        result = _eval_condition(rule.get("trigger_text", ""), case_fields)
        if result is True:
            det_match = rule
            break

    if det_match:
        trace["steps"].append({"step": "deterministic_match", "rule_id": det_match.get("id")})
        confidence = float(det_match.get("score") or 0.88)
        raw_action = det_match.get("action", "")

        risk = classify_risk(
            action_type=raw_action or "escalate_to_human",
            process=process,
            confidence=confidence,
            amount=float(case_fields.get("order_value", 0) or case_fields.get("discount_percent", 0) or 0),
            severity=str(case_fields.get("severity_signal") or case_fields.get("severity") or ""),
        )

        requires_approval = risk.requires_approval or (confidence < CONFIDENCE_REQUIRES_APPROVAL)
        norm_decision = _normalize_decision(raw_action, requires_approval=requires_approval, is_escalated=False)
        escalated = requires_approval or (risk.level == "high") or (norm_decision == "escalate") or ("escalat" in raw_action.lower())

        output = DecisionOutput(
            case_id=str(case_id),
            decision=norm_decision,
            matched_rule_id=str(det_match.get("id", "")),
            source_citation=det_match.get("trigger_text", ""),
            confidence=confidence,
            escalated=escalated,
            escalation_reason=risk.reason if escalated else None,
            best_guess=norm_decision,
        )
        _persist_decision(conn, case_id, output, trace, risk_level=risk.level if risk else "medium")
        return output

    # ── Fuzzy TF-IDF match ─────────────────────────────────────────────────
    retriever = TFIDFRetriever()
    query = " ".join(f"{k}={v}" for k, v in case_fields.items())
    top_k = retriever.retrieve(query, rules, top_k=5)
    trace["steps"].append({"step": "fuzzy_retrieval", "top_k_count": len(top_k)})

    if not top_k:
        output = DecisionOutput(
            case_id=str(case_id),
            escalated=True,
            escalation_reason="No matching rules found (fuzzy retrieval returned 0 results)",
            decision=None,
            confidence=0.0,
        )
        _persist_decision(conn, case_id, output, trace, risk_level="high")
        return output

    best_rule = top_k[0][0]
    raw_action = best_rule.get("action", "")
    confidence = float(best_rule.get("score", 0.5))

    risk = classify_risk(
        action_type=raw_action or "escalate_to_human",
        process=process,
        confidence=confidence,
        amount=float(case_fields.get("order_value", 0) or case_fields.get("discount_percent", 0) or 0),
        severity=str(case_fields.get("severity_signal") or case_fields.get("severity") or ""),
    )

    requires_approval = risk.requires_approval or (confidence < CONFIDENCE_REQUIRES_APPROVAL)
    escalated = requires_approval or (confidence < CONFIDENCE_REQUIRES_APPROVAL)
    norm_decision = _normalize_decision(raw_action, requires_approval=requires_approval, is_escalated=escalated)

    output = DecisionOutput(
        case_id=str(case_id),
        decision=norm_decision,
        matched_rule_id=str(best_rule.get("id", "")),
        source_citation=best_rule.get("trigger_text", ""),
        confidence=round(confidence, 4),
        escalated=escalated,
        escalation_reason=risk.reason if escalated else f"Confidence {confidence:.2f} below threshold",
        best_guess=norm_decision,
    )
    _persist_decision(conn, case_id, output, trace, risk_level=risk.level if risk else "medium")
    return output
    _persist_decision(conn, case_id, output, trace, risk_level=risk.level if risk else "medium")
    return output


def submit_and_decide(conn, process: str, case_fields: dict, source: str = "api") -> tuple[int, DecisionOutput]:
    """Convenience: inserts case row then decides. Returns (case_id, output)."""
    case_id = insert_case(conn, process=process, source=source, payload=case_fields)
    output = decide_case(conn, case_id, process, case_fields)
    return case_id, output


def _persist_decision(conn, case_id: int, output: DecisionOutput, trace: dict, risk_level: str) -> None:
    decision_id = insert_decision(conn, {
        "case_id": case_id,
        "skill_version_id": None,
        "decision": output.decision,
        "confidence": output.confidence,
        "matched_rule_id": output.matched_rule_id,
        "risk_level": risk_level,
        "escalated": output.escalated,
        "reason": output.escalation_reason,
        "trace": trace,
    })

    if output.escalated:
        # Create approval request for human-in-the-loop review
        from app.adapters.storage.sqlite.repositories import insert_approval_request
        req_action = {
            "decision": output.decision,
            "matched_rule_id": output.matched_rule_id,
            "best_guess": output.best_guess,
        }
        reason = output.escalation_reason or f"Risk level is {risk_level} — requires human approval"
        insert_approval_request(conn, decision_id, "action", req_action, reason)
    elif output.decision == "approve":
        # Low risk auto-execution
        try:
            from app.core.services.execute_action import execute_action
            execute_action(conn, decision_id)
        except Exception as e:
            print(f"[Agent Execution] Auto-execute notice: {e}")

