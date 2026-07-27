"""
test_condition_randomization.py — Verify condition execution order differs across cases.

Fix 4 requirement:
- Condition order is randomized per case
- execution_order is stored in ledger
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v2_1.runner.run_single_case import (
    get_randomized_conditions,
    ALL_CONDITIONS,
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


# ── Deterministic randomization ──

def test_get_randomized_conditions_contains_all():
    """Randomized conditions contain all 4 conditions."""
    order = get_randomized_conditions("CMC-A-001")
    assert len(order) == 4
    assert set(order) == set(ALL_CONDITIONS)


def test_get_randomized_conditions_deterministic():
    """Same case_id produces same order (deterministic seed)."""
    order1 = get_randomized_conditions("CMC-A-001")
    order2 = get_randomized_conditions("CMC-A-001")
    assert order1 == order2


def test_get_randomized_conditions_differs_across_cases():
    """Different case_ids produce different orders."""
    orders = []
    for i in range(1, 11):
        cid = f"CMC-A-{i:03d}"
        orders.append(get_randomized_conditions(cid))
    # At least 2 different orderings across 10 cases
    unique = [list(o) for o in set(tuple(o) for o in orders)]
    assert len(unique) >= 2, \
        f"Expected multiple orderings across 10 cases, got {len(unique)}"


def test_get_randomized_conditions_not_always_same_first():
    """First condition varies across cases (not always original)."""
    firsts = set()
    for case_num in range(1, 41):
        cid = f"CMC-A-{case_num:03d}"
        order = get_randomized_conditions(cid)
        firsts.add(order[0])
    assert len(firsts) >= 2, \
        f"First condition should vary, always: {firsts}"


def test_get_randomized_conditions_original_placement():
    """Original condition placement varies across cases."""
    positions = set()
    for case_num in range(1, 41):
        cid = f"CMC-A-{case_num:03d}"
        order = get_randomized_conditions(cid)
        positions.add(order.index("original"))
    assert len(positions) >= 2, \
        f"Original condition position should vary, always at {positions}"


# ── execution_order field ──

def test_execution_order_in_build_record():
    """build_record stores execution_order."""
    from evaluation.v2_1.runner.run_single_case import build_record
    from evaluation.v2_1.runner.evidence_router import route_evidence
    from evaluation.v2_1.runner.run_single_case import load_blinded_cases

    cases = load_blinded_cases()
    case = cases[0]
    payload = route_evidence(case)
    order = get_randomized_conditions(case["case_id"])

    result = {"condition": "generic", "raw_response": "test", "included": True,
              "error": None, "execution_order": order}
    record = build_record("test_run", case["case_id"], "generic", result,
                          case["input_question"], payload.structured, 0.3, None, 0.0)
    assert "execution_order" in record
    assert record["execution_order"] == order


def test_execution_order_differs_across_records():
    """Different case_ids store different execution_orders."""
    from evaluation.v2_1.runner.run_single_case import build_record
    from evaluation.v2_1.runner.evidence_router import route_evidence
    from evaluation.v2_1.runner.run_single_case import load_blinded_cases

    cases = load_blinded_cases()
    orders = []
    for case in cases[:5]:
        payload = route_evidence(case)
        order = get_randomized_conditions(case["case_id"])
        result = {"condition": "generic", "raw_response": "test", "included": True,
                  "error": None, "execution_order": order}
        record = build_record("test", case["case_id"], "generic", result,
                              case["input_question"], payload.structured, 0.3, None, 0.0)
        orders.append(tuple(record["execution_order"]))
    unique_orders = set(orders)
    assert len(unique_orders) >= 2, \
        f"Expected multiple orderings across 5 cases, got {len(unique_orders)}"


# ── No logic change ──

def test_randomization_no_logic_change():
    """get_randomized_conditions returns the same elements — order only."""
    for case_num in range(1, 41):
        cid = f"CMC-A-{case_num:03d}"
        order = get_randomized_conditions(cid)
        assert sorted(order) == sorted(ALL_CONDITIONS), \
            f"{cid}: elements changed: {order}"
        assert len(order) == len(ALL_CONDITIONS)


if __name__ == "__main__":
    print("=" * 60)
    print("Condition Randomization Tests — Fix 4")
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
