# Changelog — Hermes Red-Team Defect Fixes

## Fix 1 — CheckMyCoach condition must call calibrate() not calibrate_full()

**Defect ID:** HERMES-P0-01
**Files changed:** `evaluation/v1/runner/run_single_case.py`

**Old behavior:**
`run_checkmycoach()` called `calibrate_full(question)` which generates a new LLM response internally, then runs M1-M4 on that response. Each call to `run_checkmycoach` generates a different original response.

**New behavior:**
The original response is generated ONCE via `generate_original_response()` (wraps `calibrate_full`). This same response is shared across all three conditions. `run_checkmycoach()` calls `calibrate(response=original_response, question=question)` which runs the actual pipeline (M1→M2→M3→M4) on the pre-generated response.

**Verification:**
- Dry run output: `checkmycoach pipeline = original_response -> calibrate(response,question) -> M1 -> M2 -> M3 -> M4 -> UCS`
- Trace contains: `failure_type`, `m2_confidence`, `corrected_response`, `m4_passed`, `needs_calibration`

---

## Fix 2 — Generic correction must receive question+evidence

**Defect ID:** HERMES-P0-02
**Files changed:** `evaluation/v1/runner/generic_correction.py`

**Old behavior:**
`correct(original_text: str)` — only received the answer text. No question or evidence context.

**New behavior:**
`correct(question: str, original_answer: str, evidence_payload: list)` — receives the question, original answer, and retrieved evidence. Represents "evidence-based revision" not "blind rewriting".

**FORBIDDEN inputs explicitly excluded:**
- `failure_type` — not in function signature
- `target_failure_span` — not received  
- `reference_correction` — not received
- `gold labels` — not received

**Verification:**
- Test `test_generic_new_interface` PASS: params = question, original_answer, evidence_payload
- Test `test_generic_prompt_content` PASS: prompt contains question, answer, and evidence source

---

## Fix 3 — Load exact frozen generic prompt from file

**Defect ID:** HERMES-P0-03
**Files changed:** `evaluation/v1/runner/generic_correction.py`

**Old behavior:**
Hardcoded `GENERIC_SYSTEM_PROMPT` and `GENERIC_USER_PROMPT` strings embedded in the Python source.

**New behavior:**
`_load_prompt()` reads the exact `GENERIC_BASELINE_PROMPT.txt` file from `evaluation/v1/protocol/` at runtime. If the file is missing, raises `FileNotFoundError` — the runner will not proceed with a stale or missing prompt.

**Frozen prompt content (161 bytes):**
```
Revise the answer to be accurate, appropriately cautious, evidence-based and concise. Preserve useful supported information and avoid adding unsupported claims.
```

**Verification:**
- Test `test_generic_loads_frozen_prompt` PASS: loads from file, contains expected keywords
- Test `test_frozen_prompt_exists` PASS: prompt file exists at expected path

---

## Fix 4 — Generic condition needs post-correction UCS evaluation

**Defect ID:** HERMES-P0-04
**Files changed:** `evaluation/v1/runner/run_single_case.py`

**Old behavior:**
Generic condition only recorded `ucs_score` (the original response's UCS). No evaluation of the corrected text.

**New behavior:**
Generic condition now records:
- `ucs_score_original`: UCS of the original response (before correction)
- `ucs_score`: (kept for backward compat) same as original
- `ucs_score_corrected`: UCS of the generically corrected response (after correction)

Both evaluations use the same `evaluate_ucs()` from the frozen pipeline.

**Verification:**
- Dry run: `generic pipeline = generic_correct(question+answer+evidence) -> UCS(before+after)`
- Result record schema includes both `ucs_score_original` and `ucs_score_corrected`

---

## Fix 5 — Case discovery must support `input_question`

**Defect ID:** HERMES-P0-05
**Files changed:** `evaluation/v1/runner/run_single_case.py`, `evaluation/v1/runner/run_evaluation.py`

**Old behavior:**
`discover_cases()` checked for `"question" in case`. `run_single_case.py` used `case["question"]`.

**New behavior:**
Both files use `_get_case_field(case, "input_question", "question")` helper that tries multiple key names in order. `discover_cases()` also supports both field names.

**Verification:**
- Test `test_input_question_support` PASS: prefers `input_question` over `question`
- Test `test_discover_input_question` PASS: both field names work in discovery

---

## P1 Fix — Logging fields and preflight integration

**Defect ID:** HERMES-P1-01
**Files changed:** `evaluation/v1/runner/run_single_case.py`, `evaluation/v1/runner/run_evaluation.py`

**Old behavior:**
Records included only: `model`, `timestamp`, `latency_ms`, `token_usage`. No temperature, seed, or retry_count. Batch runner had no preflight.

**New behavior:**
Every result record now includes:
- `model`: model identifier string
- `temperature`: LLM temperature
- `seed`: seed value (if available, else None)
- `retry_count`: always 0 (no retry implemented yet)
- `latency_ms`: total latency
- `token_usage`: prompt/completion tokens where available
- `ucs_score_original`: before correction
- `ucs_score_corrected`: after correction (generic only)

Batch runner executes `validate_environment.py` before running (can be skipped with `--skip-preflight`).

**State machine:**
```
PREFLIGHT -> RUNNING -> COMPLETED (0 errors) / STOPPED (errors > 0)
```
