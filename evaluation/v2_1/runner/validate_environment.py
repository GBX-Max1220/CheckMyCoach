#!/usr/bin/env python3
"""
validate_environment.py — Preflight environment check for v2.1 evaluation runner.

Checks:
1. v2.1 blinded case file integrity
2. API key presence
3. Core module imports
4. Schema validity
5. Pipeline imports (not executed, just importable)

Usage:
    python -m evaluation.v2_1.runner.validate_environment
"""

import importlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

CHECKS: list[dict] = []


def check(name: str, passed: bool, detail: str = ""):
    CHECKS.append({"name": name, "passed": passed, "detail": detail})
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("=" * 60)
    print("CheckMyCoach Evaluation v2.1 — Environment Validation")
    print("=" * 60)

    # 1. v2.1 blinded case file
    cases_path = REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.1.jsonl"
    if cases_path.exists():
        with open(cases_path, encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        check(f"Blinded cases: {len(lines)} cases", len(lines) == 40, f"expected 40, got {len(lines)}")
    else:
        check("Blinded cases file", False, "file not found")

    # 2. API keys
    for key_name in ["OPENROUTER_API_KEY", "DEEPSEEK_API_KEY"]:
        key = os.getenv(key_name)
        if key:
            check(f"API key: {key_name}", True, f"present (len={len(key)})")
        else:
            check(f"API key: {key_name}", False, "not set")

    # 3. v2.1 case schema verification
    schema_check = True
    if cases_path.exists():
        with open(cases_path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    case = json.loads(line)
                    required = ["case_id", "input_question", "original_answer", "evidence_excerpt"]
                    for field in required:
                        if field not in case or not case.get(field):
                            check(f"Case {i}: missing '{field}'", False)
                            schema_check = False
                            break
                except json.JSONDecodeError as e:
                    check(f"Case {i}: JSON decode", False, str(e))
                    schema_check = False
    check("Case schema: all required fields present", schema_check)

    # 4. Core module imports
    modules = [
        "evaluation.v2_1.runner.evidence_router",
        "evaluation.v2_1.runner.conditions.original",
        "evaluation.v2_1.runner.conditions.generic",
        "evaluation.v2_1.runner.conditions.generic_plus",
        "evaluation.v2_1.runner.conditions.checkmycoach",
        "evaluation.v2_1.schemas.result",
    ]
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
            check(f"Module: {mod_name}", True)
        except ImportError as e:
            check(f"Module: {mod_name}", False, str(e))

    # 5. Pipeline modules (importable)
    pipeline_modules = [
        "pipeline.agent_pipeline",
        "calibration_agent.m1_detection",
        "calibration_agent.m2_diagnosis",
        "calibration_agent.m3_correction",
        "calibration_agent.m4_validation",
        "config",
        "schema",
        "evidence.base",
        "evidence.retriever",
    ]
    for mod_name in pipeline_modules:
        try:
            importlib.import_module(mod_name)
            check(f"Pipeline: {mod_name}", True)
        except ImportError as e:
            check(f"Pipeline: {mod_name}", False, str(e))

    # 6. Result output
    print("=" * 60)
    failed = sum(1 for c in CHECKS if not c["passed"])
    print(f"Result: {len(CHECKS) - failed}/{len(CHECKS)} passed")
    if failed:
        print(f"WARNING: {failed} check(s) failed.")
        return 1
    print("Environment validation PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
