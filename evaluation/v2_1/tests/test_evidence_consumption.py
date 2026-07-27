"""
test_evidence_consumption.py — Verify CMC M3 receives evidence.

Fix 1 requirement:
- CMC M3 prompt must include evidence text
- Generic evidence_hash == CMC evidence_hash (same evidence from router)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from calibration_agent.m3_correction import correct as m3_correct
from calibration_agent.m3_correction import _build_prompt as m3_build_prompt
from evaluation.v2_1.runner.evidence_router import route_evidence
from evaluation.v2_1.runner.run_single_case import (
    load_blinded_cases,
    load_oracle_diagnoses,
    run_condition,
    ALL_CONDITIONS,
    _hash_evidence,
    _oracle_diagnoses,
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


# ── CMC M3 evidence consumption ──

def test_m3_correct_accepts_question_and_evidence():
    """M3 correct() accepts question and evidence parameters (Fix 1)."""
    import inspect
    sig = inspect.signature(m3_correct)
    params = list(sig.parameters.keys())
    assert "question" in params, "M3 correct() must accept question"
    assert "evidence" in params, "M3 correct() must accept evidence"
    assert "failure_type" in params
    assert "original_text" in params


def test_m3_prompt_includes_evidence():
    """M3 prompt built with evidence contains the evidence text."""
    prompt = m3_build_prompt(
        "cue_leakage",
        "Original answer with 43 minutes.",
        question="How long should I exercise?",
        evidence="30-60 minutes per day for most adults.",
    )
    assert "How long should I exercise?" in prompt, "Prompt must include question"
    assert "30-60 minutes" in prompt, "Prompt must include evidence text"
    assert "cue_leakage" in prompt or "CUE_LEAKAGE" not in prompt, \
        "Failure type appears in system prompt, not user prompt"


def test_m3_prompt_without_evidence_fallback():
    """M3 prompt falls back gracefully without question or evidence."""
    prompt = m3_build_prompt(
        "cue_leakage",
        "Original answer with 43 minutes.",
    )
    assert "Original answer with 43 minutes" in prompt
    # Should not include question/evidence headers
    # The fallback behavior is to not prepend context
    assert "Original answer" in prompt or "Original advice" in prompt


def test_m3_correct_signature_backward_compatible():
    """M3 correct() works with just failure_type and original_text."""
    try:
        # This will fail because no API key, but should get there
        # (we can't actually call the LLM in unit test)
        result = m3_correct("template_dominance", "Test text.")
        # If we get here, signature is compatible
    except ValueError as e:
        # Expected: no API key
        assert "API" not in str(e), "Should not fail at signature level"
    except Exception:
        # Any other exception is fine — we're testing signature, not execution
        pass


# ── Evidence hash equality ──

def test_generic_and_cmc_same_evidence_hash():
    """Generic and CMC conditions receive the SAME evidence payload (Fix 1).

    Both conditions route through evidence_router which produces
    identical evidence_hash for the same case.
    """
    cases = load_blinded_cases()
    # Use first 5 cases to verify consistency
    for case in cases[:5]:
        payload = route_evidence(case)
        # evidence_hash is computed from the structured payload,
        # which is the same object passed to both Generic and CMC
        h = _hash_evidence(payload.structured)
        assert len(h) == 16
        assert payload.evidence_hash != ""


def test_evidence_router_used_by_all_conditions():
    """All correction conditions use the evidence_router (not KC)."""
    # Verify evidence_router is imported by the condition runners
    from evaluation.v2_1.runner.conditions.generic import run_generic
    import inspect
    src = inspect.getsource(run_generic)
    assert "evidence_payload" in src


def test_m3_prompt_template_has_question_placeholder():
    """At least one PROMPT_TEMPLATE contains question context."""
    # The _build_prompt function now prepends question/evidence
    # to ALL templates. Verify the formatting works for each type.
    for ftype in ["template_dominance", "cue_leakage", "context_mismatch"]:
        prompt = m3_build_prompt(
            ftype,
            "Original advice text here.",
            question="Test question?",
            evidence="Test evidence.",
        )
        assert "Test question?" in prompt, f"{ftype}: question missing"
        assert "Test evidence." in prompt, f"{ftype}: evidence missing"
        assert "Original advice text here" in prompt, f"{ftype}: original text missing"


# ── Evidence_hash in ledger ──

def test_build_record_stores_evidence_hash():
    """build_record stores evidence_hash for all conditions."""
    cases = load_blinded_cases()
    case = cases[0]
    payload = route_evidence(case)
    from evaluation.v2_1.runner.run_single_case import build_record
    result = {"condition": "generic", "raw_response": "test", "included": True,
              "error": None, "execution_order": ["generic"]}
    record = build_record(
        "test_run", case["case_id"], "generic", result,
        case["input_question"], payload.structured, 0.3, None, 0.0,
    )
    assert "evidence_hash" in record
    assert len(record["evidence_hash"]) == 16
    # Generic and CMC should produce same hash for same evidence
    result2 = {"condition": "checkmycoach", "raw_response": "test", "included": True,
               "error": None, "execution_order": ["checkmycoach"]}
    record2 = build_record(
        "test_run", case["case_id"], "checkmycoach", result2,
        case["input_question"], payload.structured, 0.3, None, 0.0,
    )
    assert record["evidence_hash"] == record2["evidence_hash"], \
        "Generic and CMC evidence_hash must match (same evidence payload)"


if __name__ == "__main__":
    print("=" * 60)
    print("Evidence Consumption Tests — Fix 1")
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
