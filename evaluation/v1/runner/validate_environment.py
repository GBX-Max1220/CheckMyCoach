#!/usr/bin/env python3
"""
validate_environment.py — Preflight environment check for evaluation runner.

Checks:
1. KC import
2. API key presence
3. Schema validity
4. Case file integrity
5. Core module imports

Usage:
    python -m evaluation.v1.runner.validate_environment
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
    print("CheckMyCoach Evaluation — Environment Validation")
    print("=" * 60)

    # 1. Knowledge Compiler
    try:
        import knowledge_compiler
        check("Knowledge Compiler import", True, f"module={knowledge_compiler.__name__}")
    except ImportError as e:
        check("Knowledge Compiler import", False, str(e))

    # 2. API keys
    for key_name in ["OPENROUTER_API_KEY", "DEEPSEEK_API_KEY"]:
        key = os.getenv(key_name)
        if key:
            check(f"API key: {key_name}", True, f"present (len={len(key)})")
        else:
            check(f"API key: {key_name}", False, "not set")

    # 3. Schema validity
    schema_dir = Path(__file__).parent
    for schema_file in ["input.schema.json", "result.schema.json"]:
        path = schema_dir / schema_file
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
                check(f"Schema: {schema_file}", True)
            except json.JSONDecodeError as e:
                check(f"Schema: {schema_file}", False, str(e))
        else:
            check(f"Schema: {schema_file}", False, "file not found")

    # 4. Core module imports
    modules = [
        "pipeline.agent_pipeline",
        "calibration_agent.m3_correction",
        "calibration_agent.m4_validation",
        "evidence.retriever",
        "config",
        "schema",
    ]
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
            check(f"Module: {mod_name}", True)
        except ImportError as e:
            check(f"Module: {mod_name}", False, str(e))

    # 5. Runner modules
    runner_modules = [
        "generic_correction",
    ]
    for mod_name in runner_modules:
        try:
            importlib.import_module(f"evaluation.v1.runner.{mod_name}")
            check(f"Runner module: {mod_name}", True)
        except ImportError as e:
            check(f"Runner module: {mod_name}", False, str(e))

    # 6. Case files
    cases_dir = REPO_ROOT / "evaluation" / "v1" / "cases"
    json_files = list(cases_dir.rglob("*.json"))
    if json_files:
        valid = 0
        for f in json_files:
            try:
                json.loads(f.read_text(encoding="utf-8"))
                valid += 1
            except json.JSONDecodeError:
                pass
        check(f"Case files: {len(json_files)} found, {valid} valid JSON", valid > 0, f"{valid}/{len(json_files)}")
    else:
        check("Case files", True, "0 found (empty directory is valid for preflight)")

    print("=" * 60)
    failed = sum(1 for c in CHECKS if not c["passed"])
    print(f"Result: {len(CHECKS) - failed}/{len(CHECKS)} passed")
    if failed:
        print(f"WARNING: {failed} check(s) failed — environment may not be fully ready.")
        return 1
    print("Environment validation PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
