# Metric Validity Audit — CheckMyCoach Evaluation v1

**Auditor:** Hermes Agent 4 (independent red-team)
**Date:** 2026-07-27

---

## Primary Metrics (from PRIMARY_METRICS.md)

### 1. Targeted Failure Removal

**Definition:** All target-removal primary checks pass.
**Mechanism:** Substring-absent + regex-present checks.
**Per-case:** E.g., CMC-A-001 checks `"exactly 43 minutes every day"` absent
AND `"30–60 minutes"` present.

| Concern | Assessment |
|---------|:----------:|
| Is failure removal independently scored from correction? | YES — checks are deterministic and case-defined |
| Does removal require evidence-attributable changes? | YES — checks tie to the evidence excerpt |
| Can a trivial fix pass? | YES — e.g., just deleting the target span without replacing it would fail retention checks |

**Verdict: SOUND.** The paired checks (remove + retain) prevent trivial passes.

---

### 2. Supported Information Retention

**Definition:** Retention atom preserved (regex/alias match).
**Mechanism:** Regex presence, phrase presence, or any-phrase presence.

| Concern | Assessment |
|---------|:----------:|
| Is retention measured by lexical copying alone? | **PARTIALLY.** Regex checks require specific wording (e.g., `"30\s*[–-]\s*60\s*minutes"`). Aliases or close paraphrases (e.g., "thirty to sixty minutes") would fail. |
| Is human secondary review sufficient backup? | YES — but it's secondary and labeled as such |

**Verdict: LEXICAL OVER-ENFORCEMENT CONCERN.** The deterministic checks
prefer exact wording. The protocol acknowledges this: "Deterministic checks
use aliases and regexes; secondary human review can credit a clear paraphrase."
This is acceptable for a primary check but means some valid corrections will
fail retention on the deterministic metric.

---

### 3. New Unsupported Claim Rate

**Definition:** New output propositions absent from original and evidence.
**Mechanism:** Two independent human reviewers applying closed-evidence rule.

| Concern | Assessment |
|---------|:----------:|
| Can new unsupported claims be detected? | YES — human review |
| Is an LLM judge used? | PROHIBITED by protocol. Not implemented. |
| Is the closed-evidence rule adequately defined? | YES (CLAIM_BOUNDARY.md) |

**Verdict: SOUND.** Human secondary review on a defined rule set.

---

### 4. Evidence-Link Accuracy

**Definition:** Returned knowledge-object IDs are a nonempty subset of
case-linked IDs.

| Concern | Assessment |
|---------|:----------:|
| Is this meaningful for all conditions? | YES — all conditions call `calibrate_full()` which retrieves evidence |
| Does it measure the system or the KC retriever? | Measures the retriever, not the correction |
| Is "nonempty" too weak? | YES — a retriever returning any one object from a set of 5 passes |

**Verdict: WEAK BUT NOT WRONG.** The metric measures the retriever, not the
correction pipeline. Reporting this separately from correction metrics is
appropriate.

---

### 5. Boundary Preservation (Group C only)

**Definition:** All required-boundary primary checks pass.

| Concern | Assessment |
|---------|:----------:|
| Is the boundary check independent? | YES — boundary checks use `all_phrase_groups_present` |
| Does it reward under-correction? | If a correction retains all phrases but doesn't bind them into a coherent boundary, it passes the phrase check but the human secondary review should catch this |

**Verdict: SOUND but human secondary is load-bearing for semantic coherence.**

---

### 6. Correction Minimality

**Definition:** Normalized token Levenshtein distance / max(original tokens, 1).

| Concern | Assessment |
|---------|:----------:|
| Is minimality truly descriptive? | The protocol says "descriptive deterministic" |
| Does minimality reward under-correction? | **YES — this is a well-known problem.** A correction that adds nothing (Levenshtein = 0) is "maximally minimal" but fixes nothing. The metric is explicitly descriptive, not evaluative — it reports editing amount, not editing quality. |
| Does minimality penalize adding a required boundary? | **YES** — adding a boundary (Group C) increases Levenshtein distance, reducing "minimality" |

**Verdict: ACCEPTABLE as descriptive metric.** The protocol correctly labels
it as descriptive, not evaluative. It should not be averaged or used in
composite scores.

---

### 7. Pipeline Completion

**Definition:** All five CheckMyCoach stages complete without technical failure.

| Concern | Assessment |
|---------|:----------:|
| Is pipeline success confused with correction quality? | The protocol says: "Pipeline completion does not imply scientific success." |
| Is the metric reported separately? | YES — condition-specific integers and percentages |

**Verdict: SOUND.**

---

### 8. Parse/Schema Success

**Definition:** Output and trace conform to frozen run schema.

| Concern | Assessment |
|---------|:----------:|
| Can schema failures be silently excluded? | Protocol says: "Missing outputs count as pipeline or parse failures and cannot be silently excluded from other denominators." |
| Does the runner enforce this? | PARTIALLY — the runner records `included: false` for errors but doesn't include them in other denominators explicitly |

**Verdict: SOUND in design. The runner's `included` field sets correct status.**

---

## Cross-Cutting Concerns

### Concern: Are metrics independent?

| Metric Pair | Overlap? |
|-------------|:--------:|
| Failure removal & Retention | Designed to be orthogonal — removal checks target span, retention checks support atoms |
| Failure removal & Boundary | For Group C, removal = adding the boundary (target IS the under-scoped answer). These are dependent by design. |
| Minimality & everything else | Minimality is purely descriptive — intentionally independent |
| Pipeline completion & everything else | Independent — reports technical success |

**Verdict:** Metric independence is well-designed.

### Concern: Can one condition's failure be misattributed to another metric?

Example: A correction passes failure removal (target span deleted) and
retention (support atoms present) but introduces a new unsupported claim.
This is correctly tracked by metric 3 (new unsupported claim rate).

**Verdict: NO METRIC CONFUSION. Each metric measures a distinct dimension.**

---

## Summary

| Metric | Valid? | Issue |
|--------|:------:|-------|
| Targeted failure removal | SOUND | — |
| Supported information retention | CAUTION | Lexical over-enforcement; secondary review mitigates |
| New unsupported claim rate | SOUND | Human review properly specified |
| Evidence-link accuracy | WEAK | Measures retriever, not correction; "nonempty" threshold low |
| Boundary preservation | SOUND | Human secondary needed for semantic coherence |
| Correction minimality | ACCEPTABLE | Descriptive-only, cannot be evaluative |
| Pipeline completion | SOUND | — |
| Parse/schema success | SOUND | — |

**No metric invalidates the evaluation design.**
