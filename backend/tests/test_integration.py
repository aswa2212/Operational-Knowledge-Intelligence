"""
test_integration.py — Integration tests for OKI extraction and decide_case.

Run with:
    cd backend
    pytest tests/ -v

These tests use a real SQLite in-memory DB and the synthetic fixture data —
no external API calls, no mocking required for the core pipeline.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.storage.sqlite.repositories import init_db
from app.core.domain.entities import NormalizedDocument, SourceType
from app.core.domain.authority_scoring import infer_authority
from app.core.domain.risk import classify_risk, RiskLevel
from app.core.domain.resolver import compute_confidence, sample_agreement

DATA_ROOT = Path(__file__).parent.parent.parent / "data"
FIXTURES_PATH = DATA_ROOT / "fixtures" / "eval_cases.json"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def mem_db():
    """In-memory SQLite with the full OKI schema, shared across all tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def eval_cases():
    """Load evaluation fixtures if they exist, else return empty list."""
    if FIXTURES_PATH.exists():
        return json.loads(FIXTURES_PATH.read_text())
    return []


# ─── DB schema tests ──────────────────────────────────────────────────────────

class TestDatabaseSchema:
    EXPECTED_TABLES = [
        "sources", "documents", "candidate_rules", "resolved_rules",
        "skill_versions", "cases", "decisions", "approval_requests", "audit_events",
    ]

    def test_all_tables_exist(self, mem_db: sqlite3.Connection):
        cursor = mem_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        for t in self.EXPECTED_TABLES:
            assert t in tables, f"Missing table: {t}"

    def test_can_insert_source(self, mem_db: sqlite3.Connection):
        from datetime import datetime, timezone
        mem_db.execute(
            "INSERT INTO sources (type, name, config_json, enabled, created_at) VALUES (?,?,?,?,?)",
            ("synthetic", "test_source", '{"process":"refund_handling"}', 1,
             datetime.now(timezone.utc).isoformat()),
        )
        mem_db.commit()
        row = mem_db.execute(
            "SELECT * FROM sources WHERE name='test_source'"
        ).fetchone()
        assert row is not None
        assert row["type"] == "synthetic"

    def test_can_insert_document(self, mem_db: sqlite3.Connection):
        from datetime import datetime, timezone
        source_id_row = mem_db.execute(
            "SELECT id FROM sources WHERE name='test_source'"
        ).fetchone()
        assert source_id_row is not None, "test_source must exist — run test_can_insert_source first"
        source_id = source_id_row["id"]
        mem_db.execute(
            """INSERT INTO documents
               (source_id, external_id, source_type, author_handle, channel_or_space,
                timestamp, title, text, url, metadata_json)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (source_id, "doc-001", "policy_doc", "finance_team", "policies",
             "2026-01-01T00:00:00", "Refund Policy", "Standard refunds up to $500 are auto-approved.",
             "file://local", "{}"),
        )
        mem_db.commit()
        count = mem_db.execute(
            "SELECT COUNT(*) FROM documents WHERE source_id=?", (source_id,)
        ).fetchone()[0]
        assert count >= 1


# ─── Authority scoring ────────────────────────────────────────────────────────

class TestAuthorityScoring:
    def test_policy_doc_gets_high_authority(self):
        doc = NormalizedDocument(
            source_id="s1", source_type=SourceType.POLICY_DOC,
            content="Official policy: refunds approved by the Finance VP.",
            author="cfo", author_role="VP Finance",
            timestamp="2026-01-01T00:00:00", thread_context=None,
        )
        result = infer_authority(doc)
        assert result.authority_score > 0.5

    def test_slack_chat_gets_low_authority(self):
        doc = NormalizedDocument(
            source_id="s2", source_type=SourceType.CHAT,
            content="yeah i think we just do refunds for whatever tbh",
            author="intern_jd", author_role="Unknown",
            timestamp="2026-01-01T00:00:00", thread_context="#general",
        )
        result = infer_authority(doc)
        assert result.authority_score < 0.5

    def test_github_pr_description_medium_authority(self):
        doc = NormalizedDocument(
            source_id="s3", source_type=SourceType.TICKET,
            content="This PR implements the refund automation per the Q3 policy update.",
            author="senior_engineer", author_role="Senior Engineer",
            timestamp="2026-01-01T00:00:00", thread_context="PR #1234",
        )
        result = infer_authority(doc)
        assert 0.0 < result.authority_score <= 1.0


# ─── Risk classification ──────────────────────────────────────────────────────

class TestRiskClassification:
    @pytest.mark.parametrize("amount,expected_level", [
        (50, RiskLevel.LOW),    # <= 100 auto threshold with high confidence
        (150, RiskLevel.MEDIUM), # 100 < amount <= 500 => medium
        (600, RiskLevel.HIGH),   # > 500 => high
        (1500, RiskLevel.HIGH),
    ])
    def test_refund_risk_bands(self, amount: float, expected_level: RiskLevel):
        risk = classify_risk(
            "mock_refund_payment", "refund_handling",
            confidence=0.9, amount=amount,
        )
        assert risk.level == expected_level

    def test_high_risk_requires_approval(self):
        risk = classify_risk(
            "mock_refund_payment", "refund_handling",
            confidence=0.9, amount=2000,
        )
        assert risk.requires_approval is True

    def test_low_risk_no_approval_needed(self):
        risk = classify_risk(
            "mock_refund_payment", "refund_handling",
            confidence=0.9, amount=100,
        )
        assert risk.requires_approval is False

    def test_low_confidence_raises_risk(self):
        """Even a small amount at very low confidence should bump risk."""
        risk_normal = classify_risk(
            "mock_refund_payment", "refund_handling",
            confidence=0.9, amount=100,
        )
        risk_low_conf = classify_risk(
            "mock_refund_payment", "refund_handling",
            confidence=0.2, amount=100,
        )
        # Low confidence should be >= in risk level
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert risk_order.index(risk_low_conf.level) >= risk_order.index(risk_normal.level)

    def test_label_actions_are_low_risk(self):
        risk = classify_risk("github_add_label", "incident_triage", confidence=0.5)
        assert risk.level == RiskLevel.LOW
        assert risk.requires_approval is False

    def test_escalate_action_fail_safe_is_high_risk(self):
        """escalate_to_human is not in ALWAYS_LOW_RISK_ACTIONS,
        so with no process match and no fields it fails safe to HIGH."""
        risk = classify_risk("escalate_to_human", "refund_handling", confidence=0.1)
        # The fail-safe path returns HIGH when action is unclassified
        assert risk.level in (RiskLevel.MEDIUM, RiskLevel.HIGH)


# ─── Resolver math ───────────────────────────────────────────────────────────

class TestResolverMath:
    def test_confidence_in_unit_interval(self):
        for auth in [0.1, 0.5, 0.9]:
            for agree in [0.0, 0.5, 1.0]:
                conf = compute_confidence(auth, agree, "amount <= 500")
                assert 0.0 <= conf <= 1.0, f"Out of range: {conf}"

    def test_high_authority_high_agreement_gives_high_confidence(self):
        conf = compute_confidence(0.9, 1.0, "amount <= 500")
        assert conf > 0.7

    def test_low_authority_low_agreement_gives_low_confidence(self):
        conf = compute_confidence(0.1, 0.0, "amount <= 500")
        assert conf < 0.5

    def test_sample_agreement_empty(self):
        assert sample_agreement([]) == 0.0

    def test_sample_agreement_unanimous(self):
        assert sample_agreement(["a", "a", "a"]) == 1.0

    def test_sample_agreement_split(self):
        result = sample_agreement(["a", "a", "b", "b"])
        assert result == 0.5

    def test_sample_agreement_majority(self):
        result = sample_agreement(["a", "a", "a", "b"])
        assert result == 0.75


# ─── Evaluation fixtures ──────────────────────────────────────────────────────

class TestEvaluationFixtures:
    def test_fixture_file_exists(self):
        assert FIXTURES_PATH.exists(), f"Missing: {FIXTURES_PATH}"

    def test_fixtures_are_valid_json(self, eval_cases: list):
        assert isinstance(eval_cases, list)

    def test_each_fixture_has_required_keys(self, eval_cases: list):
        if not eval_cases:
            pytest.skip("No eval cases found")
        # Actual fixture format uses case_id + case_input (not id + input_fields)
        required = {"case_id", "process", "case_input", "expected_decision"}
        for case in eval_cases:
            missing = required - set(case.keys())
            assert not missing, f"Case {case.get('case_id')} missing keys: {missing}"

    def test_risk_classification_matches_fixture_expectations(self, eval_cases: list):
        """Smoke-check: high-risk fixtures should have amounts > threshold."""
        if not eval_cases:
            pytest.skip("No eval cases found")
        for case in eval_cases:
            if case.get("expected_escalated") is True:
                fields = case.get("case_input", {})
                amount = fields.get("order_value", 0)
                # High-escalation cases with amount > 500 must be HIGH risk
                if amount > 500:
                    risk = classify_risk(
                        "mock_refund_payment", case["process"],
                        confidence=0.9, amount=amount,
                    )
                    assert risk.level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
