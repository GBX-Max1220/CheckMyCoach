# Risk Register

## R1 — KC Keyword Retrieval Precision

| Property | Value |
|----------|-------|
| **Risk** | Keyword matching on 695 registry entries may return 0 or irrelevant results for many of the 40 evaluation cases |
| **Evidence** | `evidence/retriever.py` L42-74: simple `any(kw in name or kw in oid for kw in keywords)` matching |
| **Likelihood** | Medium — "protein intake" returned 5 plausible results; "blood pressure medication" may return fewer |
| **Impact** | If retrieval returns 0 results, the pipeline silently degrades to empty evidence — correction M3 may produce worse output |
| **Mitigation** | For each case, pre-verify retrieval works. If KC returns <2 results, add question keywords as case-level `retrieval_hints` |
| **Fallback** | `correct()` already falls back to prefix prepend when LLM fails. Same fallback acts here — empty evidence → LLM generates without evidence → correction still runs |

## R2 — M3 Correction Quality Without API Key

| Property | Value |
|----------|-------|
| **Risk** | Running without a valid OpenRouter API key means M3 correction uses fallback prefix mode (`"[Correction: remove false precision] The above values are for reference only..."`), which will be easily detectable as a "generic correction" rather than an LLM-generated rewrite |
| **Evidence** | `m3_correction.py` L106-128: `_call_llm()` catches `CorrectionError`, returns None → fallback prefix. The `.env` file contains only `OPENROUTER_API_KEY=...` (confirmed) |
| **Likelihood** | High — if the OpenRouter key is expired or has no credits, all 40 cases get prefix fallback |
| **Impact** | The "CheckMyCoach full pipeline" condition becomes indistinguishable from the "generic correction baseline" for naive readers. Evaluation loses its primary experimental condition |
| **Mitigation** | Test with a single case before full 40-run. Verify M3 `source` field is `"llm"` not `"fallback"`. Budget for GPT-4o-mini: ~$0.001/case × 40 cases = ~$0.04 total |

## R3 — Three Failure Families vs Three M2 Failure Types Are Not 1:1

| Property | Value |
|----------|-------|
| **Risk** | The Evaluation v1 failure families (`unsupported_numerical_specificity`, `unsupported_factual_claim`, `missing_safety_boundary`) do not cleanly map to M2's three diagnosis types (`cue_leakage`, `template_dominance`, `context_mismatch`) |
| **Evidence** | `EVALUATION_INTERFACE_SPEC.md` mapping table shows approximate correspondence but the mapping is heuristic, not guaranteed |
| **Likelihood** | Medium — an "unsupported_factual_claim" case might be diagnosed as `cue_leakage` if the model also outputs a number, or `context_mismatch` if contradictory features appear |
| **Impact** | M2 diagnosis failure type != expected evaluation family → correction strategy is wrong → CMC condition uses wrong prompt template |
| **Mitigation** | Accept this as part of the evaluation design. The actual M2 diagnosis IS part of the evaluation data. The question is whether the system diagnoses correctly, not whether it matches the annotation. Report confusion matrices. |

## R4 — Evaluation Case Input Answers May Not Trigger the Intended Failure

| Property | Value |
|----------|-------|
| **Risk** | The LLM-generated `input_answer` for a NUM-family question might come out Calibrated (UCS=3), meaning the pipeline correctly passes it through unchanged — but the evaluation expects a correction |
| **Evidence** | `benchmark.py` 50-question run showed 0 Overconfident outputs — the LLM may default to hedging/calibrated style |
| **Likelihood** | Medium-High — DeepSeek Chat appears conservative in fitness advice, producing mostly UCS=2-3 outputs |
| **Impact** | Cases that don't trigger M1 → no correction → missing CMC condition data point |
| **Mitigation** | Draft questions to be under-specified/impossible (e.g., "What is the optimal creatine dosage for a 175lb Asian male soccer player?"). Use the question_type field from the reliability-benchmark schema (`well-specified`, `under-specified`, `impossible`). For cases where the LLM still produces a calibrated answer, accept it as a "pass" case (the system correctly said no correction needed) |

## R5 — No Human Annotation Ground Truth

| Property | Value |
|----------|-------|
| **Risk** | Evaluation v1 specifies "Do not use an unstructured LLM-as-judge for the primary labels" — but without human annotation, there is no ground truth for whether the corrected answer actually fixed the failure |
| **Evidence** | `ucs_engine.py` uses an LLM for Stage 4 (judge fallback). The primary path (Stages 1-3) is deterministic, but "does the corrected answer retain supported info" requires semantic judgment |
| **Likelihood** | Certain — this is an architectural constraint, not a bug |
| **Impact** | The 4 validation checks in PATCH-3 will be heuristic regex-based (e.g., count numbers remaining, detect superiority patterns). They are proxies, not ground truth |
| **Mitigation** | Frame the 4 validation checks as "automated proxy metrics" not "ground truth". The evaluation report must explicitly state these are heuristic. If annotation budget exists later, add human verification |

## R6 — Hardcoded Paths

| Property | Value |
|----------|-------|
| **Risk** | Multiple `sys.path.insert(0, r"C:\Users\gbx12\projects\...")` hardcoded absolute paths in `agent_pipeline.py` (L32, L39, L46, L53, L60) |
| **Evidence** | `agent_pipeline.py` lines 32, 39, 46, 53, 60 — all hardcoded to `C:\Users\gbx12\projects\...` |
| **Likelihood** | High — breaks on any other machine. Breaks if the project is relocated |
| **Impact** | Evaluation runner won't work on a different machine without editing source code |
| **Mitigation** | Accept for v1 (same machine). For v2, move paths to environment variables or a config file. Document the dependency |

## R7 — Retriever Only Loads ACSM12, Not NSCA

| Property | Value |
|----------|-------|
| **Risk** | `evidence/retriever.py` L33 defaults to `book_path = "books/acsm12"`. The NSCA textbook (1,598 objects) is not loaded. Some evaluation cases may need strength-training domain knowledge that only exists in NSCA |
| **Evidence** | ACSM12 registry: 695 entries, 707 objects. NSCA is available at `C:\Users\gbx12\projects\acsms12-manifest/books/nsca-cscs/` |
| **Impact** | Low — ACSM12 covers exercise prescription, testing, and health conditions which spans most of the 40 cases |
| **Mitigation** | If a case needs strength-specific knowledge, pass evidence manually as `context` parameter to `calibrate()` |
