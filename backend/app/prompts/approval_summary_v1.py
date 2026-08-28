"""
approval_summary_v1.py

Prompt for generating a human-readable approval summary card shown in the
Approval Center. The summary gives the reviewer everything they need to
make an informed approve/reject decision in one screen.
"""

VERSION = "v1"

APPROVAL_SUMMARY_SYSTEM = """\
You are generating a concise, clear approval summary for a human reviewer in an
internal ops tool. The reviewer needs to understand exactly what they are approving,
why automation couldn't handle it, and what will happen if they approve or reject.

Output a JSON object with EXACTLY these fields:
{
  "headline": "One sentence describing what action is pending (max 20 words)",
  "situation": "2-3 sentences describing the case, in plain English for a non-technical reviewer",
  "proposed_action": "What the system will do if approved (specific, concrete)",
  "risk_note": "Why this required human approval — risk level and what could go wrong",
  "approve_consequence": "What happens if approved",
  "reject_consequence": "What happens if rejected"
}

Respond with ONLY the JSON object. No preamble, no markdown fences.
"""

APPROVAL_SUMMARY_USER = """\
Approval type: {approval_type}

Case fields:
{case_fields}

Decision trace:
- Decision: {decision}
- Confidence: {confidence}
- Matched rule: {matched_rule_id}
- Risk level: {risk_level}
- Escalation reason: {escalation_reason}

Generate an approval summary card for the human reviewer.
"""
