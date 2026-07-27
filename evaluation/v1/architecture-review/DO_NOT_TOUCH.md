# Do Not Touch

These files and modules must remain **unchanged** during Evaluation v1 implementation. They represent working, tested, or paper-facing code that the evaluation must call as-is.

## 1. `calibration_agent/m1_detection.py` — Frozen

**Reason:** Rule-based, 9 tests pass, no bugs known. The paper (`paper.tex`) references the M1 decision logic. Changing it would invalidate paper claims.

**Risk if changed:** Paper text + reported metrics out of sync. M2 depends on M1's `needs_calibration()` signature.

## 2. `calibration_agent/m2_diagnosis.py` — Frozen

**Reason:** Rule-based, 16 tests pass, mapping from UCS to failure type is stable. Paper references the three failure types.

**Risk if changed:** Failure type names must match paper (`template_dominance`, `cue_leakage`, `context_mismatch`). The baseline comparison `baseline_comparison.py` calls `diagnose()` directly.

## 3. `calibration_agent/m4_validation.py` — Frozen

**Reason:** 9 tests pass. Its 4 checks (length, assertion, empty, copy) are the production safety net. Evaluation v1 will add **additional** checks in `evaluation/v1/validation.py`, not modify these.

**Risk if changed:** Production M3 corrections could pass validation when they shouldn't (or vice versa).

## 4. `schema.py` — Frozen

**Reason:** The `CalibrateResult` TypedDict is consumed by CLI, MCP server, audit logger, and the webpage demo. Adding new fields risks breaking downstream consumers that iterate dict keys.

**Exception:** Adding new TypedDicts in `evaluation/v1/schemas.py` is fine — these extend, not modify.

## 5. `config.py` — Frozen

**Reason:** Three environments (DEV/PROD/TEST) are used across the system. Settings include hardcoded absolute paths (`kc_path`, `fitcalib_path`) that would break if changed.

## 6. `cli.py` — Frozen

**Reason:** The paper demo script. Argument parsing interface must remain stable.

## 7. `server/mcp_server.py` — Frozen

**Reason:** The MCP tool interface (`retrieve`, `calibrate`, `health`) is consumed by the webpage demo. Any schema change would break the demo.

## 8. `paper.tex` and `references.bib` — Frozen

**Reason:** The CSCW 2027 submission. Any change to pipeline behavior must be reconciled with paper text.

## 9. `baseline_comparison.py` and `baseline_comparison.json` — Frozen

**Reason:** These contain the quantitative claims used in the paper (+0.75 UCS for Overconfident). Results have been recorded.

## 10. `evidence/base.py` (ABC) — Frozen

**Reason:** The `RetrievalBackend` interface defines the contract. Changing it would affect all backends.

## 11. The Knowledge Compiler at `C:\Users\gbx12\projects\acsms12-manifest` — Frozen

**Reason:** The Skill API (`get()`, `resolve()`, `registry`) is consumed by the evidence retriever. The 695 registry entries and 707 indexed objects are the ground-truth knowledge base.

## 12. `FitCalib-Bench/evaluation/ucs_engine.py` — Frozen

**Reason:** The UCS score (0-3) is the primary evaluation metric. The pipeline depends on `evaluate_ucs()` signature. Any change would cascade through M1 (thresholds), M2 (diagnosis rules), and paper claims.

## What You Can Freely Modify

| Allowed | Files |
|---------|-------|
| **New files under `evaluation/v1/`** | Everything in `architecture-review/`, `cases/`, `schemas.py`, `runner.py`, `baseline_correction.py`, `validation.py` |
| **Audit JSONL** | `audit/trails.jsonl` — append-only write |
| **Temporary debugging** | `json_test_output.txt` |
