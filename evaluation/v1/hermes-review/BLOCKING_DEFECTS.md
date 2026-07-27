# Blocking Defects — CheckMyCoach Evaluation v1

**Auditor:** Hermes Agent 4 (independent red-team)
**Date:** 2026-07-27

---

## Scientific Defects (BLOCKING — invalidate condition comparison)

### SD-1: Generic correction uses wrong prompt

**Severity:** HIGH — blocks all claims about generic vs CMC comparison.

**Evidence:** `generic_correction.py` defines:
- `GENERIC_SYSTEM_PROMPT = "You are a professional writing assistant. Improve the following text to be more clear, accurate, and useful. Do not fabricate data or citations. Output ONLY the improved text."`
- `GENERIC_USER_PROMPT = "Please improve the following text:\n\n{original_text}\n\nImproved text:"`

Protocol requires (`GENERIC_BASELINE_PROMPT.txt`):
`"Revise the answer to be accurate, appropriately cautious, evidence-based and concise. Preserve useful supported information and avoid adding unsupported claims."`

**Impact:** The implementation prompt is weaker and doesn't ask to preserve supported content or avoid new claims. The generic condition is systematically disadvantaged.

**Fix:** Use the exact frozen prompt from `GENERIC_BASELINE_PROMPT.txt`.

---

### SD-2: Generic correction receives no question or evidence

**Severity:** HIGH — directly violates protocol.

**Evidence:** `generic_correction.py:correct(original_text)` receives only the original text. No question. No evidence payload. Protocol says: "provide only the question, original answer, eligible evidence payload, and the exact frozen prompt."

**Impact:** The generic correction is asked to improve text without knowing what question was asked or what evidence exists. This prevents the generic condition from making evidence-anchored corrections, making the comparison manifestly unfair.

**Fix:** Pass `question`, `original_answer`, and `evidence_payload` to the generic correction function alongside the prompt.

---

### SD-3: Generic correction is LLM-based, not rule-based

**Severity:** MEDIUM — confounds the signal.

**Evidence:** `generic_correction.py` calls OpenRouter GPT-4o-mini.

**Impact:** The "generic" condition is itself an LLM system. Any observed difference between generic and CMC conflates prompt specialization, model choice, and context provided. A deterministic rule-based baseline (as MINIMUM_PATCH_PLAN proposed) would provide a clean lower bound.

**Fix:** Either implement a deterministic rule-based baseline OR clearly document that the comparison is "pipeline-with-M3 vs pipeline-with-generic-LLM" and adjust claims accordingly.

---

### SD-4: All three conditions share the same pipeline — can't isolate contributions

**Severity:** MEDIUM — reduces what the evaluation can claim.

**Evidence:** All three conditions call `calibrate_full()` (retrieve + LLM generate). The only difference is the post-hoc correction step.

**Impact:** The "original" condition is not a raw LLM output — it's a pipeline output with evidence retrieval and LLM generation. This conflates pipeline quality with correction quality. A "raw LLM" condition (no retrieval, no pipeline) is needed to isolate the evidence-retrieval contribution from the correction contribution.

**Fix:** Add a "raw LLM" condition that calls the LLM directly without pipeline evidence retrieval or UCS scoring.

---

## Implementation Defects (BLOCKING — runner produces wrong outputs)

### ID-1: `run_checkmycoach` calls `calibrate_full()` instead of `calibrate()`

**Severity:** CRITICAL — the CMC condition never runs the CMC pipeline.

**Evidence:** `run_single_case.py` `run_checkmycoach()` imports and calls `calibrate_full()` from `pipeline.agent_pipeline`. The architecture review confirms `calibrate_full()` only does retrieval + LLM generation, while `calibrate()` includes M1 detection, M2 diagnosis, M3 correction, and M4 validation.

**Impact:** All three conditions produce identical uncorrected outputs. The entire evaluation collapses to a single condition with and without a generic LLM rewrite on top. No CMC capability is tested.

**Fix:** Change `run_checkmycoach` to call `calibrate()` (from `pipeline.agent_pipeline`) instead of `calibrate_full()`.

---

### ID-2: `discover_cases()` uses wrong field name

**Severity:** HIGH — batch runner finds 0 production cases.

**Evidence:** `run_evaluation.py` `discover_cases()` checks for `"question"` in case dicts. `CASE_SCHEMA.json` defines `"input_question"`.

**Impact:** No production case stored in `cases/` is discovered by the batch runner.

**Fix:** Change `discover_cases()` to check for `"input_question"` (the canonical field name), or support both.

---

### ID-3: Generic correction prompt is hardcoded, not read from file

**Severity:** MEDIUM — compounds SD-1.

**Evidence:** `generic_correction.py` hardcodes `GENERIC_SYSTEM_PROMPT` and `GENERIC_USER_PROMPT`. The protocol file `GENERIC_BASELINE_PROMPT.txt` is generated but never read by the runner.

**Impact:** Even after fixing SD-1, the prompt would need to be loaded from the protocol file. Currently the runner has no mechanism to ingest the protocol prompt.

**Fix:** Read `GENERIC_BASELINE_PROMPT.txt` in `generic_correction.py`.

---

### ID-4: `run_generic` doesn't UCS-score the corrected output

**Severity:** MEDIUM — can't measure generic correction quality.

**Evidence:** `run_generic()` returns:
- `ucs_score`: the ORIGINAL pipeline UCS score (pre-correction)
- No post-correction UCS score

The generic condition corrects the text but doesn't re-evaluate it. There's no way to tell whether the generic correction improved the output.

**Fix:** Call UCS scoring on the corrected generic output and record both pre- and post-correction UCS scores.

---

## Minor Defects (not blocking but should be fixed)

### MN-1: `retry_count` schema field is never populated

**Evidence:** `result.schema.json` defines `retry_count: {"type": "integer", "minimum": 0}` but no runner code sets it.

**Fix:** Initialize `retry_count: 0` in all result records, or remove from schema.

### MN-2: No seed/temperature logging

**Evidence:** The runner doesn't log random seed or generation temperature for API calls.

**Fix:** Log `temperature`, `seed` (if supported by model), and `model` in each result record.

### MN-3: No preflight hook in batch runner

**Evidence:** `EXECUTION_STATE_MACHINE.md` defines PREFLIGHT → RUNNING → COMPLETED. The batch runner skips directly to RUNNING.

**Fix:** Call `validate_environment.py` checks at the start of `run_batch()`.

---

## Defect Classification

| ID | Type | Severity | Fix Time | Blocks Gate? |
|----|------|----------|----------|:------------:|
| SD-1 | Scientific | HIGH | < 1 hour | YES |
| SD-2 | Scientific | HIGH | < 1 hour | YES |
| SD-3 | Scientific | MEDIUM | < 2 hours | YES |
| SD-4 | Design | MEDIUM | < 2 hours | RECOMMENDED |
| ID-1 | Implementation | CRITICAL | < 30 min | YES |
| ID-2 | Implementation | HIGH | < 15 min | YES |
| ID-3 | Implementation | MEDIUM | < 15 min | YES |
| ID-4 | Implementation | MEDIUM | < 30 min | YES |
| MN-1 | Minor | LOW | < 5 min | NO |
| MN-2 | Minor | LOW | < 10 min | NO |
| MN-3 | Minor | LOW | < 15 min | NO |

**Total blocking defects: 8** (4 scientific + 4 implementation)
