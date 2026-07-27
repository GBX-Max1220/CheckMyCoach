# Pre-Execution Checklist — CheckMyCoach Evaluation v1

Verify each item before authorizing any API execution. All items must be PASS.

---

## A. Hermes Audit Conditions

- [ ] **Hermes FINAL_GATE_REVIEW.md** confirms GO WITH LIMITATIONS
- [ ] All 8 blocking defects (BLOCKING_DEFECTS.md) addressed
- [ ] 4 scientific defects (SD-1 through SD-4) dispositioned
- [ ] 4 implementation defects (ID-1 through ID-4) fixed
- [ ] SD-1 (generic prompt): loaded from GENERIC_BASELINE_PROMPT.txt ✅
- [ ] SD-2 (generic evidence): receives question + answer + evidence ✅
- [ ] SD-3 (LLM baseline): accepted as design limitation ✅
- [ ] SD-4 (pipeline sharing): accepted as design limitation ✅
- [ ] ID-1 (CMC uses calibrate): verified `run_checkmycoach` calls `calibrate()` ✅
- [ ] ID-2 (field name): `_get_case_field` supports `input_question` + `question` ✅
- [ ] ID-3 (prompt file): `_load_prompt()` reads from protocol file ✅
- [ ] ID-4 (UCS removed): protocol prohibits composite scores ✅
- [ ] No gold leakage confirmed (LEAKAGE_AUDIT.md) ✅
- [ ] No LLM-as-judge in evaluation output (UCS removed from result schema) ✅
- [ ] No composite headline score defined (PRIMARY_METRICS.md) ✅

## B. Model Identity

- [ ] Original generation model frozen: `deepseek-chat` at temperature 0.3
- [ ] Generic correction model frozen: `openai/gpt-4o-mini` at temperature 0.5
- [ ] CMC M3 correction model frozen: `openai/gpt-4o-mini` at temperature 0.5
- [ ] Generic and CMC M3 use identical model and temperature
- [ ] Model config recorded in `execution/model_config.json`

## C. Generic Baseline

- [ ] Frozen prompt loaded from `protocol/GENERIC_BASELINE_PROMPT.txt`
- [ ] Prompt is at least 10 characters and contains relevant keywords
- [ ] Generic condition receives `question`, `original_answer`, `evidence_payload`
- [ ] Generic condition does NOT receive `failure_type`, `target_span`, `reference_correction`, gold labels

## D. CMC Pipeline

- [ ] `run_checkmycoach()` calls `calibrate(response, question)` — confirmed by source inspection
- [ ] `run_checkmycoach()` does NOT call `calibrate_full()`
- [ ] Dry-run shows three distinct pipeline descriptions
- [ ] M1-M4 are structually reachable through `calibrate()`

## E. Output Schema

- [ ] `result.schema.json` validated: no UCS fields present
- [ ] `result.schema.json`: all three conditions defined
- [ ] `result.schema.json`: provenance properties present
- [ ] `input.schema.json`: no gold fields

## F. Code Integrity

- [ ] 68/68 tests pass (27 runner + 41 pipeline)
- [ ] Dry-run completes with no API calls
- [ ] No uncommitted changes to protocol files
- [ ] `execution/execution_manifest.json` hashes match current filesystem

## G. Execution Readiness

- [ ] `.env` file contains valid OPENROUTER_API_KEY
- [ ] `.env` file contains valid DEEPSEEK_API_KEY (if using original generation)
- [ ] API keys have sufficient quota for 40 cases × 3 conditions × ~$0.001 per call ≈ $0.12 total estimate
- [ ] One-case smoke run authorized per Hermes scope

---

## Sign-off

| Role | Name | Date |
|------|------|------|
| Engineering | | |
| Scientific Audit (Hermes) | | |
| Final Gate | | |

**Status after all checks pass: READY FOR SMOKE RUN**
