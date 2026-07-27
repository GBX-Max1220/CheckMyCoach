#!/usr/bin/env python3
"""
run_evaluation.py — Batch evaluation runner for CheckMyCoach.

Loads blinded cases (no gold labels), runs three conditions from the SAME
pre-provided original_answer. No LLM regeneration of the original answer.

State machine: PREFLIGHT -> RUNNING -> COMPLETED / STOPPED / ABORTED
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v1.runner.run_single_case import (
    load_blinded_cases,
    run_original,
    run_generic,
    run_checkmycoach,
    collect_case_evidence,
    build_record,
)


def run_preflight_check() -> bool:
    """Run environment validation before starting batch."""
    try:
        from evaluation.v1.runner.validate_environment import main as preflight
        result = preflight()
        return result == 0
    except Exception as exc:
        print(f"[PREFLIGHT] Exception during validation: {exc}")
        return False


def run_batch(cases: list[dict], conditions: list[str], ledger_path: Path,
              dry_run: bool = False, limit: int = 0,
              temperature: float = 0.5, seed: int | None = None) -> dict:
    """Run all cases through all conditions, appending to ledger."""
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    results = []
    total = min(len(cases), limit) if limit > 0 else len(cases)
    errors = 0

    for idx, case in enumerate(cases[:total] if limit > 0 else cases):
        question = case["input_question"]
        original_answer = case["original_answer"]
        print(f"\n[{idx+1}/{total}] {case['case_id']}: {question[:50]}...")

        if not original_answer:
            print(f"  ERROR: no original_answer for {case['case_id']}")
            for cond in conditions:
                record = {
                    "run_id": run_id, "case_id": case["case_id"], "condition": cond,
                    "model_id": "N/A", "provider": "N/A", "temperature": None,
                    "max_tokens": None, "seed_policy": "not_applicable",
                    "request_id": f"{run_id}_{case['case_id']}_{cond}_req",
                    "response_id": f"{run_id}_{case['case_id']}_{cond}_resp",
                    "fallback_status": "N/A", "prompt_hash": "", "evidence_hash": "",
                    "retry_count": 0, "timestamp": datetime.now(timezone.utc).isoformat(),
                    "included": False, "error": f"MISSING_ORIGINAL_ANSWER",
                    "raw_response": "", "corrected_response": None, "latency_ms": 0,
                }
                results.append(record)
            errors += 1
            continue

        # Collect evidence once, shared across conditions
        evidence = collect_case_evidence(question, case)

        for cond in conditions:
            if dry_run:
                print(f"  [DRY RUN] case={case['case_id']} condition={cond}")
                continue

            start = time.perf_counter()
            try:
                if cond == "original":
                    result = run_original(original_answer)
                elif cond == "generic":
                    result = run_generic(original_answer, question, evidence)
                elif cond == "checkmycoach":
                    result = run_checkmycoach(original_answer, question)
                else:
                    result = {"condition": cond, "error": f"Unknown condition: {cond}", "included": False}
            except Exception as exc:
                result = {"condition": cond, "error": f"RUNNER_ERROR: {exc}", "included": False}

            record = build_record(run_id, case["case_id"], cond, result, question,
                                  evidence, temperature, seed, start)
            results.append(record)

            status = "OK" if record["included"] else "ERR"
            error_info = f" error={record['error'][:60]}" if record.get("error") else ""
            print(f"  [{status}] {cond}: lat={record['latency_ms']:.0f}ms{error_info}")
            if not record["included"]:
                errors += 1

        # Incremental write
        if not dry_run:
            with open(ledger_path, "a", encoding="utf-8") as f:
                for r in results[-len(conditions):]:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return {
        "run_id": run_id,
        "total_cases": total,
        "total_results": len(results),
        "errors": errors,
        "conditions": conditions,
        "ledger_path": str(ledger_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Batch evaluation runner")
    parser.add_argument("--dry-run", action="store_true", help="Print without API calls")
    parser.add_argument("--condition", choices=["original", "generic", "checkmycoach", "all"],
                        default="all")
    parser.add_argument("--limit", type=int, default=0, help="Limit cases processed")
    parser.add_argument("--output-dir", default=None, help="Custom output directory")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip environment validation")
    parser.add_argument("--temperature", type=float, default=0.5, help="LLM temperature")
    parser.add_argument("--seed", type=int, default=None, help="LLM seed if supported")
    args = parser.parse_args()

    # === PREFLIGHT ===
    if not args.skip_preflight and not args.dry_run:
        print("[PREFLIGHT] Running environment validation...")
        preflight_ok = run_preflight_check()
        if not preflight_ok:
            print("[PREFLIGHT] FAILED — aborting.")
            return 2
        print("[PREFLIGHT] PASSED")

    # === DISCOVERY ===
    try:
        cases = load_blinded_cases()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        print("Run 'python evaluation/v1/data/blinded_cases.jsonl' creator first.")
        return 1

    if not cases:
        print("No blinded cases found.")
        return 1

    print(f"Loaded {len(cases)} blinded cases")
    if args.limit > 0:
        print(f"  --limit {args.limit}")

    conditions = ["original", "generic", "checkmycoach"] if args.condition == "all" else [args.condition]
    print(f"Conditions: {conditions}")

    output_dir = Path(args.output_dir) if args.output_dir else REPO_ROOT / "evaluation" / "v1"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        ledger_path = output_dir / "dry_run_ledger.jsonl"
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ledger_path = output_dir / f"ledger_{stamp}.jsonl"

    # === RUNNING ===
    summary = run_batch(cases, conditions, ledger_path,
                        dry_run=args.dry_run, limit=args.limit,
                        temperature=args.temperature, seed=args.seed)

    # === COMPLETED / STOPPED ===
    print(f"\n{'='*60}")
    print("Batch Complete")
    print(f"{'='*60}")
    print(f"  Run ID:     {summary['run_id']}")
    print(f"  Cases:      {summary['total_cases']}")
    print(f"  Results:    {summary['total_results']}")
    print(f"  Errors:     {summary['errors']}")
    print(f"  Ledger:     {summary['ledger_path']}")
    if args.dry_run:
        print("  (DRY RUN — no API calls made)")
    final_status = "STOPPED (with errors)" if summary['errors'] > 0 else "COMPLETED"
    print(f"  Status:     {final_status}")

    return 1 if summary["errors"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
