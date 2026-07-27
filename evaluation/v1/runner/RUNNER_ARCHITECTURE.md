# CheckMyCoach Evaluation Runner — Architecture

## Purpose
Deterministic batch runner for evaluating three correction conditions
on the same case set, preserving full audit trail.

## Three Conditions

### Original
- No correction applied.
- The raw LLM response is recorded as-is.
- Pipeline steps: retrieve evidence → LLM generate → UCS score.
- No M3 correction, no validation.

### Generic Correction
- The raw LLM response is sent to a **generic improvement prompt**.
- The generic prompt receives **only** the original text — no failure type,
  no diagnosis, no evidence about calibration problems.
- This isolates the effect of "any improvement attempt" from the
  effect of "failure-type-aware correction".
- Pipeline steps: retrieve evidence → LLM generate → UCS score →
  generic correction prompt → UCS score post-correction.

### CheckMyCoach
- The full pipeline runs: retrieve evidence → LLM generate → UCS score →
  M1 detection → M2 diagnosis → M3 correction → M4 validation.
- No gold labels, no hidden failure type are injected.
- M3 receives only the diagnosis output from M2 (as in production).

## Gold Label Safety
The evaluation case set must NOT contain:
- target failure span
- reference correction text
- expected metric outcome
- hidden gold labels
- forbidden-new-claim list (unless the production M3 prompt would genuinely
  have access to that information)

Gold fields belong only to offline evaluation analysis, never to the
input that any condition sees at generation time.

## File Layout
evaluation/v1/
├── cases/               # Case definitions (JSON)
│   └── sample/          # Sample cases for dry-run testing
├── runner/
│   ├── __init__.py
│   ├── RUNNER_ARCHITECTURE.md       (this file)
│   ├── EXECUTION_STATE_MACHINE.md
│   ├── PROVENANCE_SPEC.md
│   ├── input.schema.json
│   ├── result.schema.json
│   ├── generic_correction.py
│   ├── run_evaluation.py
│   ├── run_single_case.py
│   ├── validate_environment.py
│   ├── freeze_manifest.py
│   └── test_evaluation_runner.py
├── TEST_REPORT.md
├── DRY_RUN_REPORT.md
└── BLOCKERS.md

All production code lives in the repository's existing package structure
(pipeline/, calibration_agent/, evidence/, schema.py, config.py).
The runner imports those modules — it never duplicates them.
