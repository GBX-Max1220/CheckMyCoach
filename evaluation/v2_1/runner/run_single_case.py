"""
run_single_case.py — Run one evaluation case through one or all conditions.

v2.1 changes:
- 4 conditions: original, generic, generic_with_diagnosis, checkmycoach
- Evidence symmetry via evidence_router
- Generic+Diagnosis receives oracle diagnosis from blinded case
- Temperature 0.3, max_tokens 1024 (protocol §3.3)

Protocol reference: §4 conditions, §5 evidence equalization
"""

import argparse
import hashlib
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evaluation.v2_1.runner.evidence_router import route_evidence
from evaluation.v2_1.runner.conditions.original import run_original
from evaluation.v2_1.runner.conditions.generic import run_generic
from evaluation.v2_1.runner.conditions.generic_plus import run_generic_plus
from evaluation.v2_1.runner.conditions.checkmycoach import run_checkmycoach


# ── Global oracle diagnoses cache (loaded once per run) ──
_oracle_diagnoses: dict[str, dict] | None = None


# ── Frozen model config (must match model_config.json) ──
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
        "temperature": 0.3,
        "max_tokens": 1024,
        "seed_policy": "not_specified",
    },
    "generic_with_diagnosis": {
        "model_id": "openai/gpt-4o-mini",
        "provider": "openrouter",
        "temperature": 0.3,
        "max_tokens": 1024,
        "seed_policy": "not_specified",
    },
    "checkmycoach_m3": {
        "model_id": "openai/gpt-4o-mini",
        "provider": "openrouter",
        "temperature": 0.3,  # Equalized with Generic conditions — v2.2
        "max_tokens": 1024,
        "seed_policy": "not_specified",
    },
}

# ── Valid conditions ──
ALL_CONDITIONS = ["original", "generic", "generic_with_diagnosis", "checkmycoach"]


# ── Blinded case loading (v2.2 — 4 fields only) ──

BLINDED_FIELDS_V2_2 = ["case_id", "input_question", "original_answer", "evidence_excerpt"]
FORBIDDEN_BLINDED_FIELDS = [
    "reference_correction", "primary_checks", "secondary_checks",
    "supported_content_to_retain", "forbidden_new_claims",
    "linked_knowledge_object_ids", "source_provenance",
    "ambiguity_flags", "adjudication_status",
    "failure_family", "target_failure_span", "failure_statement",
    "content_required_to_change", "required_boundary",
]

def load_blinded_cases(cases_path: Path | None = None) -> list[dict]:
    """Load v2.2 blinded cases — ONLY 4 fields.

    Used by: Original, Generic, CMC.
    Contains NO oracle diagnosis fields.
    """
    if cases_path is None:
        cases_path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.2.jsonl"
    if not cases_path.exists():
        raise FileNotFoundError(f"Blinded cases not found at {cases_path}")

    cases = []
    with open(cases_path, encoding="utf-8") as f:
        for line in f:
            case = json.loads(line)
            # Verify ONLY the 4 permitted fields
            extra = set(case.keys()) - set(BLINDED_FIELDS_V2_2)
            if extra:
                raise ValueError(f"Forbidden fields in blinded case: {extra}")
            cases.append(case)
    return cases


def load_case_by_id(case_id: str, cases: list[dict]) -> dict:
    for case in cases:
        if case["case_id"] == case_id:
            return case
    raise FileNotFoundError(f"Case {case_id} not found")


def load_oracle_diagnoses(path: Path | None = None) -> dict[str, dict]:
    """Load oracle diagnosis file — keyed by case_id.

    Used ONLY by Generic+Diagnosis condition.
    Contains: failure_family, target_failure_span, failure_statement,
              content_required_to_change, required_boundary.
    """
    if path is None:
        path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "oracle_diagnosis_v2.2.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Oracle diagnosis file not found at {path}")

    diagnoses = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            diagnoses[entry["case_id"]] = entry
    return diagnoses


# ── Evidence hashing ──

def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _hash_evidence(evidence_payload: list) -> str:
    raw = json.dumps(evidence_payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ── Condition runners ──

def build_record(
    run_id: str,
    case_id: str,
    condition: str,
    result: dict,
    question: str,
    evidence_payload: list,
    temperature: float,
    seed: int | None,
    start_time: float,
) -> dict:
    """Build a complete provenance record for one condition result."""
    model_cfg = _get_condition_model_config(condition)
    elapsed = (time.perf_counter() - start_time) * 1000 if start_time else 0
    request_id = f"{run_id}_{case_id}_{condition}_req"
    response_id = f"{run_id}_{case_id}_{condition}_resp"

    record = {
        "run_id": run_id,
        "case_id": case_id,
        "condition": condition,
        "execution_order": result.get("execution_order", list(ALL_CONDITIONS)),
        "model_id": result.get("model", model_cfg["model_id"]),
        "provider": model_cfg["provider"],
        "temperature": result.get("temperature", model_cfg["temperature"]),
        "max_tokens": model_cfg["max_tokens"],
        "seed_policy": model_cfg["seed_policy"],
        "request_id": request_id,
        "response_id": response_id,
        "fallback_status": result.get("correction_trace", {}).get("llm_source", "N/A")
            if condition in ("generic", "generic_with_diagnosis") else "N/A",
        "prompt_hash": _hash_text(json.dumps(result.get("correction_trace", {}))),
        "evidence_hash": _hash_evidence(evidence_payload),
        "retry_count": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "included": result.get("included", False),
        "error": result.get("error"),
        "raw_response": result.get("raw_response", ""),
        "corrected_response": result.get("corrected_response"),
        "latency_ms": result.get("latency_ms", 0) or elapsed,
    }

    # Condition-specific fields
    if condition == "original":
        record["corrected_response"] = None
    elif condition in ("generic", "generic_with_diagnosis"):
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
        record["correction_source"] = result.get("correction_source", "N/A")

    if record.get("included") is None:
        record["included"] = record.get("error") is None

    _validate_result_record(record)
    return record


def _get_condition_model_config(condition: str) -> dict:
    config_key = condition if condition != "checkmycoach" else "checkmycoach_m3"
    return MODEL_CONFIG.get(config_key, MODEL_CONFIG["original"])


def _validate_result_record(record: dict):
    required = ["run_id", "case_id", "condition", "model_id", "provider",
                "temperature", "max_tokens", "seed_policy", "request_id",
                "response_id", "timestamp", "included", "execution_order"]
    for field in required:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")
    if record.get("error") and record.get("included") is not False:
        raise ValueError(f"Record has error but included=True: {record.get('error')}")


# ── Condition ordering (Fix 4: randomized per case) ──

def get_randomized_conditions(case_id: str) -> list[str]:
    """Return conditions in a deterministic random order based on case_id.

    Uses case_id as seed so order is reproducible per case but differs
    across cases. Does not modify within-condition logic.
    """
    rng = random.Random(case_id + "_v2.2")
    conds = list(ALL_CONDITIONS)
    rng.shuffle(conds)
    return conds


# ── Condition dispatch ──

def ensure_oracle_diagnoses_loaded():
    """Lazy-load oracle diagnoses file. Cached globally for run duration."""
    global _oracle_diagnoses
    if _oracle_diagnoses is None:
        _oracle_diagnoses = load_oracle_diagnoses()


def run_condition(
    condition: str,
    case: dict,
    question: str,
    original_answer: str,
    evidence_payload: list,
    execution_order: list[str] | None = None,
) -> dict:
    """Dispatch to the correct condition runner.

    Args:
        condition: One of ALL_CONDITIONS.
        case: Blinded case (4 fields: case_id, input_question, original_answer, evidence_excerpt).
        question, original_answer, evidence_payload: Standard inputs.
        execution_order: The full ordered list of conditions for this case (stored in result).

    Returns:
        Dict with condition result including execution_order metadata.
    """
    base_result = None
    if condition == "original":
        base_result = run_original(original_answer)
    elif condition == "generic":
        base_result = run_generic(original_answer, question, evidence_payload)
    elif condition == "generic_with_diagnosis":
        # Oracle diagnosis loaded from SEPARATE file — NOT from blinded case (Fix 3)
        ensure_oracle_diagnoses_loaded()
        oracle = _oracle_diagnoses.get(case["case_id"], {}) if _oracle_diagnoses else {}
        # Fail closed: Generic+Diagnosis requires oracle fields
        if not oracle.get("failure_family"):
            return {
                "condition": condition,
                "error": "ORACLE_DIAGNOSIS_MISSING",
                "included": False,
                "raw_response": "",
                "corrected_response": None,
                "execution_order": execution_order,
            }
        base_result = run_generic_plus(
            original_answer=original_answer,
            question=question,
            evidence_payload=evidence_payload,
            failure_family=oracle.get("failure_family"),
            target_failure_span=oracle.get("target_failure_span"),
            failure_statement=oracle.get("failure_statement"),
            content_required_to_change=oracle.get("content_required_to_change"),
            required_boundary=oracle.get("required_boundary"),
        )
    elif condition == "checkmycoach":
        base_result = run_checkmycoach(original_answer, question, evidence_payload)
    else:
        return {"condition": condition, "error": f"Unknown condition: {condition}", "included": False}

    # Attach execution_order to every result for provenance
    if base_result and execution_order is not None:
        base_result["execution_order"] = execution_order
    return base_result or {"condition": condition, "error": "Empty result", "included": False}


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
    elif condition == "generic_with_diagnosis":
        print(f"  pipeline: original_answer -> generic_correct(question+answer+evidence+oracle_diagnosis)")
    elif condition == "checkmycoach":
        print(f"  pipeline: original_answer -> calibrate(response,question,evidence) -> M1->M2->M3->M4")
    print(f"  [DRY RUN] No API calls made.")


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Run one evaluation case.")
    parser.add_argument("--case-id", required=True, help="Case identifier")
    parser.add_argument("--condition", choices=ALL_CONDITIONS + ["all"], default="original")
    parser.add_argument("--dry-run", action="store_true", help="Print without API calls")
    parser.add_argument("--temperature", type=float, default=0.3, help="LLM temperature (protocol §3.3)")
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

    # Evidence from router — same for all conditions (protocol §5)
    evidence_payload = route_evidence(case).structured

    if args.dry_run:
        conditions = ALL_CONDITIONS if args.condition == "all" else [args.condition]
        for cond in conditions:
            dry_run_print(case, cond)
        print("\n[DRY RUN] Complete. No API calls or file writes performed.")
        return 0

    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    if args.condition == "all":
        conditions = get_randomized_conditions(case["case_id"])
    else:
        conditions = [args.condition]

    print(f"Case: {case['case_id']}: {question[:50]}...")
    print(f"  original_answer ({len(original_answer)} chars): {original_answer[:80]}...")
    print(f"  evidence: {len(evidence_payload)} items, hash={_hash_evidence(evidence_payload)}")
    print(f"  execution_order: {conditions}")
    if "generic_with_diagnosis" in conditions:
        oracle = load_oracle_diagnoses().get(case["case_id"], {})
        print(f"  diagnosis: family={oracle.get('failure_family')}, span='{str(oracle.get('target_failure_span', ''))[:40]}...'")

    results = []
    for cond in conditions:
        start = time.perf_counter()
        try:
            result = run_condition(cond, case, question, original_answer, evidence_payload,
                                    execution_order=conditions)
        except Exception as exc:
            result = {"condition": cond, "error": f"RUNNER_ERROR: {exc}", "included": False,
                      "execution_order": conditions}

        record = build_record(run_id, case["case_id"], cond, result, question,
                              evidence_payload, args.temperature, args.seed, start)
        results.append(record)

    print(f"\nRun ID: {run_id}")
    for r in results:
        status = "OK" if r["included"] else "ERR"
        error_info = f" error={r['error'][:60]}" if r.get("error") else ""
        corr = r.get("corrected_response", "")
        print(f"  [{status}] {r['condition']}: lat={r['latency_ms']:.0f}ms corr={len(corr) if corr else 0}chars{error_info}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
