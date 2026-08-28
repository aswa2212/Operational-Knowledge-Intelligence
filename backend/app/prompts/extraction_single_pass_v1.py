"""
extraction_single_pass_v1.py

Single-pass extraction prompt — Ablation 1b baseline.
One LLM call per document; extracts all candidate rules at once.
Used to compare accuracy vs. the two-pass method.
"""

VERSION = "v1"

SINGLE_PASS_SYSTEM = """\
You are an expert at extracting operational rules from organisational communications.

Your task is to read the provided document and extract ALL business rules, policies,
exceptions, and process decisions it contains — in a single pass.

For each rule you find, output a structured JSON object. Return a JSON array of all rules.

Each rule object must have EXACTLY these fields:
{
  "condition_text": "Human-readable condition, e.g. 'days_since_purchase <= 30'",
  "action_text": "What to do, e.g. 'approve_refund'",
  "exceptions": ["list of exception strings"],
  "temporal_scope": "permanent | temporary | unclear",
  "confidence": 0.0-1.0,
  "raw_quote": "The exact sentence/passage from the document that led to this rule"
}

Rules:
- Extract only rules that are EXPLICITLY stated or strongly implied.
- If none, return an empty array: []
- A rule must have both a condition and an action.
- Informal phrasing counts (e.g. "we approve refunds within 30 days" → condition: days_since_purchase <= 30, action: approve_refund).

Respond with ONLY a JSON array. No preamble, no markdown fences.
"""

SINGLE_PASS_USER = """\
Document source: {source_id} (type: {source_type}, author: {author}, date: {timestamp})
Process: {process}

--- DOCUMENT TEXT ---
{content}
--- END ---

Extract all rules from this document as a JSON array.
"""
