"""
schema.py

Pydantic models for every structured artifact in the OKI pipeline:
normalized documents, candidate rules extracted by the LLM, resolved
rules, and the final versioned skills file.

Every module downstream (extraction, resolution, skills_builder, agent)
should import from here rather than passing around raw dicts, so a
malformed LLM output fails loudly at the boundary instead of silently
corrupting a skills file.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Layer: Ingestion
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    TICKET = "ticket"
    POLICY_DOC = "policy_doc"


class NormalizedDocument(BaseModel):
    source_id: str
    source_type: SourceType
    content: str
    author: str
    author_role: str = "Unknown"  # e.g. "VP", "Director", "Manager", "Team Lead", "IC"
    timestamp: datetime
    thread_context: Optional[str] = None
    metadata: dict = Field(default_factory=dict)



# ---------------------------------------------------------------------------
# Layer: Extraction
# ---------------------------------------------------------------------------

class CandidateRule(BaseModel):
    """Output of Pass 2 extraction, before conflict resolution."""
    condition_text: str          # human-readable condition, e.g. "days_since_purchase <= 30"
    action_text: str             # human-readable action, e.g. "approve_refund"
    exceptions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    source_id: str
    source_date: datetime
    reasoning: Optional[str] = None
    corroboration_count: int = 1
    source_document: Optional[NormalizedDocument] = None


# ---------------------------------------------------------------------------
# Layer: Conflict Resolution
# ---------------------------------------------------------------------------

class AuthorityLevel(str, Enum):
    VP = "VP"
    DIRECTOR = "Director"
    MANAGER = "Manager"
    TEAM_LEAD = "Team Lead"
    IC = "Individual Contributor"
    UNKNOWN = "Unknown"


AUTHORITY_SCORES: dict[AuthorityLevel, float] = {
    AuthorityLevel.VP: 1.0,
    AuthorityLevel.DIRECTOR: 0.85,
    AuthorityLevel.MANAGER: 0.70,
    AuthorityLevel.TEAM_LEAD: 0.60,
    AuthorityLevel.IC: 0.40,
    AuthorityLevel.UNKNOWN: 0.30,
}

# Default resolution weights, as documented in the final report.
RESOLUTION_WEIGHTS = {
    "recency": 0.35,
    "authority": 0.40,
    "corroboration": 0.15,
    "override_bonus": 0.10,
}

CONFLICT_CONFIDENCE_THRESHOLD = 0.70


class RuleStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CONFLICT_UNRESOLVED = "conflict_unresolved"
    STALE = "stale"
    DEPRECATED = "deprecated"


class Provenance(BaseModel):
    primary_source: str
    supporting_sources: list[str] = Field(default_factory=list)
    corroboration_count: int = 1
    first_seen: datetime
    last_corroborated: datetime
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: Optional[str] = None


class Condition(BaseModel):
    """
    A single comparison (field/operator/value) or a nested and/or group.
    Nested conditions let a rule express e.g.
    (days_since_purchase > 30) AND (customer_tier == 'VIP').
    """
    field: Optional[str] = None
    operator: Optional[Literal["lte", "lt", "gte", "gt", "equals", "not_equals", "and", "or"]] = None
    value: Optional[Union[str, int, float]] = None
    conditions: Optional[list["Condition"]] = None  # used when operator is "and"/"or"


Condition.model_rebuild()


class Action(BaseModel):
    type: str  # e.g. "approve_refund", "escalate_to_manager", "route_to_oncall"
    parameters: dict = Field(default_factory=dict)


class ResolvedRule(BaseModel):
    id: str
    status: RuleStatus = RuleStatus.ACTIVE
    condition: Condition
    action: Action
    provenance: Provenance
    confidence: float = Field(ge=0.0, le=1.0)
    exceptions: list[dict] = Field(default_factory=list)
    note: Optional[str] = None


class FlaggedConflict(BaseModel):
    """An unresolved contradiction routed to human review instead of guessed."""
    rule_a_id: str
    rule_b_id: str
    reason: str
    resolution_confidence: float
    condition_overlap: str


# ---------------------------------------------------------------------------
# Layer: Skills File
# ---------------------------------------------------------------------------

class EscalationTrigger(str, Enum):
    NO_RULE_MATCHES = "no_rule_matches"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    CONFLICTING_RULES_ACTIVE = "conflicting_rules_active"


class EscalationRule(BaseModel):
    id: str
    trigger: EscalationTrigger
    action: str = "escalate_to_human"
    target_role: str
    reason: str
    threshold: Optional[float] = None
    include_best_guess: bool = True


class ChangelogEntry(BaseModel):
    version: int
    date: datetime
    changes: str


class MaintenanceConfig(BaseModel):
    staleness_check_enabled: bool = True
    max_age_without_corroboration_days: int = 90
    action_on_stale: str = "flag_for_review"
    version_history: list[ChangelogEntry] = Field(default_factory=list)


class SkillsFile(BaseModel):
    process_name: str
    version: int = 1
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    description: str = ""
    rules: list[ResolvedRule] = Field(default_factory=list)
    escalation_rules: list[EscalationRule] = Field(default_factory=list)
    maintenance: MaintenanceConfig = Field(default_factory=MaintenanceConfig)
    flagged_conflicts: list[FlaggedConflict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Layer: Execution
# ---------------------------------------------------------------------------

class CaseInput(BaseModel):
    """A new incoming case to be decided against a skills file."""
    case_id: str
    process_name: str
    fields: dict  # e.g. {"days_since_purchase": 40, "customer_tier": "VIP"}


class DecisionOutput(BaseModel):
    case_id: str
    decision: Optional[str] = None
    matched_rule_id: Optional[str] = None
    source_citation: Optional[str] = None
    confidence: Optional[float] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    best_guess: Optional[str] = None
