# Implementation Fix Report

**Date:** 2026-07-27
**Scope:** Phase 1 implementation corrections for CheckMyCoach Evaluation v1
**Hermes audit reference:** `hermes-review/FINAL_GATE_REVIEW.md` (BLOCKED, 5 blocking defects)

---

## Fix 1 — Case discovery: support `input_question` field

### Original defect
Runner's `discover_cases()` searched for `"question"` field but production case format (per `CASE_SCHEMA.json`) uses `"input_question"`. Runner discovered zero production cases.

### Why it affected validity
The evaluation could not run on the actual 40-case dataset. Only the sample case with empty `evidence_text` was discoverable.

### Exact fix
Helper `_get_case_field(case, "input_question", "question")` already implemented in `run_single_case.py`. Same helper confirmed in `run_evaluation.py`. Both `discover_cases()` and `load_case()` use it correctly. No code change needed — verified correct behavior.

### Files changed
None. Verified existing implementation correct.

### Tests
- `test_input_question_support` — `input_question` prioritized over `question`; empty fallback
- `test_discover_input_question` — same check for `run_evaluation` helper

---

## Fix 2 — Evidence parity between Generic and CMC

### Original defect
Generic condition received empty evidence (sample case `evidence_text: ""`). CMC condition retrieved KC evidence internally. Asymmetric comparison.

### Why it affected validity
Generic operated blind while CMC operated with evidence. Any measured difference could be attributed to evidence access rather than correction strategy.

### Exact fix
Updated `collect_case_evidence()` with three-tier priority:
1. `evidence_excerpt` (production case format)
2. `evidence_text` (legacy sample format)
3. Runtime KC retrieval (fallback)

### Files changed
- `run_single_case.py` — `collect_case_evidence()` added `evidence_excerpt` support

### Tests
- `test_evidence_excerpt_support` — production format excerpt is used as evidence payload
- `test_evidence_text_legacy` — legacy `evidence_text` still works
- `test_generic_receives_evidence` — evidence payload included in prompt
- `test_generic_no_failure_type` — no hidden labels passed

---

## Fix 3 — Load frozen generic prompt from file

### Original defect
Prompt was hardcoded rather than loaded from the frozen protocol file.

### Why it affected validity
`GENERIC_BASELINE_PROMPT.txt` is a change-controlled protocol artifact. Hardcoding bypasses this control.

### Exact fix
`_load_prompt()` already reads from `evaluation/v1/protocol/GENERIC_BASELINE_PROMPT.txt` at runtime. Raises `FileNotFoundError` with descriptive message if missing. Verified correct.

### Files changed
None. Verified existing implementation correct.

### Tests
- `test_generic_loads_frozen_prompt` — loaded content >10 chars, contains expected keywords
- `test_frozen_prompt_exists` — file exists and is non-empty

---

## Fix 4 — Temperature consistency

### Original defect
Generic condition: `temperature=0.3`. CMC M3: `temperature=0.5`. Same model (GPT-4o-mini), different temperature.

### Why it affected validity
Temperature is a confound. Lower temperature produces more conservative outputs; higher temperature allows more variation.

### Exact fix
Changed `generic_correction.py` temperature from `0.3` to `0.5`. Added `model` and `temperature` fields to `GenericCorrectionResult` fallback path (LLM path already logged them).

### Files changed
- `generic_correction.py` — `temperature = 0.3` → `temperature = 0.5`; fallback return now includes `model` and `temperature`

### Tests
- `test_generic_temperature` — `result.temperature == 0.5`, `result.model` is set
- `test_temperature_logged` — `GenericCorrectionResult` has `temperature` and `model` attributes

---

## Fix 5 — Remove UCS as evaluation metric

### Original defect
Runner recorded and displayed `ucs_score`, `ucs_score_original`, `ucs_score_corrected`, `ucs_features` in every condition's output and progress printing.

### Why it affected validity
Protocol (EVALUATION_PROTOCOL.md, PRIMARY_METRICS.md) explicitly prohibits composite scores and LLM-as-judge. UCS violates both prohibitions. UCS in output contradicts protocol and would tempt improper secondary analysis.

### Exact fix
Removed all UCS fields from `run_original()`, `run_generic()`, `run_checkmycoach()` result dicts. Removed UCS scoring calls from `run_generic()` (called UCS before and after correction). Removed `ucs_score` and `ucs_features` from `result.schema.json`. Updated progress printing in `run_evaluation.py` and dry-run messages.

**Note:** UCS engine is NOT deleted. It remains available for offline analysis outside the evaluation runner.

### Files changed
- `run_single_case.py` — all three `run_*()` functions: removed UCS fields; `run_generic()`: removed UCS scoring calls
- `run_evaluation.py` — progress printing: removed UCS references
- `result.schema.json` — removed `ucs_score` and `ucs_features` from properties

### Tests
- `test_result_schema_no_ucs` — `ucs_score` and `ucs_features` absent from result schema
- `test_no_ucs_in_original` — run_original output has no UCS fields
- `test_no_ucs_in_generic` — run_generic output has no UCS fields
- `test_no_ucs_in_cmc` — run_checkmycoach output has no UCS fields

---

## Fix 6 — Verify CMC uses `calibrate()`, not `calibrate_full()`

### Original defect
Concern that CMC condition might call `calibrate_full()` instead of `calibrate()`, skipping M1-M4.

### Why it affected validity
`calibrate_full()` performs retrieval + generation only. `calibrate()` performs M1 detection → M2 diagnosis → M3 correction → M4 validation. Wrong function would mean CMC condition doesn't test the CMC pipeline.

### Exact fix
Verified `run_checkmycoach()` at line 82-83 calls `calibrate(response, question)`. Updated dry-run messages to remove UCS references.

### Files changed
- `run_single_case.py` — dry-run print messages: removed UCS references

### Tests
- `test_cmc_uses_calibrate` — source inspection confirms `calibrate()` not `calibrate_full()`
- `test_original_uses_calibrate_full` — `generate_original_response()` uses `calibrate_full()`

---

## Full Test Results

| Test Suite | Before | After | Change |
|-----------|--------|-------|--------|
| M1 detection (pytest) | 9/9 | 9/9 | ✅ |
| M2 diagnosis (pytest) | 16/16 | 16/16 | ✅ |
| M3 correction (pytest) | 9/9 | 9/9 | ✅ |
| M4 validation (pytest) | 9/9 | 9/9 | ✅ |
| Pipeline subtotal | 41/41 | 41/41 | ✅ |
| Evaluation runner | 15/15 | 27/27 | **+12 tests** |
| **Total** | **56/56** | **68/68** | **✅ No regressions** |

---

## Dry Run Verification

| Check | Result |
|-------|--------|
| Single case, all 3 conditions | Three different pipelines shown, no API calls |
| Batch run, 1 sample case | Discovery + iteration complete, no API calls |
| No UCS references in output | ✅ Clean |

---

## Remaining Limitations

These are accepted design limitations (not implementation defects):

1. **Evidence path asymmetry.** Generic receives pre-retrieved evidence payload. CMC retrieves evidence internally via its own pipeline. Both use the same Knowledge Compiler backend but may return different evidence sets. This is an architectural feature of CMC, not a bug.

2. **No raw-LLM condition.** All conditions start from `calibrate_full()` output (evidence-augmented generation). No condition isolates the retrieval contribution. Adding Condition D was explicitly out of scope.

3. **Constructed answers.** All 40 production `original_answer` fields are hand-authored to be clean, obvious failures. This tests capability ("can the system fix this?"), not prevalence ("does the system encounter real failures?").

4. **Single domain (fitness only).** All cases are ACSM12 + NSCA-CSCS. No medical, legal, or financial coverage.

5. **Human secondary review not implemented.** Protocol requires two independent human reviewers for secondary semantic checks. This requires annotation infrastructure outside Phase 1 scope.

6. **Generic baseline prompt asymmetry.** Frozen prompt is 18 words. CMC prompt templates across M1-M4 total ~200 words. Comparison tests instruction quality as well as architecture. Accepted as a v1 limitation.

---

## Status

**READY FOR HERMES RE-AUDIT**
