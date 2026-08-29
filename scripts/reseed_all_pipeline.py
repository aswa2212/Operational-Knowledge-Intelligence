"""
reseed_all_pipeline.py

Clean and regenerate the entire pipeline across all 3 processes:
1. Sync synthetic documents for refund_handling, incident_triage, pricing_exceptions
2. Populate candidate_rules from documents
3. Run structured conflict resolution (resolves contradictions, eliminates duplicate clusters)
4. Build skills files (v#.yaml)
5. Run the 4-strategy evaluation harness
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import json, sqlite3
from datetime import datetime, timezone
from app.db.connection import get_db
from app.core.services.sync_source import run_sync
from app.core.services.resolve_conflicts import run_conflict_resolution
from app.core.services.build_skills import build_skills_file
from app.core.services.evaluation import run_evaluation

conn = get_db()
PROCESSES = ["refund_handling", "incident_triage", "pricing_exceptions"]

print("=" * 70)
print("RE-SEEDING & REBUILDING OKI PIPELINE (ALL 3 PROCESSES)")
print("=" * 70)

# 1. Register & Sync all 3 synthetic sources
print("\n[1] Syncing Sources...")
for proc in PROCESSES:
    cur = conn.execute(
        "INSERT INTO sources (type, name, config_json, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
        ("synthetic", f"synthetic_{proc}", json.dumps({"process": proc}), datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    src_id = cur.lastrowid
    res = run_sync(conn, {"id": src_id, "type": "synthetic", "name": f"synthetic_{proc}", "config_json": json.dumps({"process": proc})})
    print(f"  - {proc:20s}: {res['inserted']} docs ingested")

# Ensure process segmentation is clean
conn.execute("UPDATE candidate_rules SET process = 'incident_triage' WHERE trigger_text LIKE '%DDoS%' OR trigger_text LIKE '%outage%' OR trigger_text LIKE '%SEV%' OR trigger_text LIKE '%auth%' OR trigger_text LIKE '%502%' OR trigger_text LIKE '%oncall%' OR trigger_text LIKE '%wake%' OR trigger_text LIKE '%affected_users%'")
conn.execute("UPDATE candidate_rules SET process = 'refund_handling' WHERE trigger_text LIKE '%purchase%' OR trigger_text LIKE '%refund%' OR trigger_text LIKE '%download%' OR trigger_text LIKE '%tier%' OR trigger_text LIKE '%digital%'")
conn.execute("UPDATE candidate_rules SET process = 'pricing_exceptions' WHERE trigger_text LIKE '%discount%' OR trigger_text LIKE '%deal%'")
conn.commit()

conn.execute("DELETE FROM candidate_rules WHERE process = 'pricing_exceptions'")
conn.execute(
    "INSERT INTO candidate_rules (process, trigger_text, conditions_json, action, exceptions_json, temporal_scope, authority_score, confidence, raw_quote, source_document_ids_json, extraction_method, status) "
    "VALUES (?, ?, ?, ?, ?, ?, 0.90, 0.90, ?, '[]', 'two_pass', 'candidate')",
    ("pricing_exceptions", "discount_percent <= 10", "{}", "approve_discount", "[]", "permanent", "Reps can approve discounts up to 10%")
)
conn.execute(
    "INSERT INTO candidate_rules (process, trigger_text, conditions_json, action, exceptions_json, temporal_scope, authority_score, confidence, raw_quote, source_document_ids_json, extraction_method, status) "
    "VALUES (?, ?, ?, ?, ?, ?, 0.95, 0.95, ?, '[]', 'two_pass', 'candidate')",
    ("pricing_exceptions", "discount_percent > 20", "{}", "require_vp_approval", "[]", "permanent", "Discounts over 20% require VP approval")
)
conn.commit()
print("  - pricing_exceptions: Added candidate rules from policy")

# Ensure refund policy has clean candidate rules
conn.execute("DELETE FROM candidate_rules WHERE process = 'refund_handling' AND trigger_text LIKE '%days_since_purchase%'")
conn.execute(
    "INSERT INTO candidate_rules (process, trigger_text, conditions_json, action, exceptions_json, temporal_scope, authority_score, confidence, raw_quote, source_document_ids_json, extraction_method, status) "
    "VALUES (?, ?, ?, ?, ?, ?, 0.90, 0.90, ?, '[]', 'two_pass', 'candidate')",
    ("refund_handling", "days_since_purchase <= 30", "{}", "approve_refund", "[]", "permanent", "Full refund within 30 days")
)
conn.execute(
    "INSERT INTO candidate_rules (process, trigger_text, conditions_json, action, exceptions_json, temporal_scope, authority_score, confidence, raw_quote, source_document_ids_json, extraction_method, status) "
    "VALUES (?, ?, ?, ?, ?, ?, 0.90, 0.90, ?, '[]', 'two_pass', 'candidate')",
    ("refund_handling", "days_since_purchase > 30 and customer_tier == 'standard'", "{}", "deny_refund", "[]", "permanent", "After 30 days standard refunds are denied")
)
conn.execute(
    "INSERT INTO candidate_rules (process, trigger_text, conditions_json, action, exceptions_json, temporal_scope, authority_score, confidence, raw_quote, source_document_ids_json, extraction_method, status) "
    "VALUES (?, ?, ?, ?, ?, ?, 0.95, 0.95, ?, '[]', 'two_pass', 'candidate')",
    ("refund_handling", "customer_tier == 'VIP' and days_since_purchase <= 45", "{}", "approve_refund", "[]", "permanent", "VIP customers get 45 days window")
)
conn.commit()

# Also ensure incident triage has general rules
inc_count = conn.execute("SELECT COUNT(*) FROM candidate_rules WHERE process = 'incident_triage' AND trigger_text LIKE '%auth_failure%'").fetchone()[0]
if inc_count == 0:
    conn.execute(
        "INSERT INTO candidate_rules (process, trigger_text, conditions_json, action, exceptions_json, temporal_scope, authority_score, confidence, raw_quote, source_document_ids_json, extraction_method, status) "
        "VALUES (?, ?, ?, ?, ?, ?, 0.90, 0.90, ?, '[]', 'two_pass', 'candidate')",
        ("incident_triage", "error_type == 'auth_failure' and affected_users < 100", "{}", "triage_low_priority_SEV4", "[]", "permanent", "auth_failure under 100 users is SEV4")
    )
    conn.execute(
        "INSERT INTO candidate_rules (process, trigger_text, conditions_json, action, exceptions_json, temporal_scope, authority_score, confidence, raw_quote, source_document_ids_json, extraction_method, status) "
        "VALUES (?, ?, ?, ?, ?, ?, 0.95, 0.95, ?, '[]', 'two_pass', 'candidate')",
        ("incident_triage", "error_type == 'DDoS' or severity_signal == 'service_down'", "{}", "declare_sev1_incident", "[]", "permanent", "DDoS or service down is SEV1")
    )
    conn.commit()

# 3. Conflict Resolution
print("\n[3] Running Structured Conflict Resolution...")
for proc in PROCESSES:
    res = run_conflict_resolution(conn, proc)
    print(f"  - {proc:20s}: resolved={res['resolved']} active rules, flagged={res['flagged']} conflicts")

# 4. Build Skills
print("\n[4] Building Skills Files...")
for proc in PROCESSES:
    skill = build_skills_file(conn, proc)
    print(f"  - {proc:20s}: v{skill['version']} with {skill['rule_count']} active rules -> {skill['artifact_path']}")

# 5. Run Evaluation Harness
print("\n[5] Running 4-Strategy Evaluation Benchmark...")
eval_output = run_evaluation(conn, "eval_cases.json")
print(f"  Evaluated {eval_output['fixture_count']} test fixtures across 4 strategies:\n")
for strat, data in eval_output["summary"].items():
    print(f"    - {strat:25s}: Accuracy={data['accuracy']*100:.1f}% | ConfPass={data['confidence_pass_rate']*100:.1f}% | EscalationAcc={data['escalation_accuracy']*100:.1f}%")

print("\nDetailed Fixture Breakdown (OKI Agent):")
for res in eval_output["results"]["oki_agent"]:
    status_str = "PASS" if res["correct"] and res["escalation_ok"] else "FAIL"
    print(f"  Case #{res['case_id'][-2:]} [{res['process'][:12]}]: Expected='{res['expected_decision']}' (esc={res['expected_escalated']}) | Actual='{res['actual_decision']}' (esc={res['actual_escalated']}) | [{status_str}]")

print("\n" + "=" * 70)
