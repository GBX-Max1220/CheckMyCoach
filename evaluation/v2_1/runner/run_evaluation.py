#!/usr/bin/env python3
"""
run_evaluation.py — Batch evaluation runner for CheckMyCoach v2.2.

Loads blinded v2.2 cases (4 fields only; oracle diagnosis loaded separately),
runs 4 conditions from the SAME pre-provided original_answer.
No LLM regeneration of the original answer.
Conditions are deterministically randomized per case (get_randomized_conditions).

States: PREFLIGHT -> RUNNING -> COMPLETED / STOPPED

Protocol reference: v2.2 EVALUATION_PROTOCOL.md
"""

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v2_1.runner.run_single_case import (
    load_blinded_cases,
    build_record,
    run_condition,
    get_randomized_conditions,
    ALL_CONDITIONS,
)
from evaluation.v2_1.runner.evidence_router import route_evidence


def _get_git_commit() -> str:
    """Get the current git commit hash. Returns 'unknown' if not available."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def run_freeze_check() -> bool:
    """Run freeze integrity check before any execution. Must pass first."""
    try:
        from evaluation.v2_1.runner.preflight_v2_2 import main as freeze_check
        result = freeze_check()
        return result == 0
    except Exception as exc:
        print(f"[FREEZE CHECK] Exception: {exc}")
        return False


def run_preflight_check() -> bool:
    """Run environment validation after freeze check passes."""
    try:
        from evaluation.v2_1.runner.validate_environment import main as preflight
        result = preflight()
        return result == 0
    except Exception as exc:
        print(f"[PREFLIGHT] Exception during validation: {exc}")
        return False


def run_batch(
    cases: list[dict],
    conditions: list[str],
    ledger_path: Path,
    dry_run: bool = False,
    limit: int = 0,
) -> dict:
    """Run all cases through all conditions, appending to ledger."""
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    results = []
    total = min(len(cases), limit) if limit > 0 else len(cases)
    errors = 0

    for idx, case in enumerate(cases[:total] if limit > 0 else cases):
        cid = case["case_id"]
        question = case["input_question"]
        original_answer = case["original_answer"]

        print(f"\n[{idx+1}/{total}] {cid}: {question[:50]}...")

        # Randomized condition order per case (Fix 4)
        case_conditions = get_randomized_conditions(cid)

        if not original_answer:
            print(f"  ERROR: no original_answer for {cid}")
            for cond in case_conditions:
                record = {
                    "run_id": run_id, "case_id": cid, "condition": cond,
                    "execution_order": case_conditions,
                    "model_id": "N/A", "provider": "N/A", "temperature": None,
                    "max_tokens": None, "seed_policy": "not_applicable",
                    "request_id": f"{run_id}_{cid}_{cond}_req",
                    "response_id": f"{run_id}_{cid}_{cond}_resp",
                    "fallback_status": "N/A", "prompt_hash": "", "evidence_hash": "",
                    "retry_count": 0, "timestamp": datetime.now(timezone.utc).isoformat(),
                    "included": False, "error": "MISSING_ORIGINAL_ANSWER",
                    "raw_response": "", "corrected_response": None, "latency_ms": 0,
                }
                results.append(record)
            errors += 1
            continue

        # Evidence from router — same payload for all conditions (protocol §5)
        evidence_payload = route_evidence(case).structured
        print(f"  execution_order: {case_conditions}")
        print(f"  evidence_hash: {hashlib.sha256(json.dumps(evidence_payload, sort_keys=True).encode('utf-8')).hexdigest()[:16]}")

        for cond in case_conditions:
            if dry_run:
                print(f"  [DRY RUN] case={cid} condition={cond}")
                continue

            start = time.perf_counter()
            try:
                result = run_condition(cond, case, question, original_answer, evidence_payload,
                                        execution_order=case_conditions)
            except Exception as exc:
                result = {"condition": cond, "error": f"RUNNER_ERROR: {exc}", "included": False,
                          "execution_order": case_conditions}

            record = build_record(run_id, cid, cond, result, question,
                                  evidence_payload, 0.3, None, start)
            results.append(record)

            status = "OK" if record["included"] else "ERR"
            error_info = f" error={record['error'][:60]}" if record.get("error") else ""
            print(f"  [{status}] {cond}: lat={record['latency_ms']:.0f}ms{error_info}")
            if not record["included"]:
                errors += 1

        # Incremental write
        if not dry_run:
            with open(ledger_path, "a", encoding="utf-8") as f:
                for r in results[-len(case_conditions):]:
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
    parser = argparse.ArgumentParser(description="CheckMyCoach Evaluation v2.1 batch runner")
    parser.add_argument("--dry-run", action="store_true", help="Print without API calls")
    parser.add_argument("--condition", choices=ALL_CONDITIONS + ["all"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="Limit cases processed")
    parser.add_argument("--output-dir", default=None, help="Custom output directory")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip environment validation")
    args = parser.parse_args()

    # === FREEZE CHECK (must pass before any execution) ===
    if not args.skip_preflight and not args.dry_run:
        print("[FREEZE CHECK] Running freeze integrity check...")
        freeze_ok = run_freeze_check()
        if not freeze_ok:
            print("[FREEZE CHECK] FAILED — aborting. No API calls made.")
            return 2
        print("[FREEZE CHECK] PASSED — execution package intact.")

        # === PREFLIGHT (environment validation) ===
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
        return 1

    if not cases:
        print("No blinded cases found.")
        return 1

    print(f"Loaded {len(cases)} blinded v2.1 cases")
    if args.limit > 0:
        print(f"  --limit {args.limit}")

    conditions = ALL_CONDITIONS if args.condition == "all" else [args.condition]
    print(f"Conditions: {conditions}")

    output_dir = Path(args.output_dir) if args.output_dir else REPO_ROOT / "evaluation" / "v2_1"
    output_dir.mkdir(parents=True, exist_ok=True)

    exec_dir = output_dir / "execution_v2.2"
    exec_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        ledger_path = exec_dir / "dry_run_ledger_v2.2.jsonl"
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ledger_path = exec_dir / f"ledger_v2.2_{stamp}.jsonl"

    # === RUNNING ===
    summary = run_batch(cases, conditions, ledger_path,
                        dry_run=args.dry_run, limit=args.limit)

    # === COMPLETED / STOPPED ===
    print(f"\n{'='*60}")
    print("v2.2 Batch Complete")
    print(f"  Protocol version: v2.2")
    print(f"  Git commit:       {_get_git_commit()}")
    print(f"  Timestamp:        {datetime.now(timezone.utc).isoformat()}")
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
