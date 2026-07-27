# Final Gate Review — CheckMyCoach Evaluation v1

**Reviewer:** Hermes Agent 4 (independent red-team)
**Date:** 2026-07-27
**Status:** BLOCKED

---

## Verdict

**REJECT — SCIENTIFIC DEFECTS**

*(With secondary implementation defects that compound the scientific concerns.)*

---

## Rationale

The evaluation protocol is well-designed on paper: three conditions, blinded analysis,
deterministic primary checks, human secondary review, no composite score, explicit
prohibition on LLM-as-judge. The case construction is thorough — 40 cases with fresh
gold, exact target spans, evidence-linked provenance, no historical label bleed.

However, the **implementation betrays the protocol in two critical ways** that
invalidate the primary research question: *Does CheckMyCoach correct failures better
than a generic improvement baseline?*

The defects are at the condition-isolation level, not at the case-construction level.
They cannot be fixed by authoring more cases or tweaking metrics — they require
runner rewrites.

---

## Short Summary of Blocking Defects

| # | Defect | Type | Blocks |
|---|--------|------|--------|
| D1 | Generic condition uses different prompt than protocol specifies | Scientific | Condition comparison invalid |
| D2 | Generic condition receives no question or evidence — only raw text | Scientific | Baseline artificially weak |
| D3 | Generic correction is LLM-based, not deterministic-rule — signal is confounded | Scientific | Can't distinguish "any LLM helps" from "targeted correction helps" |
| D4 | All three conditions share the same pipeline (retrieval + generation) | Scientific | Can't isolate correction quality from evidence-retrieval quality |
| D5 | Runner `discover_cases()` looks for `"question"` but cases use `"input_question"` | Implementation | Batch runner finds 0 production cases |

These defects are structural and unfixable without protocol-consistent runner changes.
After a dry run with the corrected runner, a separate final gate is required.

---

## Required Fixes

1. Generic correction must receive: question + original answer + eligible evidence payload + the exact prompt from `GENERIC_BASELINE_PROMPT.txt`.
2. Generic correction must use the frozen prompt from `GENERIC_BASELINE_PROMPT.txt`, not the implementation's hardcoded alternative.
3. Either (a) make generic correction deterministic-rule-based (as MINIMUM_PATCH_PLAN proposed) or (b) document that the comparison is "pipeline-with-M3 vs pipeline-with-generic-LLM" and adjust claims accordingly.
4. Add a "raw LLM" condition (no evidence retrieval) to isolate retrieval contribution from correction contribution.
5. Fix field name in `discover_cases()` to match `CASE_SCHEMA.json`.
