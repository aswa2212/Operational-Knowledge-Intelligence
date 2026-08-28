"""
resolver.py

Conflict resolution: the weighted resolver (main method) plus the three
naive-strategy variants used as Ablation 2 comparisons. Also the
sample-agreement confidence formula (MVP Readiness Check item #5).

All of this is domain logic — no FastAPI, no SQLite, no Groq/Ollama
imports here. It operates on plain dataclasses/dicts and pure functions
so it can be unit-tested in isolation and swapped/tuned without touching
anything else in the system.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.domain.authority_scoring import infer_authority
from app.core.domain.entities import CandidateRule

# --- Weighted resolution (main method) --------------------------------

RESOLUTION_WEIGHTS = {
    "recency": 0.35,
    "authority": 0.40,
    "corroboration": 0.15,
    "override_bonus": 0.10,
}

CONFLICT_ACCEPT_MIN_SCORE = 0.70
CONFLICT_ACCEPT_MIN_MARGIN = 0.05


@dataclass
class ScoredRule:
    rule: CandidateRule
    score: float
    breakdown: dict[str, float]


def _make_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _recency_score(rule_date: datetime, all_dates: list[datetime]) -> float:
    """Normalize recency to 0-1 relative to the other candidates in this
    conflict group — the newest gets 1.0, the oldest gets 0.0."""
    if len(all_dates) <= 1:
        return 1.0
    utc_dates = [_make_utc(d) for d in all_dates]
    rule_utc = _make_utc(rule_date)
    oldest, newest = min(utc_dates), max(utc_dates)
    span = (newest - oldest).total_seconds()
    if span == 0:
        return 1.0
    return max(0.0, min(1.0, (rule_utc - oldest).total_seconds() / span))


def _corroboration_score(corroboration_count: int, max_count: int) -> float:
    if max_count <= 1:
        return 1.0 if corroboration_count >= 1 else 0.0
    return min(1.0, corroboration_count / max_count)


def score_weighted(rule: CandidateRule, all_candidates: list[CandidateRule], explicit_override: bool = False) -> ScoredRule:
    """The main resolution method: recency + authority + corroboration +
    explicit override bonus, per the weights above."""
    authority_result = infer_authority(rule.source_document) if (getattr(rule, "source_document", None) is not None) else None
    authority_score = authority_result.authority_score if authority_result else rule.confidence

    all_dates = [r.source_date for r in all_candidates]
    max_corroboration = max((getattr(r, "corroboration_count", 1) for r in all_candidates), default=1)

    recency = _recency_score(rule.source_date, all_dates)
    corroboration = _corroboration_score(getattr(rule, "corroboration_count", 1), max_corroboration)
    override = 1.0 if explicit_override else 0.0

    score = (
        RESOLUTION_WEIGHTS["recency"] * recency
        + RESOLUTION_WEIGHTS["authority"] * authority_score
        + RESOLUTION_WEIGHTS["corroboration"] * corroboration
        + RESOLUTION_WEIGHTS["override_bonus"] * override
    )

    return ScoredRule(
        rule=rule,
        score=round(score, 4),
        breakdown={"recency": recency, "authority": authority_score, "corroboration": corroboration, "override": override},
    )


def resolve_conflict_weighted(candidates: list[CandidateRule]) -> tuple[ScoredRule | None, list[ScoredRule]]:
    """
    Returns (winner, all_scored). winner is None if the top score doesn't
    clear CONFLICT_ACCEPT_MIN_SCORE or doesn't beat the runner-up by
    CONFLICT_ACCEPT_MIN_MARGIN — in that case the caller should create a
    FlaggedConflict / Knowledge Review entry instead of picking one.
    """
    scored = sorted(
        (score_weighted(c, candidates) for c in candidates),
        key=lambda s: s.score,
        reverse=True,
    )
    if not scored:
        return None, []
    if len(scored) == 1:
        return (scored[0] if scored[0].score >= CONFLICT_ACCEPT_MIN_SCORE else None), scored

    best, second = scored[0], scored[1]
    if best.score >= CONFLICT_ACCEPT_MIN_SCORE and (best.score - second.score) >= CONFLICT_ACCEPT_MIN_MARGIN:
        return best, scored
    return None, scored


# --- Naive resolver variants (Ablation 2 comparisons) ------------------

def resolve_most_recent_wins(candidates: list[CandidateRule]) -> CandidateRule | None:
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.source_date)


def resolve_authority_only(candidates: list[CandidateRule]) -> CandidateRule | None:
    if not candidates:
        return None
    scored = [(c, infer_authority(c.source_document).authority_score) for c in candidates if getattr(c, "source_document", None) is not None]
    if not scored:
        return candidates[0]
    return max(scored, key=lambda pair: pair[1])[0]


def resolve_corroboration_only(candidates: list[CandidateRule]) -> CandidateRule | None:
    if not candidates:
        return None
    return max(candidates, key=lambda c: getattr(c, "corroboration_count", 1))


# --- Confidence formula (MVP Readiness Check item #5) -------------------

CONFIDENCE_WEIGHTS = {
    "authority": 0.40,
    "sample_agreement": 0.35,
    "specificity": 0.15,
    "source_credibility": 0.10,
}


def condition_specificity(condition_text: str) -> float:
    """
    Cheap proxy for how specific/well-formed a rule's condition is.
    A condition with explicit comparators and a concrete field/value
    (e.g. "days_since_purchase <= 30") is more specific than a vague
    statement ("refunds should generally be handled fairly"). This is a
    first-draft heuristic — presence of a comparator and a number.
    """
    comparators = ["<=", ">=", "<", ">", "==", "="]
    has_comparator = any(c in condition_text for c in comparators)
    has_number = any(ch.isdigit() for ch in condition_text)
    if has_comparator and has_number:
        return 1.0
    if has_comparator or has_number:
        return 0.6
    return 0.3


def compute_confidence(
    authority_score: float,
    sample_agreement: float,
    condition_text: str,
    source_credibility: float = 0.5,
) -> float:
    """
    sample_agreement: fraction of agreeing samples out of 3-5 LLM calls
    on the same fuzzy-match question (see agent_orchestrator, only run
    for fuzzy/low-confidence/contradiction-sensitive cases per Risk 3).
    """
    specificity = condition_specificity(condition_text)
    confidence = (
        CONFIDENCE_WEIGHTS["authority"] * authority_score
        + CONFIDENCE_WEIGHTS["sample_agreement"] * sample_agreement
        + CONFIDENCE_WEIGHTS["specificity"] * specificity
        + CONFIDENCE_WEIGHTS["source_credibility"] * source_credibility
    )
    return round(max(0.0, min(1.0, confidence)), 4)


def sample_agreement(samples: list[str]) -> float:
    """
    Given N sampled LLM outputs for the same fuzzy-match question,
    return the fraction that agree with the majority answer. E.g.
    5 samples, 4 say "approve" and 1 says "escalate" -> 0.8.
    """
    if not samples:
        return 0.0
    counts: dict[str, int] = {}
    for s in samples:
        counts[s] = counts.get(s, 0) + 1
    majority_count = max(counts.values())
    return round(majority_count / len(samples), 4)
