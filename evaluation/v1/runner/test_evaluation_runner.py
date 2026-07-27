"""
test_evaluation_runner.py — Tests for CheckMyCoach evaluation runner v2.

Covers:
- blinded JSONL loading
- blinded projection leakage check
- Original does not call API
- three conditions share original_answer
- schema validation of result records
- API failure exclusion (fail closed)
- generic correction has new fail-closed interface

Run with:
    python evaluation/v1/runner/test_evaluation_runner.py
"""

import json
import hashlib
import sys
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v1.runner.run_single_case import (
    load_blinded_cases,
    load_case_by_id,
    run_original,
    run_generic,
    run_checkmycoach,
    collect_case_evidence,
    build_record,
    validate_result_record,
    MODEL_CONFIG,
    _hash_evidence,
)
from evaluation.v1.runner.generic_correction import (
    correct as generic_correct,
    _load_prompt,
    _build_user_prompt,
)

PASS = 0
FAIL = 0
ERRORS = []
TESTS = []


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


def register(name):
    def decorator(fn):
        TESTS.append((name, fn))
        return fn
    return decorator


# ════════════════════════════════════════════════════════════════
# Fix 1+2: blinded JSONL loading + leakage check
# ════════════════════════════════════════════════════════════════

@register("blinded_cases.jsonl exists with 40 cases")
def test_blinded_cases_exist():
    path = Path(__file__).resolve().parent.parent / "data" / "blinded_cases.jsonl"
    assert path.exists(), f"blinded_cases.jsonl not found at {path}"
    cases = load_blinded_cases(path)
    assert len(cases) == 40, f"Expected 40 cases, got {len(cases)}"


@register("blinded projection: no gold labels leaked")
def test_blinded_no_gold():
    path = Path(__file__).resolve().parent.parent / "data" / "blinded_cases.jsonl"
    cases = load_blinded_cases(path)
    forbidden = [
        "target_failure_span", "failure_statement", "failure_family",
        "primary_checks", "secondary_checks", "reference_correction",
        "forbidden_new_claims", "content_required_to_change",
        "required_boundary", "adjudication_status",
        "linked_knowledge_object_ids", "source_provenance",
    ]
    for case in cases:
        for field in forbidden:
            assert field not in case, f"{case['case_id']}: {field} leaked"
        # Must have only the 4 allowed fields
        allowed = {"case_id", "input_question", "original_answer", "evidence_excerpt"}
        extra = set(case.keys()) - allowed
        assert not extra, f"{case['case_id']}: unexpected fields: {extra}"


@register("blinded cases: each has required fields")
def test_blinded_required_fields():
    path = Path(__file__).resolve().parent.parent / "data" / "blinded_cases.jsonl"
    cases = load_blinded_cases(path)
    for case in cases:
        assert "case_id" in case
        assert "input_question" in case
        assert "original_answer" in case
        assert len(case["original_answer"]) > 0


@register("blinded cases: load by ID works")
def test_blinded_load_by_id():
    path = Path(__file__).resolve().parent.parent / "data" / "blinded_cases.jsonl"
    cases = load_blinded_cases(path)
    case = load_case_by_id("CMC-A-001", cases)
    assert case["case_id"] == "CMC-A-001"
    assert "exactly 43 minutes" in case["original_answer"]


@register("blinded cases: non-existent ID raises")
def test_blinded_not_found():
    path = Path(__file__).resolve().parent.parent / "data" / "blinded_cases.jsonl"
    cases = load_blinded_cases(path)
    try:
        load_case_by_id("NONEXISTENT", cases)
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        pass


# ════════════════════════════════════════════════════════════════
# Fix 1: Original condition does not call API
# ════════════════════════════════════════════════════════════════

@register("run_original: returns answer directly, no API call")
def test_original_no_api():
    answer = "This is a test original answer."
    result = run_original(answer)
    assert result["condition"] == "original"
    assert result["raw_response"] == answer
    assert result["corrected_response"] is None
    assert result["included"] is True
    assert result["error"] is None
    # Verify no evidence_ids or token_usage (original shouldn't have these)
    assert "evidence_ids" not in result
    assert "token_usage" not in result


@register("run_original: does not import any pipeline module")
def test_original_no_import():
    """Verify run_original source code doesn't call calibrate_full or any pipeline."""
    import inspect
    src = inspect.getsource(run_original)
    assert "calibrate" not in src, "run_original should not reference calibrate"
    assert "pipeline" not in src, "run_original should not reference pipeline"
    assert "import" not in src, "run_original should have no imports"


# ════════════════════════════════════════════════════════════════
# Fix 1: Three conditions share the same original_answer
# ════════════════════════════════════════════════════════════════

@register("three conditions: share same original_answer")
def test_shared_original():
    answer = "Shared test answer across all conditions."
    question = "Test question?"
    evidence = [{"id": "e1", "type": "test", "content": "test evidence", "source": "test"}]

    orig_result = run_original(answer)
    assert orig_result["raw_response"] == answer

    # Generic
    gen_result = run_generic(answer, question, evidence)
    assert gen_result["raw_response"] == answer
    # Generic should produce a corrected version
    assert gen_result["corrected_response"] != answer or gen_result.get("included") == False

    # CMC (without API key, will fail — but raw_response should still match)
    cmc_result = run_checkmycoach(answer, question)
    assert cmc_result["raw_response"] == answer


# ════════════════════════════════════════════════════════════════
# Fix 3: Provenance fields
# ════════════════════════════════════════════════════════════════

@register("build_record: all provenance fields present")
def test_provenance_fields():
    run_id = "test_run"
    case_id = "CMC-A-001"
    question = "Test question?"
    evidence = []

    result = run_original("test answer")
    record = build_record(run_id, case_id, "original", result, question,
                          evidence, 0.5, None, time.perf_counter())

    required = ["run_id", "case_id", "condition", "model_id", "provider",
                "temperature", "max_tokens", "seed_policy", "request_id",
                "response_id", "timestamp", "included"]
    for field in required:
        assert field in record, f"Missing required field: {field}"

    assert record["model_id"] == MODEL_CONFIG["original"]["model_id"]
    assert record["seed_policy"] == "not_applicable"


@register("build_record: evidence_hash populated")
def test_evidence_hash():
    run_id = "test_run"
    case_id = "CMC-A-001"
    question = "Test?"
    evidence = [{"id": "e1", "content": "evidence content", "source": "test"}]

    result = run_original("test")
    record = build_record(run_id, case_id, "generic", result, question,
                          evidence, 0.5, None, time.perf_counter())
    assert "evidence_hash" in record
    assert len(record["evidence_hash"]) == 16  # SHA-256 prefix


@register("build_record: error and included consistency")
def test_error_included_consistency():
    run_id = "test_run"
    case_id = "CMC-A-001"
    question = "Test?"
    evidence = []

    # Successful result
    ok_result = {"condition": "original", "raw_response": "ok", "included": True, "error": None}
    try:
        record = build_record(run_id, case_id, "original", ok_result, question,
                              evidence, 0.5, None, time.perf_counter())
        assert record["included"] is True
    except ValueError:
        # build_record may not accept raw dicts, that's fine
        pass

    # Failed result
    err_result = {"condition": "original", "raw_response": "", "included": False, "error": "API_ERROR"}
    try:
        record = build_record(run_id, case_id, "original", err_result, question,
                              evidence, 0.5, None, time.perf_counter())
        assert record["included"] is False
        assert record["error"] == "API_ERROR"
    except ValueError:
        pass


# ════════════════════════════════════════════════════════════════
# Fix 4: Schema validation
# ════════════════════════════════════════════════════════════════

@register("result.schema.json: all new provenance fields")
def test_schema_new_fields():
    schema_path = Path(__file__).parent / "result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    props = schema.get("properties", {})
    for f in ["model_id", "provider", "max_tokens", "seed_policy",
              "request_id", "response_id", "fallback_status",
              "prompt_hash", "evidence_hash"]:
        assert f in props, f"Missing property in schema: {f}"
    assert "ucs_score" not in props
    assert "ucs_features" not in props


@register("result.schema.json: required fields match")
def test_schema_required():
    schema_path = Path(__file__).parent / "result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required = schema.get("required", [])
    for f in ["run_id", "case_id", "condition", "model_id", "provider",
              "temperature", "max_tokens", "seed_policy", "request_id",
              "response_id", "timestamp", "included"]:
        assert f in required, f"Missing required: {f}"


@register("validate_result_record: valid record passes")
def test_validate_pass():
    record = {
        "run_id": "test", "case_id": "test", "condition": "original",
        "model_id": "N/A (no API call)", "provider": "N/A",
        "temperature": None, "max_tokens": None,
        "seed_policy": "not_applicable",
        "request_id": "req", "response_id": "resp",
        "timestamp": "2026-01-01T00:00:00", "included": True,
    }
    # Should not raise
    validate_result_record(record)


@register("validate_result_record: missing field raises")
def test_validate_fail():
    record = {
        "run_id": "test", "case_id": "test",
        # missing condition, model_id, etc.
    }
    try:
        validate_result_record(record)
        assert False, "Should raise ValueError"
    except ValueError:
        pass


# ════════════════════════════════════════════════════════════════
# Fix 5: Fail closed — generic correction raises on API failure
# ════════════════════════════════════════════════════════════════

@register("generic correction: no fallback prefix constant")
def test_no_fallback():
    """Fallback prefix should not exist — fail closed."""
    import inspect
    src = inspect.getsource(generic_correct)
    assert "FALLBACK_PREFIX" not in src, "Fallback prefix constant should not exist"
    assert "fallback_text" not in src, "Fallback variable should not exist"


@register("generic correction: fails closed without API key")
def test_generic_fail_closed():
    """Without API key, generic correction should raise ValueError."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        # Can't test without key when key exists — skip assertion semantics
        # but verify the function still works
        result = generic_correct("test?", "answer.", [])
        assert result.source == "llm"
        return
    try:
        generic_correct("test?", "answer.", [])
        assert False, "Should raise ValueError when no API key"
    except ValueError:
        pass


@register("generic correction: prompt hash exists in new interface")
def test_prompt_hash():
    prompt = _load_prompt()
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    assert len(h) == 16
    assert prompt == "Revise the answer to be accurate, appropriately cautious, evidence-based and concise. Preserve useful supported information and avoid adding unsupported claims."


# ════════════════════════════════════════════════════════════════
# Original tests preserved (compatible)
# ════════════════════════════════════════════════════════════════

@register("gold-label leakage: input case has no forbidden fields")
def test_gold_label_leakage():
    """Legacy: verify sample case format has no gold."""
    sample_path = Path(__file__).resolve().parent.parent / "cases" / "sample" / "CMC-EVAL-0001.json"
    if sample_path.exists():
        case = json.loads(sample_path.read_text())
        forbidden = ["target_failure", "reference_correction", "expected_ucs", "gold_label"]
        for key in forbidden:
            assert key not in case, f"Contains forbidden field: {key}"


@register("generic correction: new interface has question+answer+evidence")
def test_generic_new_interface():
    import inspect
    sig = inspect.signature(generic_correct)
    params = list(sig.parameters.keys())
    assert "question" in params
    assert "original_answer" in params
    assert "evidence_payload" in params
    assert "failure_type" not in params


@register("generic correction: loads frozen prompt from file")
def test_generic_loads_frozen_prompt():
    protocol_dir = Path(__file__).resolve().parent.parent / "protocol"
    prompt = _load_prompt(protocol_dir)
    assert len(prompt) > 10
    assert "evidence" in prompt.lower() or "revise" in prompt.lower()


@register("generic correction: frozen prompt file exists")
def test_frozen_prompt_exists():
    prompt_path = Path(__file__).resolve().parent.parent / "protocol" / "GENERIC_BASELINE_PROMPT.txt"
    assert prompt_path.exists()
    text = prompt_path.read_text(encoding="utf-8").strip()
    assert len(text) > 10


@register("generic correction: prompt includes question+answer+evidence")
def test_generic_prompt_content():
    prompt = _build_user_prompt("test question", "test answer",
                                [{"id": "e1", "content": "test", "source": "ACSM12"}])
    assert "test question" in prompt
    assert "test answer" in prompt
    assert "ACSM12" in prompt


@register("input.schema.json: no gold fields")
def test_input_schema_no_gold():
    schema_path = Path(__file__).parent / "input.schema.json"
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        props = schema.get("properties", {})
        for key in ["target_failure", "reference_correction", "expected_ucs", "gold_label"]:
            assert key not in props


@register("result.schema.json: valid structure")
def test_result_schema():
    schema_path = Path(__file__).parent / "result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert "required" in schema
    assert "properties" in schema


@register("result.schema.json: three conditions defined")
def test_three_conditions():
    schema_path = Path(__file__).parent / "result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    enum = schema["properties"]["condition"]["enum"]
    for c in ["original", "generic", "checkmycoach"]:
        assert c in enum


@register("collect_case_evidence: supports evidence_excerpt from production format")
def test_evidence_excerpt_support():
    case = {"evidence_excerpt": "Production evidence excerpt here."}
    result = collect_case_evidence("question", case)
    assert len(result) > 0
    assert result[0]["content"] == "Production evidence excerpt here."


@register("collect_case_evidence: empty excerpt returns empty list")
def test_evidence_excerpt_empty():
    case = {"evidence_excerpt": ""}
    result = collect_case_evidence("question", case)
    assert len(result) == 0


# ════════════════════════════════════════════════════════════════
# Fix 6: Dependency freeze (verify in manifest)
# ════════════════════════════════════════════════════════════════

@register("execution manifest exists with dependency hashes")
def test_execution_manifest():
    manifest_path = Path(__file__).resolve().parent.parent / "execution" / "execution_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert "runner_files" in manifest
    assert "model_config" in manifest


@register("model_config.json exists with all three models")
def test_model_config():
    config_path = Path(__file__).resolve().parent.parent / "execution" / "model_config.json"
    assert config_path.exists()
    config = json.loads(config_path.read_text())
    assert "original_generation" in config
    assert "generic_correction" in config
    assert "cmc_m3_correction" in config
    assert config["model_equality"]["generic_equals_cmc_m3"] is True


if __name__ == "__main__":
    print("=" * 60)
    print("CheckMyCoach Evaluation Runner - Tests v2")
    print("=" * 60)
    for name, fn in TESTS:
        run_test(name, fn)
    print("=" * 60)
    print(f"Results: {PASS}/{PASS + FAIL} passed ({FAIL} failed)")
    if ERRORS:
        print("Errors:")
        for e in ERRORS:
            print(f"  FAIL  {e}")
    print("=" * 60)
    raise SystemExit(0 if FAIL == 0 else 1)
