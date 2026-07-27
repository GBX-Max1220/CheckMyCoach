# CheckMyCoach Internal Evaluation Protocol

Version: 1.0.0  
Build date: 2026-07-27  
Status: constructor-complete; independent audit pending

## Purpose and scope

This is a clean, internal, constructed evaluation set for comparing correction behavior. It is not a public benchmark, not a prevalence sample, and not evidence that any model or deployed coach makes these errors at a particular rate. A top-tier lab could justify this project as a system-evaluation instrument only if the evaluation set and the system remain developmentally separated. The present release enforces that separation at the artifact level.

The 40 cases test whether a correction condition can remove one identifiable failure while retaining supplied supported content and avoiding new unsupported claims. Knowledge Compiler objects are frozen inputs with page-level provenance, but their repository documents describe content review as automated rather than expert. Accordingly, the scientific gold here is **fidelity to the supplied evidence object**, not a claim that the object is independent clinical truth.

## Conditions

1. **Original**: score `original_answer` without correction.
2. **Generic correction**: provide only the question, original answer, eligible evidence payload, and the exact frozen prompt in `GENERIC_BASELINE_PROMPT.txt`.
3. **CheckMyCoach**: use the existing detection → diagnosis → evidence retrieval → type-aware correction → validation pipeline.

Neither correction condition may receive `failure_family`, `target_failure_span`, `failure_statement`, `content_required_to_change`, `required_boundary`, `forbidden_new_claims`, `reference_correction`, `primary_checks`, `secondary_checks`, or `adjudication_status`. The reference correction is an audit aid, not a canonical answer and not model input.

## Assignment and blinding

The execution owner creates a blinded run view containing only `case_id`, `input_question`, `original_answer`, and the evidence payload that the condition is allowed to receive. Gold files remain outside the runtime directory. Condition names are masked during outcome review. Any human secondary review is performed on paired outputs in randomized order without system identity.

## Failure families

- **Unsupported numerical specificity (15)**: the answer chooses a point, tuple, schedule, or certainty level more specific than the evidence permits. Decimal places are neither necessary nor sufficient.
- **Unsupported factual claim (15)**: an identifiable proposition contradicts or is absent from the closed supplied evidence.
- **Missing boundary (10)**: useful content is present, but an explicit safety, applicability, uncertainty, or conditional boundary from the supplied evidence is omitted.

## Gold construction

Historical cases and labels were candidate discovery material only. No historical label enters `cases.jsonl`. Every case has a fresh failure statement, frozen evidence excerpt, exact target span, retention atoms, prohibited content, a non-unique reference correction, and case-level checks. All target spans are literal substrings of the original answer; for omissions, the span is the under-scoped recommendation requiring qualification.

## Execution contract

Run all 40 cases in all three conditions. Preserve raw outputs, pipeline events, retrieval IDs, parse status, and errors. Do not retry scientific failures. Technical retries must be pre-specified and logged. A failed pipeline or invalid schema remains a failure, not missing data. Do not call an LLM to score outputs.

## Outcome assessment

Primary checks are deterministic string/regex/schema checks defined per case. Secondary semantic review uses the rules in `CLAIM_BOUNDARY.md` and two independent human reviewers; an LLM judge is prohibited. The reference correction illustrates one acceptable repair only. Alternative wording passes if it satisfies the checks and the evidence boundary.

## Analysis

Report each outcome separately by condition and failure family with numerator and denominator. Use paired case-level comparisons for exploratory inference; do not treat 40 deliberately constructed cases as an IID population sample. No composite headline score is allowed. Missing outputs count as pipeline or parse failures and cannot be silently excluded from other denominators.

## Change control

After independent audit begins, any case change increments the dataset version and records the old/new hashes. Do not overwrite v1 artifacts. The system team must not tune CheckMyCoach on these 40 cases after viewing case-level results; discovered defects become candidates for a separate development set or v2 evaluation release.
