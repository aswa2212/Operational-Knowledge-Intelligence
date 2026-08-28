"""
Run with: pytest tests/ -v (from backend/)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.connectors.synthetic_connector import load_all_sources
from app.core.domain.entities import NormalizedDocument, SourceType
from app.core.domain.authority_scoring import infer_authority
from app.core.domain.risk import classify_risk, RiskLevel
from app.core.domain.resolver import compute_confidence, sample_agreement

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "synthetic" / "refund_handling"


def test_ingestion_loads_sample_documents():
    docs = load_all_sources(DATA_DIR)
    assert len(docs) >= 2
    assert any(d.source_type == SourceType.EMAIL for d in docs)
    assert any(d.source_type == SourceType.POLICY_DOC for d in docs)


def test_authority_scoring_gives_low_score_to_informal_chat():
    doc = NormalizedDocument(
        source_id="s1", source_type=SourceType.CHAT,
        content="fyi someone said we can maybe do this for now",
        author="unknown_user", author_role="Unknown",
        timestamp="2026-07-01T10:00:00", thread_context="#random",
    )
    result = infer_authority(doc)
    assert result.authority_score < 0.4


def test_authority_scoring_gives_higher_score_to_policy_doc():
    doc = NormalizedDocument(
        source_id="s2", source_type=SourceType.POLICY_DOC,
        content="This is the official policy. Approved by finance.",
        author="finance_team", author_role="Unknown",
        timestamp="2026-07-01T10:00:00", thread_context=None,
    )
    result = infer_authority(doc)
    assert result.authority_score > 0.5


def test_risk_classification_low_amount_is_low_risk():
    risk = classify_risk("mock_refund_payment", "refund_handling", confidence=0.9, amount=50)
    assert risk.level == RiskLevel.LOW
    assert risk.requires_approval is False


def test_risk_classification_high_amount_requires_approval():
    risk = classify_risk("mock_refund_payment", "refund_handling", confidence=0.9, amount=1000)
    assert risk.level == RiskLevel.HIGH
    assert risk.requires_approval is True


def test_risk_classification_always_low_risk_actions():
    risk = classify_risk("github_add_label", "incident_triage", confidence=0.5)
    assert risk.level == RiskLevel.LOW


def test_confidence_formula_in_bounds():
    conf = compute_confidence(authority_score=0.7, sample_agreement=0.8, condition_text="amount <= 500")
    assert 0.0 <= conf <= 1.0


def test_sample_agreement_majority():
    assert sample_agreement(["a", "a", "a", "b"]) == 0.75
    assert sample_agreement([]) == 0.0
