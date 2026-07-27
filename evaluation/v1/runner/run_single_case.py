#!/usr/bin/env python3
"""
run_single_case.py — Run one evaluation case through one or all conditions.

Frozen protocol requirements:
- All three conditions share the SAME original_answer from the case file.
- Original condition: return original_answer directly, NO API call.
- CheckMyCoach condition: runs calibrate(response=original_answer, question=input_question) from real pipeline.
- Generic condition: runs generic_correction with question+answer+evidence.

No LLM regeneration of the original answer. No UCS in evaluation output.
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

from evaluation.v1.runner.generic_correction import correct as generic_correct

# ── Frozen model config (must match execution/model_config.json) ──
MODEL_CONFIG = {
    "original": {
        "model_id": "N/A (no API call)",
        "provider": "N/A",
        "temperature": None,
        "max_tokens": None,
        "seed_policy": "not_applicable",
    },
    "generic": {
        "model_id": "openai/gpt-4o-mini",
        "provider": "openrouter",
        "temperature": 0.5,
        "max_tokens": 1024,
        "seed_policy": "not_specified",
    },
    "checkmycoach_m3": {
        "model_id": "openai/gpt-4o-mini",
        "provider": "openrouter",
        "temperature": 0.5,
        "max_tokens": 300,
        "seed_policy": "not_specified",
    },
}


# ── Case loading ──

def load_blinded_cases(cases_path: Path | None = None) -> list[dict]:
    """Load blinded cases from the JSONL file.

    Blinded cases contain only: case_id, input_question, original_answer, evidence_excerpt.
    No gold labels, no reference corrections, no target spans.
    """
    if cases_path is None:
        cases_path = REPO_ROOT / "evaluation" / "v1" / "data" / "blinded_cases.jsonl"
    if not cases_path.exists():
        raise FileNotFoundError(f"Blinded cases not found at {cases_path}")

    cases = []
    with open(cases_path, encoding="utf-8") as f:
        for line in f:
            case = json.loads(line)
            # Verify no gold fields
            for field in ["target_failure_span", "failure_statement", "failure_family",
                          "primary_checks", "secondary_checks", "reference_correction",
                          "forbidden_new_claims", "content_required_to_change",
                          "required_boundary", "adjudication_status"]:
                if field in case:
                    raise ValueError(f"Gold field leaked into blinded cases: {field}")
            cases.append(case)
    return cases


def load_case_by_id(case_id: str, cases: list[dict]) -> dict:
    """Find a case by its ID in the loaded case list."""
    for case in cases:
        if case["case_id"] == case_id:
            return case
    raise FileNotFoundError(f"Case {case_id} not found")


# ── Prompt / evidence hashing ──

def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _hash_evidence(evidence_payload: list) -> str:
    raw = json.dumps(evidence_payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ── Condition runners ──

def run_original(original_answer: str) -> dict:
    """Original condition: return the pre-provided answer directly. No API call."""
    return {
        "condition": "original",
        "raw_response": original_answer,
        "corrected_response": None,
        "included": True,
        "error": None,
    }


def run_checkmycoach(original_response: str, question: str) -> dict:
    """CheckMyCoach condition: run calibrate pipeline on the original response.

    Executes M1 detection, M2 diagnosis, M3 correction, M4 validation.
    """
    from pipeline.agent_pipeline import calibrate
    try:
        result = calibrate(response=original_response, question=question)
        return {
            "condition": "checkmycoach",
            "raw_response": original_response,
            "corrected_response": result.get("corrected_response"),
            "m4_passed": result.get("m4_passed"),
            "needs_calibration": result.get("needs_calibration"),
            "failure_type": result.get("failure_type"),
            "m2_confidence": result.get("m2_confidence"),
            "correction_trace": {
                "failure_type": result.get("failure_type"),
                "m2_confidence": result.get("m2_confidence"),
                "corrected_response": result.get("corrected_response"),
            },
            "validation_trace": {
                "m4_passed": result.get("m4_passed"),
            },
            "evidence_ids": [e.get("id", "") for e in (result.get("evidence") or [])],
            "token_usage": result.get("token_usage", {}),
            "latency_ms": (result.get("latency_ms") or {}).get("total", 0),
            "included": result.get("success", True),
            "error": result.get("error"),
        }
    except Exception as exc:
        return {
            "condition": "checkmycoach",
            "raw_response": original_response,
            "corrected_response": None,
            "evidence_ids": [],
            "token_usage": {},
            "latency_ms": 0,
            "included": False,
            "error": f"CMC_PIPELINE_ERROR: {exc}",
        }


def run_generic(original_response: str, question: str, evidence_payload: list | None = None) -> dict:
    """Generic condition: evidence-based revision using frozen prompt.

    Does NOT receive failure_type, target_span, or gold labels.
    On API failure: included=False (fail closed).
    """
    correction = generic_correct(
        question=question,
        original_answer=original_response,
        evidence_payload=evidence_payload or [],
    )

    return {
        "condition": "generic",
        "raw_response": original_response,
        "corrected_response": correction.corrected_text,
        "correction_trace": {
            "prompt_source": "frozen GENERIC_BASELINE_PROMPT.txt",
            "model": correction.model,
            "temperature": correction.temperature,
            "llm_source": correction.source,
        },
        "evidence_ids": [e.get("id", "") for e in (evidence_payload or [])],
        "token_usage": correction.token_usage or {},
        "latency_ms": 0,
        "included": correction.source != "fallback" if hasattr(correction, 'source') else True,
        "error": correction.error if hasattr(correction, 'error') and correction.error else None,
    }


# ── Evidence ──

def collect_case_evidence(question: str, case: dict) -> list:
    """Collect evidence: from case evidence_excerpt, or via retrieval."""
    excerpt = case.get("evidence_excerpt") or ""
    if excerpt:
        return [{"id": "case_evidence", "type": "inline", "content": excerpt[:500], "source": "case file"}]
    # No fallback retrieval — if no excerpt, empty evidence is used
    return []


# ── Result schema validator ──

def validate_result_record(record: dict):
    """Validate that a result record conforms to the expected schema."""
    required = ["run_id", "case_id", "condition", "model_id", "provider",
                "temperature", "max_tokens", "seed_policy", "request_id",
                "response_id", "timestamp", "included"]
    for field in required:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")
    if "error" in record and record.get("error") and record.get("included") is not False:
        raise ValueError(f"Record has error but included=True: {record.get('error')}")


# ── Build provenance record ──

def _get_condition_model_config(condition: str) -> dict:
    condition_key = condition if condition != "checkmycoach" else "checkmycoach_m3"
    return MODEL_CONFIG.get(condition_key, MODEL_CONFIG["original"])


def build_record(run_id: str, case_id: str, condition: str, result: dict,
                 question: str, evidence_payload: list, temperature: float,
                 seed: int | None, start_time: float) -> dict:
    """Build a complete provenance record for one condition result."""
    model_cfg = _get_condition_model_config(condition)
    elapsed = (time.perf_counter() - start_time) * 1000 if start_time else 0
    request_id = f"{run_id}_{case_id}_{condition}_req"
    response_id = f"{run_id}_{case_id}_{condition}_resp"

    record = {
        "run_id": run_id,
        "case_id": case_id,
        "condition": condition,
        "model_id": result.get("model", model_cfg["model_id"]),
        "provider": model_cfg["provider"],
        "temperature": result.get("temperature", model_cfg["temperature"]),
        "max_tokens": model_cfg["max_tokens"],
        "seed_policy": model_cfg["seed_policy"],
        "request_id": request_id,
        "response_id": response_id,
        "fallback_status": result.get("correction_trace", {}).get("llm_source", "N/A")
            if condition == "generic" else "N/A",
        "prompt_hash": "",
        "evidence_hash": _hash_evidence(evidence_payload),
        "retry_count": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "included": result.get("included", False),
        "error": result.get("error"),
        "raw_response": result.get("raw_response", ""),
        "corrected_response": result.get("corrected_response"),
        "latency_ms": result.get("latency_ms", 0) or elapsed,
    }

    # Add condition-specific fields
    if condition == "original":
        record["corrected_response"] = None
    elif condition == "generic":
        record["correction_trace"] = result.get("correction_trace", {})
        record["evidence_ids"] = result.get("evidence_ids", [])
        record["token_usage"] = result.get("token_usage", {})
    elif condition == "checkmycoach":
        record["correction_trace"] = result.get("correction_trace", {})
        record["validation_trace"] = result.get("validation_trace", {})
        record["evidence_ids"] = result.get("evidence_ids", [])
        record["token_usage"] = result.get("token_usage", {})
        record["m4_passed"] = result.get("m4_passed")
        record["needs_calibration"] = result.get("needs_calibration")
        record["failure_type"] = result.get("failure_type")

    record["latency_ms"] = result.get("latency_ms", 0) or elapsed

    if record.get("included") is None:
        record["included"] = record.get("error") is None

    validate_result_record(record)
    return record


# ── Dry run ──

def dry_run_print(case: dict, condition: str):
    """Print what would happen without making API calls."""
    question = case.get("input_question", "")
    print(f"[DRY RUN] case_id={case['case_id']} condition={condition}")
    print(f"  question: {question[:60]}...")
    if condition == "original":
        print(f"  pipeline: return pre-provided original_answer (NO API call)")
    elif condition == "generic":
        print(f"  pipeline: original_answer -> generic_correct(question+answer+evidence)")
    elif condition == "checkmycoach":
        print(f"  pipeline: original_answer -> calibrate(response,question) -> M1 -> M2 -> M3 -> M4")
    print(f"  [DRY RUN] No API calls made.")


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Run one evaluation case.")
    parser.add_argument("--case-id", required=True, help="Case identifier")
    parser.add_argument("--condition", choices=["original", "generic", "checkmycoach", "all"],
                        default="original")
    parser.add_argument("--dry-run", action="store_true", help="Print without API calls")
    parser.add_argument("--temperature", type=float, default=0.5, help="LLM temperature")
    parser.add_argument("--seed", type=int, default=None, help="LLM seed if supported")
    args = parser.parse_args()

    all_cases = load_blinded_cases()
    case = load_case_by_id(args.case_id, all_cases)
    question = case["input_question"]
    original_answer = case["original_answer"]

    if not question:
        print(f"ERROR: case {case['case_id']} has no input_question")
        return 1
    if not original_answer:
        print(f"ERROR: case {case['case_id']} has no original_answer")
        return 1

    if args.dry_run:
        if args.condition == "all":
            for cond in ["original", "generic", "checkmycoach"]:
                dry_run_print(case, cond)
        else:
            dry_run_print(case, args.condition)
        print("\n[DRY RUN] Complete. No API calls or file writes performed.")
        return 0

    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    conditions = ["original", "generic", "checkmycoach"] if args.condition == "all" else [args.condition]

    # All three conditions share the SAME original_answer (pre-provided, no regeneration)
    print(f"Case: {case['case_id']}: {question[:50]}...")
    print(f"  original_answer ({len(original_answer)} chars): {original_answer[:80]}...")

    # Collect evidence once for all conditions
    evidence = collect_case_evidence(question, case)

    results = []
    for cond in conditions:
        start = time.perf_counter()
        try:
            if cond == "original":
                result = run_original(original_answer)
            elif cond == "generic":
                result = run_generic(original_answer, question, evidence)
            elif cond == "checkmycoach":
                result = run_checkmycoach(original_answer, question)
            else:
                result = {"condition": cond, "error": "Unknown condition", "included": False}
        except Exception as exc:
            result = {"condition": cond, "error": f"RUNNER_ERROR: {exc}", "included": False}

        record = build_record(run_id, case["case_id"], cond, result, question, evidence,
                              args.temperature, args.seed, start)
        results.append(record)

    # Print summary
    print(f"\nRun ID: {run_id}")
    print(f"Case: {case['case_id']}")
    for r in results:
        status = "OK" if r["included"] else "ERR"
        error_info = f" error={r['error'][:60]}" if r.get("error") else ""
        corr = r.get("corrected_response", "")
        print(f"  [{status}] {r['condition']}: lat={r['latency_ms']:.0f}ms corr={len(corr) if corr else 0}chars{error_info}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
