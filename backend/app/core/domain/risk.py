"""
risk.py

First-draft risk classification for the agent orchestrator (MVP Readiness
Check, item #4). This is domain logic, not config: what makes an action
risky is a judgment call specific to each action type, and it should be
reviewed in code review and covered by tests as the team learns from real
cases — not silently edited in a YAML file.

Operational dollar/severity THRESHOLDS referenced here (e.g. the $100 /
$500 refund cutoffs) DO live in config/config.yaml, since those are pure
operational knobs a non-engineer might reasonably want to tune. This
module reads those thresholds from config and applies the classification
logic around them.
"""

from dataclasses import dataclass
from enum import Enum

from app.config.loader import get_config


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RiskAssessment:
    level: RiskLevel
    reason: str
    requires_approval: bool


# Actions that are always low risk regardless of case details — purely
# informational or easily reversible.
ALWAYS_LOW_RISK_ACTIONS = {"github_add_label", "github_comment", "draft_customer_email"}

# Actions that always require human approval regardless of confidence —
# either irreversible or high real-world consequence.
ALWAYS_HIGH_RISK_ACTIONS = {"declare_sev1_incident", "notion_create_page"}


def classify_risk(
    action_type: str,
    process: str,
    confidence: float,
    amount: float | None = None,
    severity: str | None = None,
) -> RiskAssessment:
    """
    First-draft risk matrix (see master report Section 8 for the agent
    decision loop this feeds into). `amount` is used for refund/pricing
    processes; `severity` is used for incident triage.
    """
    config = get_config()
    risk_cfg = config.get("risk", {})

    if action_type in ALWAYS_LOW_RISK_ACTIONS:
        return RiskAssessment(RiskLevel.LOW, f"{action_type} is always low-risk", requires_approval=False)

    if action_type in ALWAYS_HIGH_RISK_ACTIONS:
        return RiskAssessment(RiskLevel.HIGH, f"{action_type} always requires approval", requires_approval=True)

    if process == "refund_handling" and amount is not None:
        auto_threshold = risk_cfg.get("refund_auto_threshold", 100)
        approval_threshold = risk_cfg.get("refund_approval_threshold", 500)

        if amount > approval_threshold:
            return RiskAssessment(RiskLevel.HIGH, f"refund ${amount} exceeds ${approval_threshold} approval threshold", requires_approval=True)

        if any(k in action_type.lower() for k in ["deny", "reject", "refuse"]):
            return RiskAssessment(RiskLevel.LOW, f"{action_type} is standard policy denial, no payout", requires_approval=False)

        if amount <= auto_threshold and confidence >= risk_cfg.get("refund_auto_min_confidence", 0.75):
            return RiskAssessment(RiskLevel.LOW, f"refund ${amount} <= auto threshold ${auto_threshold}, confidence {confidence}", requires_approval=False)
        elif amount <= approval_threshold:
            return RiskAssessment(RiskLevel.MEDIUM, f"refund ${amount} within ${auto_threshold}-${approval_threshold} band", requires_approval=True)
        else:
            return RiskAssessment(RiskLevel.HIGH, f"refund ${amount} exceeds ${approval_threshold} approval threshold", requires_approval=True)

    if process == "incident_triage" and severity is not None:
        if severity.lower() in ("sev1", "sev-1", "critical", "high"):
            return RiskAssessment(RiskLevel.HIGH, f"severity={severity} requires human approval", requires_approval=True)
        return RiskAssessment(RiskLevel.LOW, f"severity={severity} is auto-actionable", requires_approval=False)

    if process == "pricing_exceptions" and amount is not None:
        auto_threshold = risk_cfg.get("pricing_auto_threshold", 15)  # e.g. discount %
        if amount <= auto_threshold:
            return RiskAssessment(RiskLevel.LOW, f"discount {amount}% <= auto threshold {auto_threshold}%", requires_approval=False)
        return RiskAssessment(RiskLevel.MEDIUM, f"discount {amount}% exceeds auto threshold {auto_threshold}%", requires_approval=True)

    # Unknown/unclassified action or missing required fields — fail safe.
    return RiskAssessment(RiskLevel.HIGH, "unclassified action or missing case fields — failing safe", requires_approval=True)
