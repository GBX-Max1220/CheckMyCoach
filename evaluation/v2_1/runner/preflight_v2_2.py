#!/usr/bin/env python3
"""
preflight_v2_2.py — Freeze integrity check for CheckMyCoach v2.2.

Verifies:
- execution_manifest_v2.2.json exists and parses
- Every file hash matches the manifest
- protocol_version == "v2.2"
- All required files exist on disk

Usage:
    python -m evaluation.v2_1.runner.preflight_v2_2

Exit codes:
    0: All checks passed
    1: One or more checks failed
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MANIFEST_PATH = REPO_ROOT / "evaluation" / "v2_1" / "execution_manifest_v2.2.json"
PROTOCOL_VERSION = "v2.2"

CHECKS: list[dict] = []


def check(name: str, passed: bool, detail: str = ""):
    CHECKS.append({"name": name, "passed": passed, "detail": detail})
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    print("=" * 60)
    print("CheckMyCoach v2.2 — Preflight Freeze Check")
    print("=" * 60)

    # 1. Manifest exists
    if not MANIFEST_PATH.exists():
        check("Manifest file exists", False, f"not found at {MANIFEST_PATH}")
        print("=" * 60)
        print(f"Result: 0/{len(CHECKS) + 1} passed — aborting.")
        return 1
    check("Manifest file exists", True)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    # 2. Protocol version matches
    actual_version = manifest.get("protocol_version", "")
    check(f"Protocol version: {actual_version}",
          actual_version == PROTOCOL_VERSION,
          f"expected {PROTOCOL_VERSION}")

    # 2b. External dependencies hash verification
    ext_path = MANIFEST_PATH.parent / "external_dependencies_v2.2.json"
    if ext_path.exists():
        ext_data = json.loads(ext_path.read_text(encoding="utf-8"))
        ext_actual = hashlib.sha256(json.dumps(ext_data, sort_keys=True).encode()).hexdigest()
        ext_expected = manifest.get("external_dependencies_hash", "")
        if ext_expected and ext_actual == ext_expected:
            check("External dependencies hash", True)
        elif not ext_expected:
            check("External dependencies hash", False, "not recorded in manifest")
        else:
            check("External dependencies hash", False, "mismatch")
    else:
        check("External dependencies file", False, "external_dependencies_v2.2.json not found")

    # 3. Hash verification for all file groups
    # Map group → base directory for file resolution
    group_bases = {
        "Protocol": REPO_ROOT / "evaluation" / "v2_1",
        "Data": REPO_ROOT / "evaluation" / "v2_1",  # cases.jsonl lives elsewhere — handled below
        "Runner": REPO_ROOT / "evaluation" / "v2_1",
        "Pipeline": REPO_ROOT,  # pipeline files are repo-root relative
        "Scoring": REPO_ROOT / "evaluation" / "v2_1",
    }

    file_groups = {
        "Protocol": manifest.get("protocol_files", {}),
        "Data": manifest.get("data_files", {}),
        "Runner": manifest.get("runner_files", {}),
        "Pipeline": manifest.get("pipeline_files", {}),
        "Scoring": manifest.get("scoring_files", {}),
    }

    for group_name, files in file_groups.items():
        base = group_bases.get(group_name, REPO_ROOT / "evaluation" / "v2_1")
        for rel_path_str, expected_hash in files.items():
            # Special case: cases.jsonl is in evaluation/v1/data/
            if rel_path_str == "data/cases.jsonl":
                full_path = REPO_ROOT / "evaluation" / "v1" / "data" / "cases.jsonl"
            else:
                full_path = base / rel_path_str
            if not full_path.exists():
                check(f"{group_name}: {rel_path_str}", False, "file not found")
                continue
            actual_hash = sha256(full_path)
            match = actual_hash == expected_hash
            if not match:
                check(f"{group_name}: {rel_path_str}", False,
                      f"hash mismatch: expected {expected_hash[:16]}..., got {actual_hash[:16]}...")
            else:
                check(f"{group_name}: {rel_path_str}", True)

    # 4. Combined hash (mandatory — fail closed if empty or mismatch)
    # Include external dependencies in combined hash
    ext_combined = json.dumps(ext_data, sort_keys=True) if ext_path.exists() else ""

    combined_input = json.dumps(manifest.get("protocol_files", {}), sort_keys=True) + \
                     json.dumps(manifest.get("data_files", {}), sort_keys=True) + \
                     json.dumps(manifest.get("runner_files", {}), sort_keys=True) + \
                     json.dumps(manifest.get("pipeline_files", {}), sort_keys=True) + \
                     json.dumps(manifest.get("scoring_files", {}), sort_keys=True) + \
                     ext_combined
    combined_hash = hashlib.sha256(combined_input.encode()).hexdigest()
    stored_combined = manifest.get("combined_sha256", "")
    if not stored_combined:
        check("Combined SHA-256", False, "empty — must be populated")
    elif stored_combined != combined_hash:
        check("Combined SHA-256", False, f"mismatch: expected {combined_hash[:16]}...")
    else:
        check("Combined SHA-256", True)

    # 5. Required runtime files
    runtime_checks = [
        ("Blinded cases", REPO_ROOT / "evaluation" / "v2_1" / "data" / "blinded_cases_v2.2.jsonl"),
        ("Oracle diagnoses", REPO_ROOT / "evaluation" / "v2_1" / "data" / "oracle_diagnosis_v2.2.jsonl"),
        ("Gold cases", REPO_ROOT / "evaluation" / "v1" / "data" / "cases.jsonl"),
        ("Generic prompt", REPO_ROOT / "evaluation" / "v2_1" / "protocol" / "GENERIC_BASELINE_PROMPT.txt"),
        ("Run evaluation", REPO_ROOT / "evaluation" / "v2_1" / "runner" / "run_evaluation.py"),
        ("Run single case", REPO_ROOT / "evaluation" / "v2_1" / "runner" / "run_single_case.py"),
        ("Scorer", REPO_ROOT / "evaluation" / "v2_1" / "scoring" / "scorer.py"),
    ]
    for label, path in runtime_checks:
        check(f"Required file: {label}", path.exists())

    print("=" * 60)
    failed = sum(1 for c in CHECKS if not c["passed"])
    print(f"Result: {len(CHECKS) - failed}/{len(CHECKS)} passed ({failed} failed)")
    if failed:
        print("FROZEN EXECUTION BLOCKED — fix mismatches before running.")
        return 1
    print("All checks passed. v2.2 execution package is intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
