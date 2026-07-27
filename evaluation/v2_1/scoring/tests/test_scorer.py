"""
test_scorer.py — Tests for the external evaluation scorer.

Verifies:
1. All 8 check types work correctly (deterministic, no LLM)
2. Pipeline-internal fields (m4_passed, UCS, failure_type) do NOT affect scores
3. Scorer is independent of pipeline modules
4. Real case data produces correct scores
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v2_1.scoring.scorer import (
    _run_check,
    score_one,
    score_ledger,
    aggregate,
    load_gold_cases,
)
from evaluation.v2_1.scoring.score_schema import CHECK_TYPES

PASS = 0
FAIL = 0
ERRORS = []


def run_test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  PASS  {name}")
    except AssertionError as e:
        FAIL += 1
        msg = str(e) if str(e) else "assertion failed"
        print(f"  FAIL  {name}: {msg}")
        ERRORS.append(f"{name}: {msg}")
    except Exception as e:
        FAIL += 1
        print(f"  FAIL  {name}: {type(e).__name__}: {e}")
        ERRORS.append(f"{name}: {type(e).__name__}: {e}")


# ════════════════════════════════════════════════════════════
# Check type tests
# ════════════════════════════════════════════════════════════

def test_substring_absent_passes():
    """substring_absent: target string not found → pass."""
    check = {"check_id": "test", "type": "substring_absent", "value": "forbidden text"}
    passed, _ = _run_check(check, "This is clean text.")
    assert passed is True


def test_substring_absent_fails():
    """substring_absent: target string found → fail."""
    check = {"check_id": "test", "type": "substring_absent", "value": "forbidden text"}
    passed, _ = _run_check(check, "This contains forbidden text here.")
    assert passed is False


def test_regex_present_passes():
    """regex_present: pattern matches → pass."""
    check = {"check_id": "test", "type": "regex_present",
             "pattern": r"30\s*[–-]\s*60\s*minutes"}
    passed, _ = _run_check(check, "Adults need 30–60 minutes per day.")
    assert passed is True


def test_regex_present_fails():
    """regex_present: pattern does not match → fail."""
    check = {"check_id": "test", "type": "regex_present",
             "pattern": r"30\s*[–-]\s*60\s*minutes"}
    passed, _ = _run_check(check, "Adults need 20 minutes per day.")
    assert passed is False


def test_any_phrase_present_passes():
    """any_phrase_present: at least one phrase found → pass."""
    check = {"check_id": "test", "type": "any_phrase_present",
             "values": ["most days", "on most days"]}
    passed, _ = _run_check(check, "Exercise on most days.")
    assert passed is True


def test_any_phrase_present_fails():
    """any_phrase_present: no phrases found → fail."""
    check = {"check_id": "test", "type": "any_phrase_present",
             "values": ["most days", "on most days"]}
    passed, _ = _run_check(check, "Exercise every day.")
    assert passed is False


def test_all_phrase_present_passes():
    """all_phrase_present: all phrases found → pass."""
    check = {"check_id": "test", "type": "all_phrase_present",
             "values": ["improve", "glycemic control"]}
    passed, _ = _run_check(check, "Exercise can improve glycemic control.")
    assert passed is True


def test_all_phrase_present_fails():
    """all_phrase_present: some phrases missing → fail."""
    check = {"check_id": "test", "type": "all_phrase_present",
             "values": ["improve", "glycemic control", "reduce risk"]}
    passed, _ = _run_check(check, "Exercise can improve glycemic control.")
    assert passed is False


def test_phrase_present_passes():
    """phrase_present: single phrase found → pass."""
    check = {"check_id": "test", "type": "phrase_present", "value": "clothing"}
    passed, _ = _run_check(check, "Wear appropriate clothing.")
    assert passed is True


def test_phrase_present_fails():
    """phrase_present: single phrase not found → fail."""
    check = {"check_id": "test", "type": "phrase_present", "value": "clothing"}
    passed, _ = _run_check(check, "Wear warm layers.")
    assert passed is False


def test_any_regex_present_passes():
    """any_regex_present: at least one pattern matches → pass."""
    check = {"check_id": "test", "type": "any_regex_present",
             "patterns": [r"40\s*[–-]\s*59%\s*HRR", r"60\s*[–-]\s*89%\s*HRR"]}
    passed, _ = _run_check(check, "Moderate is 40–59% HRR.")
    assert passed is True


def test_any_regex_present_fails():
    """any_regex_present: no patterns match → fail."""
    check = {"check_id": "test", "type": "any_regex_present",
             "patterns": [r"40\s*[–-]\s*59%\s*HRR", r"60\s*[–-]\s*89%\s*HRR"]}
    passed, _ = _run_check(check, "Use moderate intensity.")
    assert passed is False


def test_all_regex_present_passes():
    """all_regex_present: all patterns match → pass."""
    check = {"check_id": "test", "type": "all_regex_present",
             "patterns": [r"mild discomfort", r"15\s*[–-]\s*30\s*seconds"]}
    passed, _ = _run_check(check, "Move to mild discomfort and hold 15–30 seconds.")
    assert passed is True


def test_all_regex_present_fails():
    """all_regex_present: some patterns missing → fail."""
    check = {"check_id": "test", "type": "all_regex_present",
             "patterns": [r"mild discomfort", r"15\s*[–-]\s*30\s*seconds",
                           r"decrease.*pain"]}
    passed, _ = _run_check(check, "Move to mild discomfort and hold 15–30 seconds.")
    assert passed is False


def test_all_phrase_groups_present_passes():
    """all_phrase_groups_present: each group has a match → pass."""
    check = {"check_id": "test", "type": "all_phrase_groups_present",
             "groups": [["pain"], ["radiating"], ["loss of sensation", "numbness"],
                        ["decrease", "reduce", "stop"]]}
    passed, _ = _run_check(check, "If you feel pain or radiating symptoms, "
                                   "loss of sensation means reduce intensity.")
    assert passed is True


def test_all_phrase_groups_present_fails():
    """all_phrase_groups_present: a group has no match → fail."""
    check = {"check_id": "test", "type": "all_phrase_groups_present",
             "groups": [["pain"], ["radiating"], ["loss of sensation", "numbness"]]}
    passed, _ = _run_check(check, "If you feel pain, stop.")
    assert passed is False


def test_unknown_check_type_raises():
    """Unknown check type raises ValueError."""
    check = {"check_id": "test", "type": "nonexistent_type"}
    try:
        _run_check(check, "some text")
        assert False, "Should raise ValueError"
    except ValueError:
        pass


# ════════════════════════════════════════════════════════════
# Score_one tests with synthetic ledger records
# ════════════════════════════════════════════════════════════

# Build a minimal gold database with one real case (CMC-A-001)
GOLD_SAMPLE = {
    "CMC-A-001": {
        "case_id": "CMC-A-001",
        "primary_checks": [
            {"check_id": "remove_exact_43", "type": "substring_absent",
             "value": "exactly 43 minutes every day"},
            {"check_id": "retain_duration_range", "type": "regex_present",
             "pattern": r"30\s*[–-]\s*60\s*minutes"},
            {"check_id": "retain_frequency_qualifier", "type": "any_phrase_present",
             "values": ["most days", "on most days"]},
        ],
    }
}


def _make_ledger_entry(case_id="CMC-A-001", condition="generic",
                       corrected="Adults need 30–60 minutes on most days.",
                       raw="Most adults should exercise for exactly 43 minutes every day.",
                       **kwargs):
    entry = {
        "run_id": "test",
        "case_id": case_id,
        "condition": condition,
        "raw_response": raw,
        "corrected_response": corrected,
        "included": True,
        # Pipeline-internal fields that SHOULD NOT affect scoring
        "m4_passed": True,
        "needs_calibration": True,
        "failure_type": "cue_leakage",
        "ucs_score": 1,
        "correction_trace": {"something": "internal"},
        "token_usage": {},
    }
    entry.update(kwargs)
    return entry


def test_score_one_generic_pass():
    """score_one: good correction → all checks pass."""
    entry = _make_ledger_entry()
    result = score_one(entry, GOLD_SAMPLE)
    assert result["case_id"] == "CMC-A-001"
    assert result["condition"] == "generic"
    assert result["primary_score"] is True
    assert result["passed"] is True
    assert result["checks"]["remove_exact_43"] is True
    assert result["checks"]["retain_duration_range"] is True
    assert result["checks"]["retain_frequency_qualifier"] is True


def test_score_one_failure_not_removed():
    """score_one: failure still present → fail."""
    entry = _make_ledger_entry(
        corrected="Most adults should exercise for exactly 43 minutes every day."
    )
    result = score_one(entry, GOLD_SAMPLE)
    assert result["primary_score"] is False
    assert result["checks"]["remove_exact_43"] is False


def test_score_one_missing_evidence():
    """score_one: evidence not retained → fail."""
    entry = _make_ledger_entry(corrected="I don't know.")
    result = score_one(entry, GOLD_SAMPLE)
    assert result["primary_score"] is False
    assert result["checks"]["retain_duration_range"] is False


def test_score_one_original_condition():
    """score_one: original condition scores raw_response."""
    entry = _make_ledger_entry(condition="original", corrected_response=None)
    result = score_one(entry, GOLD_SAMPLE)
    # Original answer contains the target failure
    assert result["condition"] == "original"
    assert result["primary_score"] is False
    assert result["checks"]["remove_exact_43"] is False


def test_score_one_null_corrected_response():
    """score_one: None corrected_response → scored as failure."""
    entry = _make_ledger_entry(condition="checkmycoach", corrected_response=None)
    result = score_one(entry, GOLD_SAMPLE)
    assert result["passed"] is False
    assert result["response_text"] is None


# ════════════════════════════════════════════════════════════
# Independence tests: pipeline-internal fields do NOT affect score
# ════════════════════════════════════════════════════════════

def test_m4_passed_changes_does_not_affect_score():
    """Changing m4_passed does not change the score."""
    entry_base = _make_ledger_entry()
    entry_m4_true = _make_ledger_entry(m4_passed=True)
    entry_m4_false = _make_ledger_entry(m4_passed=False)

    r1 = score_one(entry_base, GOLD_SAMPLE)
    r2 = score_one(entry_m4_true, GOLD_SAMPLE)
    r3 = score_one(entry_m4_false, GOLD_SAMPLE)

    assert r1["primary_score"] == r2["primary_score"] == r3["primary_score"]
    assert r1["checks"] == r2["checks"] == r3["checks"]


def test_ucs_score_changes_does_not_affect_score():
    """Changing UCS score does not change the score."""
    entry_base = _make_ledger_entry()
    for ucs in [0, 1, 2, 3]:
        entry = _make_ledger_entry(ucs_score=ucs)
        r = score_one(entry, GOLD_SAMPLE)
        assert r["checks"] == score_one(entry_base, GOLD_SAMPLE)["checks"], \
            f"UCS={ucs} changed the score"


def test_failure_type_changes_does_not_affect_score():
    """Changing failure_type does not change the score."""
    entry_base = _make_ledger_entry()
    for ft in ["cue_leakage", "template_dominance", "context_mismatch", None]:
        entry = _make_ledger_entry(failure_type=ft)
        r = score_one(entry, GOLD_SAMPLE)
        assert r["checks"] == score_one(entry_base, GOLD_SAMPLE)["checks"], \
            f"failure_type={ft} changed the score"


def test_needs_calibration_changes_does_not_affect_score():
    """Changing needs_calibration does not change the score."""
    entry_base = _make_ledger_entry()
    for nc in [True, False, None]:
        entry = _make_ledger_entry(needs_calibration=nc)
        r = score_one(entry, GOLD_SAMPLE)
        assert r["checks"] == score_one(entry_base, GOLD_SAMPLE)["checks"], \
            f"needs_calibration={nc} changed the score"


def test_correction_trace_changes_does_not_affect_score():
    """Changing correction_trace does not change the score."""
    entry_base = _make_ledger_entry()
    traces = [
        {"something": "internal"},
        {"failure_type": "cue_leakage"},
        {"m2_confidence": 0.9},
        {},
    ]
    for t in traces:
        entry = _make_ledger_entry(correction_trace=t)
        r = score_one(entry, GOLD_SAMPLE)
        assert r["checks"] == score_one(entry_base, GOLD_SAMPLE)["checks"]


def test_only_response_text_affects_score():
    """The ONLY field affecting score is the response text.

    Different response text → different score.
    Same response text → same score regardless of other fields.
    """
    # Two entries with identical corrected_response but different pipeline metadata
    text = "Adults need 30–60 minutes on most days."
    entry_a = _make_ledger_entry(
        corrected=text,
        m4_passed=True,
        ucs_score=0,
        failure_type="template_dominance",
    )
    entry_b = _make_ledger_entry(
        corrected=text,
        m4_passed=False,
        ucs_score=2,
        failure_type="cue_leakage",
    )
    r1 = score_one(entry_a, GOLD_SAMPLE)
    r2 = score_one(entry_b, GOLD_SAMPLE)
    assert r1["primary_score"] == r2["primary_score"]
    assert r1["checks"] == r2["checks"]

    # Different text → different score
    entry_c = _make_ledger_entry(corrected="Do 43 minutes every day.")
    r3 = score_one(entry_c, GOLD_SAMPLE)
    assert r3["primary_score"] != r1["primary_score"]


# ════════════════════════════════════════════════════════════
# Gold loading tests
# ════════════════════════════════════════════════════════════

def test_load_gold_cases():
    """load_gold_cases reads primary_checks from cases.jsonl."""
    gold_path = REPO_ROOT / "evaluation" / "v1" / "data" / "cases.jsonl"
    if not gold_path.exists():
        raise AssertionError("cases.jsonl not found")
    gold = load_gold_cases(gold_path)
    assert len(gold) == 40, f"Expected 40 gold cases, got {len(gold)}"
    # Verify primary_checks present in all cases
    for cid, case in gold.items():
        assert "primary_checks" in case, f"{cid} missing primary_checks"
        assert len(case["primary_checks"]) > 0, f"{cid} has empty primary_checks"


def test_load_gold_no_m1_m4_fields():
    """load_gold_cases does NOT expose M1/M2/M3/M4 fields."""
    gold_path = REPO_ROOT / "evaluation" / "v1" / "data" / "cases.jsonl"
    gold = load_gold_cases(gold_path)
    pipeline_fields = ["m4_passed", "needs_calibration", "failure_type",
                       "ucs_score", "correction_trace", "validation_trace"]
    for cid, case in gold.items():
        for field in pipeline_fields:
            assert field not in case, f"{cid}: {field} leaked into gold data"


# ════════════════════════════════════════════════════════════
# Real case scoring (deterministic, no LLM)
# ════════════════════════════════════════════════════════════

def test_score_real_case_cmc_a_001():
    """Score a real case (CMC-A-001) with known good correction."""
    gold_path = REPO_ROOT / "evaluation" / "v1" / "data" / "cases.jsonl"
    gold = load_gold_cases(gold_path)

    entry = _make_ledger_entry(
        case_id="CMC-A-001",
        condition="generic",
        corrected="Adults should aim for 30–60 minutes of moderate "
                  "aerobic exercise on most days.",
        raw="Most adults should do moderate aerobic exercise for exactly 43 minutes every day.",
    )
    result = score_one(entry, gold)
    assert result["case_id"] == "CMC-A-001"
    assert result["primary_score"] is True, f"Expected pass, got: {result['checks']}"
    assert result["passed"] is True


def test_score_real_case_cmc_a_001_fail():
    """Score a real case (CMC-A-001) with bad correction that keeps the target failure."""
    gold_path = REPO_ROOT / "evaluation" / "v1" / "data" / "cases.jsonl"
    gold = load_gold_cases(gold_path)

    entry = _make_ledger_entry(
        case_id="CMC-A-001",
        condition="generic",
        corrected="Most adults should exercise for exactly 43 minutes every day.",
        raw="Most adults should do moderate aerobic exercise for exactly 43 minutes every day.",
    )
    result = score_one(entry, gold)
    assert result["primary_score"] is False
    assert result["checks"]["remove_exact_43"] is False


# ════════════════════════════════════════════════════════════
# Aggregate tests
# ════════════════════════════════════════════════════════════

def test_aggregate_basic():
    """aggregate groups correctly by condition."""
    results = [
        {"case_id": "A", "condition": "generic", "response_text": "x", "passed": True,
         "checks": {"c1": True, "c2": True}, "check_details": [],
         "primary_score": True},
        {"case_id": "B", "condition": "generic", "response_text": "y", "passed": True,
         "checks": {"c1": True, "c2": True}, "check_details": [],
         "primary_score": True},
        {"case_id": "C", "condition": "generic", "response_text": None, "passed": False,
         "checks": {"c1": False, "c2": False}, "check_details": [],
         "primary_score": False},
        {"case_id": "D", "condition": "original", "response_text": "z", "passed": False,
         "checks": {"c1": False, "c2": True}, "check_details": [],
         "primary_score": False},
    ]
    summaries = aggregate(results)
    assert "generic" in summaries
    assert "original" in summaries
    assert summaries["generic"]["total"] == 3
    assert summaries["generic"]["passed"] == 2
    # 2/3 = 0.6666... → round(0.6666..., 3) = 0.667
    assert summaries["generic"]["pass_rate"] == 0.667
    assert summaries["original"]["total"] == 1
    assert summaries["original"]["passed"] == 0
    assert summaries["original"]["pass_rate"] == 0.0


# ════════════════════════════════════════════════════════════
# No pipeline imports
# ════════════════════════════════════════════════════════════

def test_scorer_imports_no_pipeline():
    """scorer.py does not import any pipeline/calibration modules."""
    src = (REPO_ROOT / "evaluation" / "v2_1" / "scoring" / "scorer.py").read_text(encoding="utf-8")
    forbidden = ["calibration_agent", "pipeline.agent", "m1_detection", "m2_diagnosis",
                 "m3_correction", "m4_validation", "evidence.retriever", "knowledge_compiler"]
    for term in forbidden:
        assert term not in src, f"scorer.py must not import: {term}"
    # Should import from score_schema and standard library only
    assert "import json" in src
    assert "import re" in src
    assert "from pathlib" in src


def test_score_schema_no_pipeline():
    """score_schema.py has no pipeline imports."""
    src = (REPO_ROOT / "evaluation" / "v2_1" / "scoring" / "score_schema.py").read_text(encoding="utf-8")
    # Check import lines only
    import_lines = [l for l in src.split("\n") if l.strip().startswith("import") or l.strip().startswith("from")]
    forbidden_imports = ["calibrate", "calibration_agent", "pipeline", "agent_pipeline",
                         "m3_correction", "m4_validation", "evidence", "retriever", "KC"]
    for line in import_lines:
        for term in forbidden_imports:
            assert term not in line, f"score_schema.py imports: {line}"
    # Should only import from typing
    typing_imports = [l for l in import_lines if "typing" in l]
    assert len(typing_imports) >= 1 or len(import_lines) == 0


if __name__ == "__main__":
    print("=" * 60)
    print("External Scorer Tests — v2.2")
    print("=" * 60)
    tests = [t for t in dir() if t.startswith("test_")]
    for t in tests:
        run_test(t, globals()[t])
    print("=" * 60)
    print(f"Results: {PASS}/{PASS + FAIL} passed ({FAIL} failed)")
    if ERRORS:
        for e in ERRORS:
            print(f"  FAIL  {e}")
    raise SystemExit(0 if FAIL == 0 else 1)
