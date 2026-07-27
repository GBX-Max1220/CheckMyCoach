# Case-Level Audit — CheckMyCoach Evaluation v1

**Auditor:** Hermes Agent 4 (independent red-team)
**Date:** 2026-07-27
**Method:** Independent inspection of `cases.jsonl`, `build_v1_evaluation.py`, evidence excerpts, and KC objects.

---

## Audit Criteria

For each of 40 cases:
1. **Failure is genuine** — the original answer deviates from the frozen evidence excerpt in a closed-world-decidable way.
2. **Target span is correct** — the span is a literal substring of `original_answer`.
3. **Evidence link supports the label** — the KC object hash and excerpt match, and the excerpt licenses the failure statement.
4. **Reference correction preserves valid content** — the reference removes the failure without erasing supportable content.
5. **Case is not circular** — the failure statement does not encode the correction strategy.
6. **No expert dependency is hidden** — the case is decidable from the supplied closed-world evidence.
7. **Case is not a near-duplicate** — different failure family, different evidence object, or different failure mechanism.
8. **Metric does not encode the intervention** — primary checks don't assume a specific correction method.

---

## Full Audit Table

| Case | Failure genuine? | Target span correct? | Evidence link valid? | Reference preserves support? | Not circular? | No hidden expert dep? | Not near-duplicate? | Metric neutral? |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Group A — Unsupported Numerical Specificity (15)** |
| CMC-A-001 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-002 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-003 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-004 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-005 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-006 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-007 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-008 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-009 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-010 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-011 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-012 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-013 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-014 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-A-015 | YES | YES | YES | YES | YES | YES | YES | YES |
| **Group B — Unsupported Factual Claim (15)** |
| CMC-B-001 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-002 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-003 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-004 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-005 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-006 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-007 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-008 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-009 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-010 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-011 | YES | YES | YES | YES | YES | YES | SEE NOTE | YES |
| CMC-B-012 | YES | YES | YES | YES | YES | YES | SEE NOTE | YES |
| CMC-B-013 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-014 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-B-015 | YES | YES | YES | YES | YES | YES | YES | YES |
| **Group C — Missing Boundary (10)** |
| CMC-C-001 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-C-002 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-C-003 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-C-004 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-C-005 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-C-006 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-C-007 | YES | YES | YES | YES | YES | YES | SEE NOTE | YES |
| CMC-C-008 | YES | YES | YES | YES | YES | YES | SEE NOTE | YES |
| CMC-C-009 | YES | YES | YES | YES | YES | YES | YES | YES |
| CMC-C-010 | YES | YES | YES | YES | YES | YES | YES | YES |

---

## Notes on Near-Duplicates

### CMC-B-011 / CMC-C-007 (Untrained seniors resistance training)

Both use `recommendation.initial_training_intensity_volume_untrained_seniors`.
- **B-011**: Original answer says "start with high intensity and high volume" — tests reversal of factual claim (test says low, answer says high).
- **C-007**: Original answer says "begin with low intensity and volume" — tests omission of individualization boundary.

**Verdict:** Different failure families, different answers, different failure mechanisms. **Not a near-duplicate.** Both cases test orthogonal properties of the same evidence object.

### CMC-B-012 / CMC-C-008 (Postexercise carbohydrate and protein)

Both use `recommendation.postexercise_carbohydrate_and_protein`.
- **B-012**: Original answer says "never facilitates" — tests reversal of a factual statement.
- **C-008**: Original answer correctly states "add protein to facilitate" — tests omission of the low-carb condition boundary.

**Verdict:** Different failure families, different answers, orthogonal failure mechanisms. **Not a near-duplicate.** The B-012 and C-008 cases test entirely distinct failure modes on the same evidence.

### CMC-B-002 / CMC-C-005 (Dynamic stretching)

Both reference `recommendation.dynamic_stretching_before_activity`.
- **B-002**: "Dynamic stretching should be avoided" — tests factual reversal.
- **C-005**: "Use movement-based stretching" — tests omission of controlled/no-bouncing boundary.

**Verdict:** Different failure families. B-002 receives only the dynamic-stretching object; C-005 also references ballistic stretching. **Not a near-duplicate.**

---

## Target Span Correctness for Group C Cases

All 10 Group C cases have `target_failure_span` identical to `original_answer`. This is **intentional and correct** for the missing-boundary family: the entire under-scoped answer is the target because the failure is an omission of a required boundary from an otherwise useful statement. The primary checks verify (a) retention of the supported content AND (b) addition of the missing boundary. This is a valid design.

---

## Effective Independent Case Families

Based on evidence-object overlap:

| Evidence Object(s) | Cases | Independent? |
|--------------------|-------|:---:|
| `warning.ballistic_stretching` | B-001 | YES |
| `recommendation.dynamic_stretching_before_activity` (+ `warning.ballistic_stretching` for C-005) | B-002, C-005 | YES* |
| `recommendation.clothing_considerations_for_exercise_in_heat` | B-003 | YES |
| `recommendation.clothing_considerations_for_exercise_in_cold` | B-004 | YES |
| `recommendation.avoid_alcohol_and_tobacco_during_cold_exposure` | B-005 | YES |
| `recommendation.benefits_of_regular_physical_activity_for_diabetes` | B-006 | YES |
| `threshold.age.older_adult` | B-007 | YES |
| `concept.high_intensity_interval_training` | B-008 | YES |
| `threshold.resting_heart_rate` | B-009 | YES |
| `recommendation.individualized_hydration_weight_changes` | B-010, C-006 | YES* |
| `recommendation.initial_training_intensity_volume_untrained_seniors` | B-011, C-007 | YES* |
| `recommendation.postexercise_carbohydrate_and_protein` | B-012, C-008 | YES* |
| `recommendation.sports_drink_composition_hot_weather` | B-013, C-010 | YES* |
| `recommendation.test_sequencing_order` | B-014 | YES |
| `concept.static_stretch` / `recommendation.static_stretch_duration` | B-015, A-010 | YES |
| All Group A remaining (A-001–A-015) and single-use evidence objects | Various | YES |

*Same evidence object, different failure families and different original answers — independent for analysis purposes when reported by failure family.

**Total effective independent families:** 40/40 (no true near-duplicate pairs). The shared evidence objects between B and C families test orthogonal failure modes and must be reported by family, not pooled.
