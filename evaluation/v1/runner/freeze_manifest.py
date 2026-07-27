#!/usr/bin/env python3
"""
freeze_manifest.py — Compute SHA-256 hashes for all evaluation runner files.

Outputs a JSON manifest that can be used to verify file integrity
before each evaluation run.

Usage:
    python -m evaluation.v1.runner.freeze_manifest
"""

import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    runner_dir = Path(__file__).parent.resolve()
    repo_root = runner_dir.parent.parent.parent

    files = sorted(runner_dir.rglob("*"))
    files = [f for f in files if f.is_file() and f.name != "freeze_manifest.py"]

    manifest = {
        "manifest_version": "1",
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "files": {},
    }

    for f in files:
        relative = f.relative_to(repo_root)
        manifest["files"][str(relative)] = sha256(f)

    manifest_path = runner_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest written: {manifest_path}")
    print(f"Files hashed: {len(manifest['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
