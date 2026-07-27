# CheckMyCoach Evaluation v2.2 — Protocol

**Version:** 2.2.0
**Date:** 2026-07-28
**Design authority:** PI (post v2.2 audit + CodeX causal audit)
**Status:** FROZEN — no changes without version bump

---

## 1. Research Questions

**RQ1 (primary):** Does providing explicit failure-type diagnosis to a generic revision prompt improve correction quality over diagnosis-blind generic revision?

**RQ2 (secondary):** Does CMC's type-aware template-based correction improve correction quality over generic revision with equivalent oracle diagnosis?

**RQ3 (exploratory):** How does correction effectiveness vary across the three failure families (unsupported numerical specificity, unsupported factual claim, missing boundary)?

---

## 2. Hypotheses

- **H1:** Generic+Diagnosis > Generic on targeted failure removal (diagnosis information enables more precise correction).

- **H2:** CMC ≥ Generic+Diagnosis on targeted failure removal (type-aware template correction preserves or improves upon diagnosis-informed generic correction).

- **H3 (null):** Generic+Diagnosis ≈ Generic across all primary metrics (diagnosis information alone does not improve a generic correction prompt).

- **H4 (exploratory):** The diagnosis advantage (Generic+Diagnosis − Generic) is larger for missing_boundary cases than for unsupported factual claims, because boundary insertion requires knowing which boundary to add.

- **H5 (monitoring):** All correction conditions > Original on failure removal (any intervention reduces failures compared to uncorrected baseline).

---

## 3. Variables

### 3.1 Independent Variable

**Condition** (4 levels, within-case):

| Level | Label | Correction applied | Has diagnosis info? | Evidence source | Model | max_tokens |
|-------|-------|-------------------|---------------------|-----------------|-------|------------|
| Original | `original` | None (uncorrected baseline) | N/A | N/A | N/A | N/A |
| Generic | `generic` | Single-pass LLM revision | No | Case evidence_excerpt | gpt-4o-mini | 1024 |
| Generic+Diagnosis | `generic_with_diagnosis` | Single-pass LLM revision | **Yes** — oracle failure family, target span, statement, required change, required boundary | Case evidence_excerpt | gpt-4o-mini | 1024 |
| CheckMyCoach | `checkmycoach` | CMC pipeline: UCS → M1 → M2 → M3 → M4 | Pipeline uses its own UCS/M1/M2 detection (not oracle) | Case evidence_excerpt (fed as pre-retrieved) | gpt-4o-mini (M3) / deepseek-chat (UCS/M1/M2) | 1024 (M3) |

### 3.2 Dependent Variables

| Metric | Unit / Denominator | Operationalization | Tier |
|--------|-------------------|-------------------|------|
| **Targeted failure removal** | case; all attempted cases | All target-removal primary checks pass | Primary deterministic |
| **Supported info retention** | retention atom; all specified atoms | Regex/alias atom retained; semantic paraphrase reported separately | Primary deterministic + secondary human |
| **New unsupported claim rate** | new output proposition; all output propositions | Two independent humans apply closed-evidence rule; report claims and cases with ≥1 | Secondary human (no LLM) |
| **Boundary preservation** | applicable case; 10 Group-C cases | All required-boundary primary checks pass | Primary deterministic |
| **Evidence-link accuracy** | case; all cases with correction | Returned knowledge object IDs are from the case-linked set | Primary deterministic |
| **Correction minimality** | case; all parseable corrections | Normalized token Levenshtein distance / max(original tokens, 1) | Descriptive deterministic |
| **Pipeline completion** | case; all 40 per condition | All stages complete without technical failure | Primary deterministic |
| **Parse/schema success** | case; all outputs | Output conforms to frozen run schema | Primary deterministic |

### 3.3 Controlled Variables

| Variable | Value | Rationale |
|----------|-------|-----------|
| `evidence_excerpt` | Same frozen excerpt for all three correction conditions | Remove evidence confound that invalidated v1 |
| Correction model | `openai/gpt-4o-mini` across Generic, Generic+Diagnosis, and CMC M3 | Isolate correction strategy from model capability |
| Temperature | **0.3** for all LLM correction calls (Generic, Generic+Diagnosis, CMC M3) | Equalized across all correction conditions per CodeX causal audit |
| max_tokens | **1024** for all correction conditions | Equalized — CMC M3 raised from v1's 300 |
| Original answer | Pre-provided, same across all conditions | No LLM regeneration of original answer |
| Case order | Deterministically randomized per case via `get_randomized_conditions(case_id)`. seed_material = case_id + '_v2.2'. Realized execution_order recorded in ledger. | Prevents systematic order confounds across conditions |
| API provider | OpenRouter for all correction models | Environmental consistency |
| Seed policy | `not_specified` (OpenRouter does not support seeds) | Documented limitation |

### 3.4 Blocked Variables (not controlled)

| Variable | Status | Impact |
|----------|--------|--------|
| CMC pipeline internal models (UCS, M1, M2) | Different from correction model (deepseek-chat) | RQ2 interpretation: CMC vs Generic+Diagnosis contrasts pipeline (detection+correction) against oracle-informed generic correction |
| CMC M4 validation logic | Internal to pipeline, not bypassed for this experiment | M4 output is recorded but not used as evaluation metric |
| Pipeline non-determinism | UCS Engine's LLM stage has stochastic branching | score_delta annotated as noisy; not used as primary metric |

### 3.5 Pipeline Component Descriptions (accurate for v2.2)

| Component | Type | Description |
|-----------|------|-------------|
| M1 Detection | Deterministic (rule-based) | Threshold over UCS score: UCS ≤ 1 → calibrate. No LLM call. |
| M2 Diagnosis | Deterministic (rule-based) | Classification from extraction features: claims_superiority, has_directional_claim, etc. No LLM call. |
| M3 Correction | LLM (openai/gpt-4o-mini) | Type-aware correction generation. Evidenced by correction_source=llm in ledger. Fallback is treated as pipeline failure. |
| M4 Validation | Deterministic (rule-based) | Length, assertion, non-copy checks. No LLM judge. |
| External Scorer | Deterministic (pure Python) | Post-run evaluation using case-level primary_checks. No LLM calls. No pipeline imports. |

---

## 4. Exact Information Given to Each Condition

### 4.1 Original

```
Input:
  - input_question: str
  - original_answer: str

Processing:
  Return original_answer directly. No API call.

Output:
  corrected_response = None
```

### 4.2 Generic

```
Input:
  - input_question: str
  - original_answer: str
  - evidence_excerpt: str  (from blinded case)

System prompt:
  GENERIC_BASELINE_PROMPT.txt
  "Revise the answer to be accurate, appropriately cautious, evidence-based
   and concise. Preserve useful supported information and avoid adding
   unsupported claims."

User prompt construction:
  Question: {input_question}

  Relevant evidence:
  {evidence_excerpt}

  Original answer:
  {original_answer}

  Revised answer:

Forbidden inputs:
  NOT failure_family
  NOT target_failure_span
  NOT failure_statement
  NOT content_required_to_change
  NOT required_boundary
  NOT reference_correction
  NOT primary_checks
```

### 4.3 Generic+Diagnosis

```
Input:
  - input_question: str
  - original_answer: str
  - evidence_excerpt: str  (from blinded case)
  - failure_family: str    (from gold case, e.g., "unsupported_numerical_specificity")
  - target_failure_span: str  (from gold case, e.g., "exactly 43 minutes")
  - failure_statement: str    (from gold case)
  - content_required_to_change: list[str]  (from gold case)
  - required_boundary: str or null  (from gold case, only non-null for Group C)

System prompt:
  GENERIC_BASELINE_PROMPT.txt
  (Same as Generic condition — the prompt does not change)

User prompt construction:
  Question: {input_question}

  Relevant evidence:
  {evidence_excerpt}

  Original answer:
  {original_answer}

  Failure diagnosis:
  - Type: {failure_family}
  - Problematic content: "{target_failure_span}"
  - Issue: {failure_statement}
  - Required changes: {content_required_to_change.join("; ")}
  [If required_boundary is not null:]
  - Required boundary: {required_boundary}

  Revised answer:

Forbidden inputs:
  NOT reference_correction
  NOT primary_checks
  NOT secondary_checks

Note:
  Diagnosis information comes from gold labels (ground truth), NOT from
  CMC's M2 output. This is an ORACLE condition — it receives perfect
  diagnostic information to establish the upper bound for diagnosis-informed
  generic correction. If Generic+Diagnosis ≈ Generic, then even perfect
  diagnosis does not improve a generic correction prompt.
```

### 4.4 CheckMyCoach

```
Input:
  - input_question: str
  - original_answer: str
  - evidence_excerpt: str  (fed as pre-retrieved evidence to calibrate())

Pipeline call:
  calibrate(
      response=original_answer,
      question=input_question,
      evidence=[{
          "id": "case_evidence",
          "type": "inline",
          "content": evidence_excerpt,
          "source": "blinded case file"
      }]
  )

Pipeline stages:
  Step 0: Receive pre-retrieved evidence (skip KC runtime retrieval)
  Step 1: UCS Engine — evaluate calibration of original_answer
  Step 2: M1 — does UCS score indicate need for calibration?
  Step 3: M2 — if yes, diagnose failure type
  Step 4: M3 — type-aware correction
  Step 5: M4 — validation (did correction change the text?)
  Step 6: score_delta — UCS before/after (descriptive, not primary metric)

Forbidden inputs:
  NOT failure_family (pipeline derives its own)
  NOT target_failure_span
  NOT failure_statement
  NOT content_required_to_change
  NOT required_boundary
  NOT reference_correction

Model assignments:
  - UCS Engine: deepseek-chat (pipeline default, temperature 0.3)
  - M1 Detection: rule-based (threshold over UCS score)
  - M2 Diagnosis: deepseek-chat (pipeline default, temperature 0.3)
  - M3 Correction: openai/gpt-4o-mini (temperature 0.3, max_tokens 1024)
  - M4 Validation: openai/gpt-4o-mini (temperature 0.3)
```

---

## 5. Evidence Equalization

### 5.1 Mechanism

ALL three correction conditions receive the identical evidence payload:

```
{
  "id": "case_evidence",
  "type": "inline",
  "content": <evidence_excerpt from blinded case>,
  "source": "blinded case file"
}
```

For **Generic** and **Generic+Diagnosis**: evidence_excerpt is inserted into the user prompt.

For **CMC**: evidence_excerpt is passed as the `evidence` parameter to `calibrate()`. This bypasses KC runtime retrieval entirely. The pipeline still runs its internal UCS/M1/M2/M3/M4 stages, but uses the provided evidence rather than retrieving its own.

### 5.2 Rationale

This removes the single most damaging v1 confound. In v1, CMC retrieved evidence that was irrelevant to the case content (e.g., `procedure.one_rm_testing` for a question about aerobic exercise duration), while Generic received a curated case-specific excerpt. Any comparison between conditions was structurally confounded by different evidence inputs.

Under v2.2, Generic, Generic+Diagnosis, and CMC differ ONLY in:
- Whether they receive failure diagnosis information (Generic vs Generic+Diagnosis)
- Their internal correction mechanism (generic prompt vs type-aware pipeline)

The evidence is identical across all three.

### 5.3 Note on CMC Identity

This changes CMC from the v1 configuration: CMC no longer uses its native retrieval. This means v2.2 tests CMC's **correction mechanism** (UCS→M1→M2→M3→M4) with fixed evidence, not CMC as an end-to-end package with its own retrieval.

If the intended contribution is "CMC as a complete system," a separate "CMC-native" condition (CMC with its own retrieval) should be added as a 5th condition. This is NOT done in v2.2 to minimize engineering change and maintain design simplicity. The v2.2 claim is about **correction mechanism**, not about end-to-end package performance.

---

## 6. Blinded Case Format

### 6.1 New blinded file: `blinded_cases_v2.2.jsonl`

Created from `cases.jsonl` by extracting only the permitted fields. Each case record contains:

```json
{
  "case_id": "CMC-A-001",
  "input_question": "...",
  "original_answer": "...",
  "evidence_excerpt": "...",

  "failure_family": "unsupported_numerical_specificity",
  "target_failure_span": "exactly 43 minutes",
  "failure_statement": "The answer asserts a precise value of 43 minutes...",
  "content_required_to_change": ["Replace 43 minutes with the range 30-60 minutes"],
  "required_boundary": null
}
```

### 6.2 Fields STILL excluded from blinded file

The following fields from `cases.jsonl` are NEVER exposed to any condition:

| Field | Reason for exclusion |
|-------|---------------------|
| `reference_correction` | Defines a specific acceptable answer — would bias correction output |
| `primary_checks` | Used for outcome evaluation — must remain hidden from conditions |
| `secondary_checks` | Used for human review — must remain hidden |
| `supported_content_to_retain` | Used for atom-level retention checking — would hint at expected output |
| `forbidden_new_claims` | Used for human review — would bias against introducing these |
| `linked_knowledge_object_ids` | Used for evidence-link metric — not relevant when evidence is provided inline |
| `source_provenance` | Metadata — not relevant to correction |
| `ambiguity_flags` | Constructor notes — not relevant |
| `adjudication_status` | Constructor metadata — not relevant |

### 6.3 Hash verification

The blinded file's SHA-256 is recorded in the execution manifest before any API calls. Any post-hoc modification invalidates the freeze.

---

## 7. Primary Metrics (with condition applicability)

| Metric | Original | Generic | Generic+Diagnosis | CMC | Pass condition |
|--------|----------|---------|-------------------|-----|----------------|
| Targeted failure removal | ❌ (no correction) | ✅ | ✅ | ✅ | All removal primary checks pass |
| Supported info retention | ❌ | ✅ | ✅ | ✅ | All retention atoms preserved |
| New unsupported claim rate | ❌ (defines baseline) | ✅ (human) | ✅ (human) | ✅ (human) | Zero new claims |
| Boundary preservation | ❌ | ✅ (10 Group-C) | ✅ (10 Group-C) | ✅ (10 Group-C) | All boundary checks pass |
| Evidence-link accuracy | N/A (no evidence) | ✅ (trivial — case excerpt is linked) | ✅ (trivial — case excerpt is linked) | ✅ (trivial — case excerpt is linked) | evidence_hash matches |
| Correction minimality | ❌ | ✅ (descriptive) | ✅ (descriptive) | ✅ (descriptive) | Lower = less editing |
| Pipeline completion | ✅ (trivial) | ✅ | ✅ | ✅ | No technical failures |
| Parse/schema success | ✅ | ✅ | ✅ | ✅ | All required fields present |

**Note:** Evidence-link accuracy is 40/40 for all conditions under v2.2 because all use the same frozen case excerpt. This metric becomes a format check rather than a retrieval quality test. This is appropriate because the v2.2 research question is about correction mechanism, not retrieval quality.

---

## 8. Analysis Plan

### 8.1 Primary contrast

The key comparison is:

**Generic+Diagnosis vs Generic** — does diagnosis information improve generic correction?

This is tested via exact McNemar test on paired binary outcomes (failure removed: yes/no per case). The 40-case corpus gives 80% power to detect a difference of ≥10 discordant pairs at α=0.05 (two-sided). Report discordant counts and exact binomial p-value.

### 8.2 Secondary contrast

**CMC vs Generic+Diagnosis** — does type-aware correction improve over oracle-informed generic correction?

Same McNemar test structure. If CMC > Generic+Diagnosis, the advantage is attributable to M3's correction mechanism (not to diagnosis alone). If CMC ≈ Generic+Diagnosis, the advantage over Generic is entirely attributable to having diagnosis information.

### 8.3 Exploratory analyses

- **Failure family stratification:** Compute removal rates per family (15/15/10 split). Report with raw counts only — no inferential test on subgroups.
- **Correction minimality:** Report median and IQR of normalized Levenshtein distance per condition. Descriptive only.
- **Case-level result matrix:** Report every case's pass/fail outcome per condition in a 40×4 table. Identify which cases all conditions fail (hard cases) and which only CMC or Generic+Diagnosis passes.

### 8.4 Prohibited analyses

- No composite headline score
- No between-case independence assumption (40 cases are deliberately constructed, not IID sampled)
- No population inference (results describe this corpus only)
- No LLM judge for outcome assessment (human secondary review only)
- No post-hoc exclusion of cases that "the pipeline would not trigger on" — M4_passed and needs_calibration are recorded but not used to filter denominators

---

## 9. Reviewer Attack Points and Defenses

### Attack 1: "Generic+Diagnosis receives oracle diagnosis from gold labels, not real M2 output."

**Defense:** This is intentional. The oracle condition establishes the upper bound for diagnosis-informed generic correction. If Generic+Diagnosis ≈ Generic (H3 not rejected), then even perfect diagnostic information does not help a generic correction prompt — the bottleneck is the correction mechanism, not the diagnosis. If CMC > Generic+Diagnosis, the improvement is attributable to M3's type-aware templates, not to having more information. This design separates the "detection" claim from the "correction" claim, which the three-condition design could not do.

Limitation acknowledged: CMC's M2 may produce different (better or worse) diagnoses than the oracle. This means the CMC vs Generic+Diagnosis comparison tests the pipeline's combined detection+correction against oracle-informed generic correction. A fifth condition (Generic + M2 output) would further decompose, but this is beyond v2.2 scope.

### Attack 2: "CMC without its native retrieval is not CMC."

**Defense:** Accepted. v2.2 tests CMC's **correction mechanism** under equal evidence, not CMC as an end-to-end package. The claim is bounded to correction mechanism comparison. The v1 execution already tested CMC-with-native-retrieval and found it irrecoverable due to irrelevant evidence. A separate "CMC-native" condition is a natural extension for future work but is outside the current research question, which is about whether type-aware correction improves over generic correction when evidence is held equal.

### Attack 3: "The prompt for Generic and Generic+Diagnosis must be identical except for the diagnosis section."

**Defense:** It IS identical. Both use GENERIC_BASELINE_PROMPT.txt as the system prompt. The user prompt for Generic+Diagnosis simply prepends the diagnosis block before the "Revised answer:" prompt. The correction instruction (be accurate, cautious, evidence-based, concise; preserve; avoid unsupported) is unchanged. This ensures the diagnosis information is the ONLY additional signal.

### Attack 4: "Temperature 0.3 without seeds — non-determinism undermines inference."

**Defense:** Temperature 0.3 reduces variability compared to v1's 0.5 but does not eliminate it. We acknowledge this as a limitation. The paired within-case design (same case across all four conditions in one pass) means that non-determinism adds noise symmetrically. A single observation per case×condition is acceptable for exploratory paired comparisons but does not support effect size estimation. Future work should run multiple seeds when seed support becomes available from the provider.

### Attack 5: "40 cases is too small for any meaningful comparison."

**Defense:** This is a constructed evaluation set, not a population sample. The appropriate test (McNemar) conditions on discordant pairs and does not require a minimum sample size in the traditional power sense. The 40-case corpus is explicitly framed as an internal diagnostic instrument, not an IID sample. We report exact p-values and case-level outcomes; we do not generalize to other questions, domains, models, or user populations. The corpus size is comparable to established evaluation sets in the calibration literature (e.g., Band et al. 2024: 50 cases; Zhou et al. 2024: 36 cases).

### Attack 6: "M4 validation in CMC is a tautology (just checks text changed)."

**Defense:** We agree. M4 is NOT used as an evaluation metric in v2.2. All outcomes are scored by the case-level primary checks (deterministic regex/alias tests), not by M4. M4 is recorded as a pipeline trace field for completeness only. The external evaluation is the case-defined primary checks, which assess evidence fidelity, boundary preservation, and failure removal independently of the pipeline's internal validation.

### Attack 7: "Why not test temperature=0 for full determinism?"

**Defense:** OpenRouter does not guarantee seed reproducibility, and the CMC pipeline's UCS engine has an internal LLM stage that is not under our temperature control in the same way. Temperature 0.3 represents a pragmatic trade-off between reducing variance and maintaining the pipeline's operational characteristics. We document this clearly as a limitation.

---

## 10. Engineering Changes from v1

### Required changes (MINIMAL — reuse existing infrastructure)

| Component | Change | Complexity |
|-----------|--------|------------|
| `run_single_case.py` | Add `run_generic_with_diagnosis()` function | **Low** — 30 lines, adapts from `run_generic()` |
| `run_single_case.py` | Modify `run_checkmycoach()` to accept optional evidence parameter | **Low** — evidence parameter already supported by `calibrate()` |
| `run_single_case.py` | Modify `build_record()` to handle `generic_with_diagnosis` condition | **Low** — add one branch |
| `run_single_case.py` | Add `generic_with_diagnosis` to condition enum and dry-run output | **Low** |
| `run_evaluation.py` | Add `generic_with_diagnosis` to condition iteration | **Low** |
| `result.schema.json` | Add `generic_with_diagnosis` to condition enum | **Low** — one line |
| Model config | Raise CMC M3 max_tokens from 300 to 1024 | **Low** — config change |
| Model config | Lower CMC and Generic temperature from 0.5 to 0.3 | **Low** — config change |
| Data | Create `blinded_cases_v2.2.jsonl` from `cases.jsonl` | **Low** — scripted extraction |
| Manifest | Create `execution/manifest_v2.2.json` with SHA-256 hashes | **Low** |

### No change needed

| Component | Reason |
|-----------|--------|
| `cases.jsonl` | Gold labels unchanged — same 40 cases |
| `GENERIC_BASELINE_PROMPT.txt` | Same prompt for both Generic conditions |
| `generic_correction.py` | Interface unchanged — just new caller |
| `calibrate()` in `agent_pipeline.py` | Already accepts `evidence` parameter |
| M1/M2/M3/M4 source code | Pipeline internal logic unchanged |
| Evaluation protocol documents | New v2.2 document replaces v1 for this run |
| Claim boundary rules | Unchanged — same CLAIM_BOUNDARY.md |
| Human review protocol | Same procedure; just new condition to blind |

### Estimated engineering effort

- Python code changes: ~50 lines total
- New config/data files: ~4 files
- No new dependencies
- No pipeline refactoring

---

## 11. Freeze Procedure

1. Create `blinded_cases_v2.2.jsonl` from frozen `cases.jsonl`
2. Record SHA-256 of all artifact files in `execution_manifest_v2.2.json`
3. Run dry-run (all 40 cases × 4 conditions, no API calls)
4. Verify all 160 ledger records have correct schema and no gold leakage
5. Run validation tests (existing 68 tests + 4 new Generic+Diagnosis tests)
6. Sign checklist
7. Execute one-case smoke run with API calls
8. Verify output format and provenance
9. Gate sign-off
10. Full execution: 40 cases × 4 conditions

---

## 12. Claim Boundary

### What this experiment CAN support

1. (Generic+Diagnosis > Generic) indicates that failure diagnosis information improves generic correction on this corpus.
2. (CMC ≥ Generic+Diagnosis) indicates that type-aware template correction preserves or improves upon oracle-informed generic correction.
3. (Generic+Diagnosis ≈ Generic) indicates that even perfect diagnosis information does not improve a generic correction prompt — the bottleneck is the correction mechanism.
4. Per-family stratified results (e.g., diagnosis helps more for missing_boundary than for unsupported_factual_claim).
5. Case-level pass/fail patterns identifying which cases are systematically hard.

### What this experiment CANNOT support

1. Generalization to populations, domains, models, or deployment conditions beyond this 40-case constructed corpus.
2. Claims about CMC's end-to-end system performance (with its own retrieval) — that is a separate evaluation.
3. Clinical accuracy or safety claims.
4. Human-AI trust, decision quality, or behavioral outcomes.
5. Prevalence estimates for any failure type in natural model outputs.
6. Claims about CMC's internal diagnostic accuracy (M2 is NOT evaluated against gold labels in this design — the oracle condition bypasses it).

---

## 13. Status

```
┌─────────────────────────────────────────────────┐
│         V2.1 PROTOCOL — DESIGN FROZEN           │
│                                                 │
│  Next actions:                                  │
│  1. Review and approve protocol                 │
│  2. Generate blinded_cases_v2.2.jsonl           │
│  3. Implement runner changes (~50 LOC)          │
│  4. Update result.schema.json                   │
│  5. Dry-run + test gate                         │
│  6. Smoke run + verification                    │
│  7. Full execution (40 × 4 = 160 records)       │
└─────────────────────────────────────────────────┘
```
