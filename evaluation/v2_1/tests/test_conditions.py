"""
test_conditions.py — Condition behavior tests for v2.1.

Tests that the 4 conditions behave correctly:
1. Original returns answer directly (no API)
2. Generic uses evidence only (no diagnosis)
3. Generic+Diagnosis uses oracle diagnosis
4. CMC receives same evidence payload
"""

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v2_1.runner.conditions.original import run_original
from evaluation.v2_1.runner.conditions.generic import run_generic
from evaluation.v2_1.runner.conditions.generic_plus import run_generic_plus, _build_user_prompt_with_diagnosis
from evaluation.v2_1.runner.conditions.checkmycoach import run_checkmycoach
from evaluation.v2_1.runner.run_single_case import (
    load_blinded_cases,
    load_case_by_id,
    build_record,
    _validate_result_record,
    MODEL_CONFIG,
)

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


# ── Blinded case loading (v2.2 — 4 fields only) ──

def test_blinded_cases_v2_2_exists():
    """Blinded cases v2.2 file exists with 40 cases, 4 fields each."""
    cases_path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.2.jsonl"
    assert cases_path.exists(), "blinded_cases_v2.2.jsonl not found"
    cases = load_blinded_cases(cases_path)
    assert len(cases) == 40, f"Expected 40 cases, got {len(cases)}"
    for case in cases:
        assert set(case.keys()) == {"case_id", "input_question", "original_answer", "evidence_excerpt"}, \
            f"Case {case['case_id']} has extra fields: {set(case.keys())}"


def test_blinded_cases_no_diagnosis_fields():
    """Blinded v2.2 cases have NO oracle diagnosis fields."""
    cases_path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.2.jsonl"
    cases = load_blinded_cases(cases_path)
    oracle_fields = ["failure_family", "target_failure_span", "failure_statement",
                     "content_required_to_change", "required_boundary"]
    for case in cases:
        for field in oracle_fields:
            assert field not in case, f"{case['case_id']}: {field} leaked into blinded"

def test_oracle_diagnosis_file_exists():
    """Oracle diagnosis file exists with 40 entries, all required fields."""
    from evaluation.v2_1.runner.run_single_case import load_oracle_diagnoses
    ora = load_oracle_diagnoses()
    assert len(ora) == 40, f"Expected 40 oracle entries, got {len(ora)}"
    for cid, entry in ora.items():
        assert "failure_family" in entry, f"{cid} missing failure_family"
        assert "target_failure_span" in entry, f"{cid} missing target_failure_span"


def test_blinded_cases_no_gold_leakage():
    """Blinded v2.2 cases have no forbidden gold fields."""
    cases_path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.2.jsonl"
    cases = load_blinded_cases(cases_path)
    forbidden = ["reference_correction", "primary_checks", "secondary_checks",
                 "supported_content_to_retain", "forbidden_new_claims",
                 "linked_knowledge_object_ids", "source_provenance",
                 "ambiguity_flags", "adjudication_status",
                 "failure_family", "target_failure_span"]
    for case in cases:
        for field in forbidden:
            assert field not in case, f"{case['case_id']}: {field} leaked"


# ── Original condition ──

def test_original_no_api():
    """Original condition returns answer directly, no API."""
    answer = "Test original answer."
    result = run_original(answer)
    assert result["condition"] == "original"
    assert result["raw_response"] == answer
    assert result["corrected_response"] is None
    assert result["included"] is True
    assert result["error"] is None


def test_original_no_import():
    """Original condition does not reference pipeline modules."""
    import inspect
    src = inspect.getsource(run_original)
    assert "calibrate" not in src
    assert "pipeline" not in src
    assert "import" not in src


# ── Generic condition ──

def test_generic_condition_name():
    """Generic condition returns correct condition name."""
    result = run_generic("test", "test?", [])
    # Result might have error due to missing API key, but condition must be correct
    assert result["condition"] == "generic"
    assert result["raw_response"] == "test"


def test_generic_no_diagnosis():
    """Generic condition trace has no oracle_diagnosis."""
    result = run_generic("test", "test?", [])
    trace = result.get("correction_trace", {})
    assert "oracle_diagnosis" not in trace, "Generic should not have oracle_diagnosis"


# ── Generic+Diagnosis condition ──

def test_generic_plus_condition_name():
    """Generic+Diagnosis condition returns correct condition name."""
    result = run_generic_plus(
        original_answer="test",
        question="test?",
        evidence_payload=[],
        failure_family="unsupported_numerical_specificity",
        target_failure_span="exactly 43 minutes",
        failure_statement="The evidence gives a range.",
        content_required_to_change=["replace the exact value"],
    )
    assert result["condition"] == "generic_with_diagnosis"
    assert result["raw_response"] == "test"


def test_generic_plus_trace_has_oracle_diagnosis():
    """Generic+Diagnosis trace contains oracle diagnosis fields."""
    result = run_generic_plus(
        original_answer="test",
        question="test?",
        evidence_payload=[],
        failure_family="unsupported_numerical_specificity",
        target_failure_span="exactly 43 minutes",
        failure_statement="The evidence gives a range.",
        content_required_to_change=["replace the exact value"],
    )
    trace = result.get("correction_trace", {})
    assert "oracle_diagnosis" in trace
    diag = trace["oracle_diagnosis"]
    assert diag["failure_family"] == "unsupported_numerical_specificity"
    assert diag["target_failure_span"] == "exactly 43 minutes"
    assert diag["failure_statement"] == "The evidence gives a range."
    assert diag["content_required_to_change"] == ["replace the exact value"]


def test_generic_plus_falls_back_without_diagnosis():
    """Generic+Diagnosis without oracle fields still returns (degraded)."""
    result = run_generic_plus(
        original_answer="test",
        question="test?",
        evidence_payload=[],
    )
    assert result["condition"] == "generic_with_diagnosis"
    # Without diagnosis, it falls back — trace should not have oracle_diagnosis
    trace = result.get("correction_trace", {})
    assert "oracle_diagnosis" in trace
    assert trace["oracle_diagnosis"]["failure_family"] is None


def test_generic_plus_user_prompt_contains_diagnosis():
    """_build_user_prompt_with_diagnosis includes the diagnosis block."""
    prompt = _build_user_prompt_with_diagnosis(
        question="How long?",
        original_answer="43 minutes.",
        evidence_excerpt="30-60 minutes.",
        failure_family="unsupported_numerical_specificity",
        target_failure_span="43 minutes",
        failure_statement="Evidence gives a range.",
        content_required_to_change=["Use range"],
        required_boundary=None,
    )
    assert "Failure diagnosis:" in prompt
    assert "unsupported_numerical_specificity" in prompt
    assert "43 minutes" in prompt
    assert "Revised answer:" in prompt
    assert "Required boundary" not in prompt  # Null boundary omitted


def test_generic_plus_user_prompt_with_boundary():
    """_build_user_prompt_with_diagnosis includes required_boundary when set."""
    prompt = _build_user_prompt_with_diagnosis(
        question="How long?",
        original_answer="Continue workout.",
        evidence_excerpt="Avoid below -27C.",
        failure_family="missing_boundary",
        target_failure_span="Continue workout.",
        failure_statement="Missing cold threshold.",
        content_required_to_change=["Add avoid-or-modify boundary"],
        required_boundary="Avoid below -27C wind chill.",
    )
    assert "Failure diagnosis:" in prompt
    assert "Required boundary:" in prompt
    assert "Avoid below -27C" in prompt


# ── CheckMyCoach condition ──

def test_checkmycoach_condition_name():
    """CMC condition returns correct condition name."""
    result = run_checkmycoach("test", "test?", [])
    assert result["condition"] == "checkmycoach"
    assert result["raw_response"] == "test"


# ── Build record ──

def test_build_record_provenance_fields():
    """build_record produces all required provenance fields."""
    run_id = "test_run_v2_1"
    case_id = "CMC-A-001"
    question = "Test question?"
    evidence = [{"id": "case_evidence", "content": "test", "source": "blinded case file"}]
    result = {"condition": "generic", "raw_response": "test answer", "included": True, "error": None}
    record = build_record(run_id, case_id, "generic", result, question,
                          evidence, 0.3, None, time.perf_counter())
    required = ["run_id", "case_id", "condition", "model_id", "provider",
                "temperature", "max_tokens", "seed_policy", "request_id",
                "response_id", "timestamp", "included"]
    for field in required:
        assert field in record, f"Missing required field: {field}"
    assert record["model_id"] == MODEL_CONFIG["generic"]["model_id"]
    assert record["temperature"] == MODEL_CONFIG["generic"]["temperature"]
    assert record["max_tokens"] == MODEL_CONFIG["generic"]["max_tokens"]


def test_build_record_generic_plus_model_config():
    """build_record uses correct model config for generic_with_diagnosis."""
    run_id = "test"
    case_id = "CMC-A-001"
    question = "?"
    evidence = [{"id": "case_evidence", "content": "test", "source": "blinded case file"}]
    result = {"condition": "generic_with_diagnosis", "raw_response": "t", "included": True, "error": None}
    record = build_record(run_id, case_id, "generic_with_diagnosis", result, question,
                          evidence, 0.3, None, time.perf_counter())
    assert record["condition"] == "generic_with_diagnosis"
    assert record["temperature"] == 0.3
    assert record["max_tokens"] == 1024


def test_validate_result_record_valid():
    """Valid record passes validation."""
    record = {
        "run_id": "test", "case_id": "test", "condition": "original",
        "execution_order": ["original", "generic", "generic_with_diagnosis", "checkmycoach"],
        "model_id": "N/A (no API call)", "provider": "N/A",
        "temperature": None, "max_tokens": None,
        "seed_policy": "not_applicable",
        "request_id": "req", "response_id": "resp",
        "timestamp": "2026-01-01T00:00:00", "included": True,
    }
    _validate_result_record(record)


def test_validate_result_record_missing_field_raises():
    """Record with missing field raises ValueError."""
    record = {"run_id": "test"}
    try:
        _validate_result_record(record)
        assert False, "Should raise ValueError"
    except ValueError:
        pass


# ── Evidence symmetry ──

def test_evidence_symmetry_blinded_file():
    """Verify all blinded cases have evidence_excerpt for symmetric routing."""
    cases_path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.1.jsonl"
    with open(cases_path, encoding="utf-8") as f:
        cases = [json.loads(l) for l in f if l.strip()]
    for case in cases:
        assert "evidence_excerpt" in case
        assert case["evidence_excerpt"], f"Case {case['case_id']} has empty evidence_excerpt"


# ── Run summary ──

if __name__ == "__main__":
    print("=" * 60)
    print("v2.1 Condition Tests")
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
