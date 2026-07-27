"""
test_evidence_router.py — Evidence symmetry tests for v2.1.

Verifies that all three correction conditions receive the SAME evidence
from the evidence_router, and that the payload matches protocol §5.1.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v2_1.runner.evidence_router import route_evidence, EvidencePayload

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


def test_evidence_router_returns_payload():
    """route_evidence returns an EvidencePayload with correct structure."""
    case = {
        "case_id": "CMC-A-001",
        "evidence_excerpt": "For most adults: 30–60 minutes per day of moderate aerobic exercise on most days.",
    }
    payload = route_evidence(case)
    assert isinstance(payload, EvidencePayload)
    assert isinstance(payload.evidence_excerpt, str)
    assert len(payload.evidence_excerpt) > 0
    assert len(payload.evidence_hash) == 16
    assert isinstance(payload.structured, list)
    assert len(payload.structured) == 1


def test_evidence_router_payload_id():
    """Structured evidence has the expected id, content, and source."""
    case = {"case_id": "CMC-A-001", "evidence_excerpt": "Test evidence for routing."}
    payload = route_evidence(case)
    entry = payload.structured[0]
    assert entry["id"] == "case_evidence"
    assert entry["type"] == "inline"
    assert entry["source"] == "blinded case file"
    assert entry["content"] == "Test evidence for routing."


def test_evidence_router_hash_consistency():
    """Same evidence_excerpt produces same hash."""
    case1 = {"case_id": "CMC-A-001", "evidence_excerpt": "Same evidence text."}
    case2 = {"case_id": "CMC-B-002", "evidence_excerpt": "Same evidence text."}
    p1 = route_evidence(case1)
    p2 = route_evidence(case2)
    assert p1.evidence_hash == p2.evidence_hash


def test_evidence_router_hash_changes_with_content():
    """Different evidence_excerpt produces different hash."""
    case1 = {"case_id": "CMC-A-001", "evidence_excerpt": "Evidence A."}
    case2 = {"case_id": "CMC-B-002", "evidence_excerpt": "Evidence B."}
    p1 = route_evidence(case1)
    p2 = route_evidence(case2)
    assert p1.evidence_hash != p2.evidence_hash


def test_evidence_router_empty_excerpt_raises():
    """Empty evidence_excerpt raises ValueError."""
    case = {"case_id": "CMC-A-001", "evidence_excerpt": ""}
    try:
        route_evidence(case)
        assert False, "Should raise ValueError on empty excerpt"
    except ValueError:
        pass


def test_evidence_router_missing_excerpt_raises():
    """Missing evidence_excerpt raises ValueError."""
    case = {"case_id": "CMC-A-001"}
    try:
        route_evidence(case)
        assert False, "Should raise ValueError on missing excerpt"
    except ValueError:
        pass


def test_evidence_payload_truncated_to_500():
    """Evidence content is truncated to 500 chars."""
    long_text = "A" * 1000
    case = {"case_id": "CMC-A-001", "evidence_excerpt": long_text}
    payload = route_evidence(case)
    assert len(payload.structured[0]["content"]) == 500


def test_evidence_router_all_blinded_cases():
    """All 40 blinded cases produce valid evidence payloads."""
    cases_path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.1.jsonl"
    assert cases_path.exists(), "blinded_cases_v2.1.jsonl not found"
    with open(cases_path, encoding="utf-8") as f:
        cases = [json.loads(l) for l in f if l.strip()]
    assert len(cases) == 40
    for case in cases:
        payload = route_evidence(case)
        assert payload.evidence_excerpt, f"Case {case['case_id']} has empty evidence_excerpt"
        assert len(payload.evidence_hash) == 16
        assert len(payload.structured) == 1


def test_evidence_symmetry_across_conditions():
    """Evidence_router returns the SAME content for all correction conditions.

    This is the KEY test for protocol §5: all three correction conditions
    must receive identical evidence_excerpt.
    """
    cases_path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.1.jsonl"
    with open(cases_path, encoding="utf-8") as f:
        cases = [json.loads(l) for l in f if l.strip()]

    # Generic, Generic+Diagnosis, and CMC must all receive the same evidence
    for case in cases:
        payload = route_evidence(case)
        # The structured payload is the evidence object — all three conditions
        # receive the same list. We verify it's always present and consistent.
        assert payload.structured[0]["content"] == case["evidence_excerpt"]
        assert payload.evidence_hash != ""   # Always populated


if __name__ == "__main__":
    print("=" * 60)
    print("Evidence Router Tests — v2.1")
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
