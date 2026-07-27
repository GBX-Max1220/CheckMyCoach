"""
scorer.py — Frozen external evaluation scorer for CheckMyCoach v2.2.

INDEPENDENT post-run evaluator.
- Deterministic: same inputs → same outputs.
- No LLM calls.
- No pipeline imports (no M1/M2/M3/M4).
- No calibration metadata input (m4_passed, needs_calibration, UCS, etc.).
- Only reads: final response text + case_id + frozen primary_checks.

Usage:
    python -m evaluation.v2_1.scoring.scorer \\
        --ledger evaluation/v2_1/ledger.jsonl \\
        --gold evaluation/v1/data/cases.jsonl \\
        --output evaluation/v2_1/scores/scores.jsonl
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional


# ── Check runner ──

def _run_check(check: dict, text: str) -> tuple[bool, str]:
    """Run one primary check against a text string.

    Args:
        check: Primary check dict from cases.jsonl.
               Contains: type, check_id, plus type-specific fields.
        text: The response text to evaluate.

    Returns:
        (passed: bool, detail: str)
        detail is a human-readable reason for failure (empty on pass).

    Raises:
        ValueError: If check type is unknown.
    """
    check_type = check["type"]
    check_id = check.get("check_id", "unknown")
    detail = ""

    if check_type == "substring_absent":
        value = check["value"]
        if value in text:
            return False, f"Forbidden substring found: '{value}'"
        return True, ""

    elif check_type == "regex_present":
        pattern = check["pattern"]
        if re.search(pattern, text):
            return True, ""
        return False, f"Required regex not matched: {pattern}"

    elif check_type == "any_regex_present":
        patterns = check["patterns"]
        for p in patterns:
            if re.search(p, text):
                return True, ""
        return False, f"None of the required regex patterns matched: {patterns}"

    elif check_type == "all_regex_present":
        patterns = check["patterns"]
        missing = [p for p in patterns if not re.search(p, text)]
        if not missing:
            return True, ""
        return False, f"Regex patterns not matched: {missing}"

    elif check_type == "phrase_present":
        value = check["value"]
        if value in text:
            return True, ""
        return False, f"Required phrase not found: '{value}'"

    elif check_type == "any_phrase_present":
        values = check["values"]
        for v in values:
            if v in text:
                return True, ""
        return False, f"None of the required phrases found: {values}"

    elif check_type == "all_phrase_present":
        values = check["values"]
        missing = [v for v in values if v not in text]
        if not missing:
            return True, ""
        return False, f"Required phrases not found: {missing}"

    elif check_type == "all_phrase_groups_present":
        groups = check["groups"]
        missing_groups = []
        for gi, group in enumerate(groups):
            if not any(phrase in text for phrase in group):
                missing_groups.append(group)
        if not missing_groups:
            return True, ""
        return False, f"Phrase groups with no match: {missing_groups}"

    else:
        raise ValueError(f"Unknown check type: '{check_type}' (check_id: {check_id})")


# ── Gold data loading ──

def load_gold_cases(gold_path: Path) -> dict[str, dict]:
    """Load gold cases from cases.jsonl, keyed by case_id.

    Extracts only primary_checks for scoring.
    No M1/M2/M3/M4 fields are accessed.
    """
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold cases not found: {gold_path}")

    cases: dict[str, dict] = {}
    with open(gold_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            case = json.loads(line)
            cid = case.get("case_id")
            if not cid:
                continue
            cases[cid] = {
                "case_id": cid,
                "primary_checks": case.get("primary_checks", []),
            }
    return cases


# ── Ledger loading ──

def load_ledger(ledger_path: Path) -> list[dict]:
    """Load ledger records from a JSONL file."""
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger not found: {ledger_path}")

    records = []
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            records.append(json.loads(line))
    return records


# ── Core scoring ──

def score_one(ledger_entry: dict, gold: dict[str, dict]) -> dict:
    """Score one ledger entry against its case gold.

    Args:
        ledger_entry: Single line from the ledger JSONL.
        gold: Gold case database (from load_gold_cases).

    Returns:
        ScoreRecord dict with ONLY: case_id, condition, response_text,
        checks (check_id→bool), primary_score, passed.

    Raises:
        KeyError: If case_id not in gold.
    """
    cid = ledger_entry["case_id"]
    condition = ledger_entry["condition"]

    if cid not in gold:
        raise KeyError(f"Case {cid} not found in gold data")

    case_gold = gold[cid]
    checks_list = case_gold.get("primary_checks", [])

    # Determine the text to score
    # Original condition: score raw_response (the pre-provided answer)
    # Correction conditions: score corrected_response
    if condition == "original":
        response_text = ledger_entry.get("raw_response", "")
    else:
        response_text = ledger_entry.get("corrected_response")

    # Run checks
    check_results: dict[str, bool] = {}
    check_details = []

    if response_text is None:
        # Pipeline failure — no text to score
        for chk in checks_list:
            cid_chk = chk.get("check_id", "unknown")
            check_results[cid_chk] = False
        primary_score = False
        passed = False
    else:
        for chk in checks_list:
            cid_chk = chk.get("check_id", "unknown")
            try:
                passed_chk, detail = _run_check(chk, response_text)
            except Exception as exc:
                passed_chk = False
                detail = f"Check error: {exc}"
            check_results[cid_chk] = passed_chk
            check_details.append({
                "check_id": cid_chk,
                "check_type": chk.get("type", "unknown"),
                "passed": passed_chk,
                "detail": detail,
            })
        primary_score = all(check_results.values())
        passed = primary_score

    return {
        "case_id": cid,
        "condition": condition,
        "response_text": response_text,
        "checks": check_results,
        "check_details": check_details,
        "primary_score": primary_score,
        "passed": passed,
    }


# ── Batch scoring ──

def score_ledger(ledger_path: Path, gold_path: Path,
                 output_path: Optional[Path] = None) -> list[dict]:
    """Score all entries in a ledger against gold cases.

    Args:
        ledger_path: Path to ledger JSONL (from run_evaluation.py).
        gold_path: Path to cases.jsonl (contains primary_checks).
        output_path: Optional path to write scored results JSONL.

    Returns:
        List of ScoreRecord dicts.
    """
    records = load_ledger(ledger_path)
    gold = load_gold_cases(gold_path)

    results = []
    for entry in records:
        try:
            result = score_one(entry, gold)
        except (KeyError, ValueError) as exc:
            result = {
                "case_id": entry.get("case_id", "?"),
                "condition": entry.get("condition", "?"),
                "response_text": None,
                "checks": {},
                "check_details": [],
                "primary_score": False,
                "passed": False,
                "error": str(exc),
            }
        results.append(result)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for r in results:
                # Strip check_details from output (too verbose for bulk)
                output_record = {k: v for k, v in r.items() if k != "check_details"}
                f.write(json.dumps(output_record, ensure_ascii=False) + "\n")

    return results


# ── Aggregation ──

def aggregate(results: list[dict]) -> dict[str, dict]:
    """Aggregate scores by condition.

    Args:
        results: List of ScoreRecord dicts (from score_ledger).

    Returns:
        Dict of condition → ConditionSummary.
    """
    by_condition: dict[str, list[dict]] = {}
    for r in results:
        cond = r["condition"]
        if cond not in by_condition:
            by_condition[cond] = []
        by_condition[cond].append(r)

    summaries = {}
    for cond, items in by_condition.items():
        total = len(items)
        passed_count = sum(1 for i in items if i["passed"])
        errors = sum(1 for i in items if i.get("response_text") is None)

        # Per-check pass rates
        all_check_ids: set[str] = set()
        for i in items:
            all_check_ids.update(i.get("checks", {}).keys())

        per_check_rates = {}
        for cid_check in sorted(all_check_ids):
            attempts = [i for i in items if cid_check in i.get("checks", {})]
            passes = sum(1 for i in attempts if i["checks"].get(cid_check, False))
            per_check_rates[cid_check] = round(passes / len(attempts), 3) if attempts else 0.0

        summaries[cond] = {
            "condition": cond,
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "pass_rate": round(passed_count / total, 3) if total > 0 else 0.0,
            "errors": errors,
            "per_check_pass_rate": per_check_rates,
        }

    return summaries


# ── CLI ──

def main():
    parser = argparse.ArgumentParser(
        description="CheckMyCoach v2.2 External Scorer — independent post-run evaluation"
    )
    parser.add_argument("--ledger", required=True,
                        help="Path to ledger JSONL (from run_evaluation.py)")
    parser.add_argument("--gold", required=True,
                        help="Path to cases.jsonl (contains primary_checks)")
    parser.add_argument("--output", default=None,
                        help="Output path for scored JSONL")
    parser.add_argument("--aggregate", default=None,
                        help="Output path for aggregate JSON")
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    gold_path = Path(args.gold)
    output_path = Path(args.output) if args.output else None
    agg_path = Path(args.aggregate) if args.aggregate else None

    print(f"Scoring ledger: {ledger_path}")
    print(f"Gold data:      {gold_path}")

    # Load and validate
    gold = load_gold_cases(gold_path)
    print(f"Loaded {len(gold)} gold cases")

    records = load_ledger(ledger_path)
    print(f"Loaded {len(records)} ledger records")

    # Score
    results = []
    errors = 0
    for entry in records:
        try:
            result = score_one(entry, gold)
            results.append(result)
        except Exception as exc:
            results.append({
                "case_id": entry.get("case_id", "?"),
                "condition": entry.get("condition", "?"),
                "response_text": None,
                "checks": {},
                "primary_score": False,
                "passed": False,
                "error": str(exc),
            })
            errors += 1

    # Write scored output
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for r in results:
                slim = {k: v for k, v in r.items() if k != "check_details"}
                f.write(json.dumps(slim, ensure_ascii=False) + "\n")
        print(f"Wrote scores:   {output_path}")

    # Summarize
    passed_count = sum(1 for r in results if r["passed"])
    print(f"\nResults: {passed_count}/{len(results)} passed ({errors} errors)")
    print()

    # Aggregate by condition
    summaries = aggregate(results)
    for cond, s in sorted(summaries.items()):
        print(f"  {cond:30s}  {s['passed']:2d}/{s['total']:2d} passed  ({s['pass_rate']:.1%})  {s['errors']} errors")

    if agg_path:
        agg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(agg_path, "w", encoding="utf-8") as f:
            json.dump(summaries, f, indent=2, ensure_ascii=False)
        print(f"\nWrote aggregates: {agg_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
