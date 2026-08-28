"""
extraction_two_pass_v1.py

Two-pass extraction prompts — the main extraction method (Ablation 1a).

Pass 1: identify raw candidate rule mentions in a document.
Pass 2: structure each mention into a typed CandidateRule.
"""

VERSION = "v1"

# ── Pass 1: Mention identification ──────────────────────────────────────────

PASS1_SYSTEM = """\
You are an expert at extracting operational rules from organisational communications.

Your task is to identify ALL sentences or passages in the provided document that state,
imply, or modify a business rule, policy, exception, or process decision.

Rules to follow:
- Include informal statements too (e.g. "we usually do X" or "Sarah said no refunds after 30 days")
- Include contradiction signals (e.g. "actually, the new policy is...")
- Include temporary/conditional rules (e.g. "for this month only, we'll approve...")
- Do NOT infer or generate rules that are not present in the text
- Return your result as a JSON array of strings, one per candidate mention

Respond with ONLY a JSON array. No preamble, no markdown fences.
Example: ["passage 1...", "passage 2...", ...]
"""

PASS1_USER = """\
Document source: {source_id} (type: {source_type}, author: {author}, date: {timestamp})

--- DOCUMENT TEXT ---
{content}
--- END ---

Extract all rule-mentioning passages from this document.
"""

# ── Pass 2: Structuring ──────────────────────────────────────────────────────

PASS2_SYSTEM = """\
You are structuring an informal rule mention from an organisational document into a
precise, machine-readable CandidateRule.

Output a single JSON object with EXACTLY these fields:
{
  "condition_text": "Human-readable condition describing when the rule applies, e.g. 'days_since_purchase <= 30'",
  "action_text": "What to do when the condition is met, e.g. 'approve_refund'",
  "exceptions": ["list of exception strings, e.g. 'unless the item is digital'"],
  "temporal_scope": "permanent | temporary | unclear",
  "confidence": 0.0-1.0,
  "reasoning": "One sentence explaining why you structured it this way"
}

Respond with ONLY the JSON object. No preamble, no markdown.
- If the mention is ambiguous, use a lower confidence (< 0.5).
- If the mention is clearly temporary ("for this quarter", "until Jan"), use temporal_scope = "temporary".
- If there is NO clear action implied, set action_text to "requires_human_decision".
"""

PASS2_USER = """\
Source document: {source_id} (type: {source_type}, date: {timestamp})
Process: {process}

Raw mention to structure:
"{mention}"

Full document context (for disambiguation only — do not extract additional rules from this):
{content}

Structure the mention above into a CandidateRule.
"""
