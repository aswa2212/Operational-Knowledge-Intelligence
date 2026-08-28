"""
authority_scoring.py

Dynamic Authority & Role Verification Engine for OKI.

Computes auditable authority scores (0.0 to 1.0) using:
  1. Verified Directory / Database Lookups (author_profiles table)
  2. Platform-Native Metadata (Slack is_admin/is_owner/title, GitHub author_association, Notion roles)
  3. 5-Tier Organizational Hierarchy NLP & Title Classification
  4. Delegated / Quoted Authority Extraction ("Approved by VP", "Per Leadership")
  5. Source Formality & Linguistic Phrasing Modifiers
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from typing import Optional

from app.core.domain.entities import NormalizedDocument, SourceType


@dataclass
class AuthorityResult:
    inferred_role: str
    authority_score: float  # 0.0 - 1.0
    basis: str  # Detailed human-readable audit trail explanation


# ── 5-Tier Role Hierarchy & Base Authority Weights ───────────────────────────
ROLE_TIER_SCORES: dict[str, float] = {
    "executive": 0.95,  # CEO, CTO, VP, Head of, Director, Founder, Admin/Owner
    "manager": 0.85,    # Manager, Team Lead, Engineering Lead, Supervisor, Principal
    "senior": 0.70,     # Senior Engineer, Specialist, Architect, Codeowner
    "staff": 0.50,      # Software Engineer, Support Agent, Associate, Contributor
    "guest": 0.25,      # Intern, Contractor, Guest, External
}

# Source-type baseline contribution
SOURCE_TYPE_BASE_SCORE: dict[SourceType, float] = {
    SourceType.POLICY_DOC: 0.55,   # Notion policy pages: formal documentation
    SourceType.TICKET: 0.35,       # GitHub issues/tickets: moderate formality
    SourceType.EMAIL: 0.35,
    SourceType.CHAT: 0.20,         # Slack messages: conversational
}

# Phrasing cues that adjust authority
STRONG_PHRASING_CUES: dict[str, float] = {
    "per policy": 0.20,
    "approved by": 0.25,
    "effective immediately": 0.20,
    "official policy": 0.20,
    "must": 0.10,
    "required": 0.10,
    "policy states": 0.20,
    "signed off by": 0.25,
}

WEAK_PHRASING_CUES: dict[str, float] = {
    "fyi": -0.15,
    "i think": -0.15,
    "not sure but": -0.20,
    "for now": -0.10,
    "just heard": -0.15,
    "someone said": -0.20,
    "maybe": -0.10,
}

TEMPORAL_CUES = ["for now", "temporary", "this week", "until", "for the next", "as of today", "for today only"]
HIGH_AUTHORITY_CHANNEL_HINTS = ["exec", "leadership", "policy-updates", "announcements", "all-hands"]


# ── Title & Role NLP Classifier ──────────────────────────────────────────────

_EXECUTIVE_PATTERN = re.compile(
    r"\b(ceo|cto|coo|cfo|cpo|chief|officer|vp|vice president|head of|director|founder|co-founder|president|principal|owner|executive)\b",
    re.IGNORECASE,
)
_MANAGER_PATTERN = re.compile(
    r"\b(manager|lead|team lead|engineering lead|supervisor|staff engineer|tech lead|scrum master)\b",
    re.IGNORECASE,
)
_SENIOR_PATTERN = re.compile(
    r"\b(senior|sr\.|specialist|architect|codeowner|lead maintainer|tier 2|tier 3)\b",
    re.IGNORECASE,
)
_GUEST_PATTERN = re.compile(
    r"\b(intern|contractor|guest|external|freelance|temporary)\b",
    re.IGNORECASE,
)


def classify_title_tier(title: str | None) -> tuple[str, float, str]:
    """
    Classify job title into (tier_name, base_authority, explanation).
    """
    if not title:
        return "staff", ROLE_TIER_SCORES["staff"], "default staff baseline"

    t = title.strip()
    if _EXECUTIVE_PATTERN.search(t):
        return "executive", ROLE_TIER_SCORES["executive"], f"title '{t}' matches Executive tier"
    if _MANAGER_PATTERN.search(t):
        return "manager", ROLE_TIER_SCORES["manager"], f"title '{t}' matches Manager/Lead tier"
    if _SENIOR_PATTERN.search(t):
        return "senior", ROLE_TIER_SCORES["senior"], f"title '{t}' matches Senior tier"
    if _GUEST_PATTERN.search(t):
        return "guest", ROLE_TIER_SCORES["guest"], f"title '{t}' matches Guest/Intern tier"

    return "staff", ROLE_TIER_SCORES["staff"], f"title '{t}' mapped to Staff tier"


def evaluate_platform_metadata(metadata: dict) -> tuple[Optional[str], Optional[float], list[str]]:
    """
    Extract authority cues from native platform metadata (Slack/GitHub/Notion).
    """
    cues = []
    tier = None
    score = None

    # Slack metadata
    if metadata.get("is_owner") or metadata.get("is_primary_owner"):
        tier = "executive"
        score = 0.98
        cues.append("slack_workspace_owner:+0.98")
    elif metadata.get("is_admin"):
        tier = "manager"
        score = 0.88
        cues.append("slack_workspace_admin:+0.88")

    # GitHub author_association
    assoc = (metadata.get("author_association") or "").upper()
    if assoc == "OWNER":
        tier = "executive"
        score = 0.95
        cues.append("github_repo_owner:+0.95")
    elif assoc in ["MEMBER", "COLLABORATOR"]:
        tier = "senior" if assoc == "MEMBER" else "staff"
        score = 0.75 if assoc == "MEMBER" else 0.60
        cues.append(f"github_association_{assoc.lower()}:{score:+.2f}")
    elif assoc in ["CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "NONE"]:
        tier = "guest"
        score = 0.35
        cues.append(f"github_association_{assoc.lower()}:+0.35")

    # Notion metadata
    if metadata.get("workspace_role") == "workspace_admin":
        tier = "executive"
        score = 0.95
        cues.append("notion_workspace_admin:+0.95")

    return tier, score, cues


def extract_delegated_authority(text_lower: str) -> tuple[Optional[str], Optional[float], Optional[str]]:
    """
    Detects if the text attributes or delegates policy authority to leadership.
    e.g. 'approved by VP of Operations', 'per CTO decision'.
    """
    if "approved by vp" in text_lower or "per vp" in text_lower or "vp approved" in text_lower or "leadership approved" in text_lower:
        return "executive", 0.92, "delegated quote from VP/Leadership"
    if "approved by manager" in text_lower or "per manager" in text_lower or "lead approved" in text_lower:
        return "manager", 0.82, "delegated quote from Manager/Lead"
    if "approved by director" in text_lower or "per director" in text_lower:
        return "executive", 0.92, "delegated quote from Director"
    return None, None, None


# ── Master Inferred Authority Resolver ──────────────────────────────────────

def infer_authority(
    document: NormalizedDocument,
    db_conn=None,
    known_authors: dict[str, str] | None = None
) -> AuthorityResult:
    """
    Infers the verified authority score (0.0 to 1.0) and full audit trail for a document.
    """
    basis_parts = []
    text_lower = document.content.lower()
    meta = {}
    if hasattr(document, "metadata") and isinstance(document.metadata, dict):
        meta = document.metadata
    elif hasattr(document, "metadata_json") and document.metadata_json:
        try:
            meta = json.loads(document.metadata_json) if isinstance(document.metadata_json, str) else document.metadata_json
        except Exception:
            meta = {}

    inferred_role = "staff"
    role_score = ROLE_TIER_SCORES["staff"]

    # 1. Check Database Org Directory (author_profiles)
    db_profile = None
    if db_conn and document.author:
        try:
            row = db_conn.execute("SELECT * FROM author_profiles WHERE handle = ?", (document.author,)).fetchone()
            if row:
                db_profile = dict(row)
        except Exception:
            pass

    if db_profile and db_profile.get("is_verified"):
        inferred_role = db_profile.get("inferred_role_tier", "staff")
        role_score = float(db_profile.get("base_authority", 0.50))
        basis_parts.append(f"verified_author_profile({inferred_role}):{role_score:.2f}")
    elif db_profile:
        inferred_role = db_profile.get("inferred_role_tier", "staff")
        role_score = float(db_profile.get("base_authority", 0.50))
        basis_parts.append(f"saved_author_profile({inferred_role}):{role_score:.2f}")
    elif known_authors and document.author in known_authors:
        inferred_role = known_authors[document.author]
        _, role_score, exp = classify_title_tier(inferred_role)
        basis_parts.append(f"known_author({inferred_role}):{role_score:.2f}")
    else:
        # 2. Check Platform Metadata (Slack is_admin, GitHub OWNER, etc.)
        plat_tier, plat_score, plat_cues = evaluate_platform_metadata(meta)
        if plat_score is not None:
            inferred_role = plat_tier or "staff"
            role_score = plat_score
            basis_parts.extend(plat_cues)
        else:
            # 3. Check Author Role / Title String
            raw_title = document.author_role if document.author_role != "Unknown" else meta.get("author_role") or meta.get("job_title")
            inferred_role, role_score, title_exp = classify_title_tier(raw_title)
            basis_parts.append(f"title_nlp({inferred_role}):{role_score:.2f}")

    # 4. Check Delegated Authority Quotes
    del_tier, del_score, del_exp = extract_delegated_authority(text_lower)
    if del_score is not None and del_score > role_score:
        inferred_role = f"{del_tier} (delegated)"
        role_score = del_score
        basis_parts.append(f"{del_exp}:+{del_score:.2f}")

    # 5. Combine with Source Type & Linguistic Phrasing Modifiers
    src_base = SOURCE_TYPE_BASE_SCORE.get(document.source_type, 0.20)
    
    # Anchor score on the verified/inferred role authority, with source-type formality adjustment
    formality_delta = (src_base - 0.35) * 0.25
    score = role_score + formality_delta
    basis_parts.append(f"source_type={document.source_type.value}:{src_base:.2f}({formality_delta:+.2f})")

    # Phrasing Modifiers
    for cue, weight in STRONG_PHRASING_CUES.items():
        if cue in text_lower:
            score += weight * 0.4  # scaled modifier
            basis_parts.append(f"phrase '{cue}':{weight * 0.4:+.2f}")

    for cue, weight in WEAK_PHRASING_CUES.items():
        if cue in text_lower:
            score += weight * 0.4  # scaled modifier
            basis_parts.append(f"phrase '{cue}':{weight * 0.4:+.2f}")

    # Channel Context
    if document.thread_context:
        channel = document.thread_context.lower()
        if any(hint in channel for hint in HIGH_AUTHORITY_CHANNEL_HINTS):
            score += 0.08
            basis_parts.append(f"high_authority_channel '{document.thread_context}':+0.08")

    final_score = max(0.10, min(1.0, round(score, 2)))

    return AuthorityResult(
        inferred_role=inferred_role,
        authority_score=final_score,
        basis=" | ".join(basis_parts),
    )


def is_temporal(document: NormalizedDocument) -> bool:
    """Pre-check for temporal markers in document text."""
    text_lower = document.content.lower()
    return any(cue in text_lower for cue in TEMPORAL_CUES)
