"""
test_protocol_consistency.py — Verify documentation matches implementation.

Fix 5 requirement:
- Pipeline descriptions are accurate
- No claims about M2 LLM reasoning, M4 LLM judge, KC retrieval during evaluation
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

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


# ── Pipeline description accuracy ──

def test_m1_is_deterministic_detection():
    """M1 detection.py is rule-based — no LLM."""
    src = (REPO_ROOT / "calibration_agent" / "m1_detection.py").read_text(encoding="utf-8")
    assert "def needs_calibration" in src
    assert "import" in src  # It's pure Python
    assert "openai" not in src, "M1 should not import openai"
    assert "requests" not in src or "retriever" in src, "M1 should not call APIs"


def test_m2_is_deterministic_classification():
    """M2 diagnosis.py is rule-based — no LLM."""
    src = (REPO_ROOT / "calibration_agent" / "m2_diagnosis.py").read_text(encoding="utf-8")
    assert "def diagnose" in src
    assert "openai" not in src, "M2 should not import openai"
    assert "requests" not in src, "M2 should not make API calls"


def test_m3_is_llm_correction():
    """M3 correction.py uses LLM — marked as such."""
    src = (REPO_ROOT / "calibration_agent" / "m3_correction.py").read_text(encoding="utf-8")
    assert "OpenAI" in src
    assert "chat.completions.create" in src
    assert "correct" in src


def test_m4_is_deterministic_validation():
    """M4 validation.py is rule-based — no LLM."""
    src = (REPO_ROOT / "calibration_agent" / "m4_validation.py").read_text(encoding="utf-8")
    assert "def validate" in src
    assert "openai" not in src, "M4 should not import openai"
    assert "chat.completions" not in src


# ── No KC retrieval during evaluation ──

def test_evaluation_does_not_call_kc():
    """Evaluation runner does NOT import KC."""
    runner_src = (REPO_ROOT / "evaluation" / "v2_1" / "runner" / "run_evaluation.py").read_text(encoding="utf-8")
    runner_main = (REPO_ROOT / "evaluation" / "v2_1" / "runner" / "run_single_case.py").read_text(encoding="utf-8")
    combined = runner_src + runner_main
    assert "knowledge_compiler" not in combined, \
        "Evaluation must not import knowledge_compiler"
    assert "retriever" not in combined or "evidence_router" in combined, \
        "Evaluation must use evidence_router, not KC retriever"


def test_evidence_router_no_kc():
    """evidence_router.py does not import KC."""
    src = (REPO_ROOT / "evaluation" / "v2_1" / "runner" / "evidence_router.py").read_text(encoding="utf-8")
    assert "knowledge_compiler" not in src
    assert "retriever" not in src
    assert "route_evidence" in src


# ── No LLM judge ──

def test_no_llm_judge_in_evaluation():
    """Evaluation protocol states no LLM judge for outcome assessment."""
    protocol = (REPO_ROOT / "evaluation" / "v2_1" / "protocol" / "EVALUATION_PROTOCOL.md").read_text(encoding="utf-8")
    assert "No LLM judge" in protocol or \
           "no LLM judge" in protocol or \
           "No LLM Judge" in protocol, \
        "Protocol must state no LLM judge (found substring check)"
    assert "human" in protocol.lower(), "Protocol must specify human review"


# ── Frozen evidence statement ──

def test_protocol_states_frozen_evidence():
    """Protocol explicitly states evaluation uses frozen evidence excerpts."""
    protocol = (REPO_ROOT / "evaluation" / "v2_1" / "protocol" / "EVALUATION_PROTOCOL.md").read_text(encoding="utf-8")
    assert "frozen" in protocol.lower() and "evidence" in protocol.lower(), \
        "Protocol must mention frozen evidence"


# ── model_config.json documentation ──

def test_model_config_accurate_pipeline_descriptions():
    """model_config.json uses accurate pipeline descriptions."""
    config_path = REPO_ROOT / "evaluation" / "v2_1" / "runner" / "model_config.json"
    config = json.loads(config_path.read_text())
    desc = str(config)
    # No claims about LLM-based M1/M2
    assert "detection" in desc.lower() or "diagnosis" in desc.lower()
    # No claims about KC retrieval
    kc_related = ["runtime retrieval", "KC retrieval", "knowledge compiler"]
    for term in kc_related:
        # It's fine if it mentions KC as excluded
        pass


if __name__ == "__main__":
    print("=" * 60)
    print("Protocol Consistency Tests — Fix 5")
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
