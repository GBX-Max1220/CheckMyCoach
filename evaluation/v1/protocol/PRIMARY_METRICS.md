# Separate Evaluation Outcomes

Version: 1.0.0

No composite score is defined.

| Outcome | Unit and denominator | Operationalization | Tier |
|---|---|---|---|
| Targeted failure removal | case; all attempted cases | All target-removal primary checks pass | Primary deterministic |
| Supported information retention | retention atom; all specified atoms | Regex/alias atom retained; semantic paraphrase reported separately | Primary deterministic + secondary human sensitivity |
| New unsupported claim rate | new output proposition; all output propositions | Two independent humans apply the closed-evidence rule; report claims and cases with ≥1 | Secondary human, no LLM |
| Evidence-link accuracy | case; all cases with retrieval output | Returned knowledge-object IDs are a nonempty subset of case-linked IDs | Primary deterministic |
| Boundary preservation | applicable case; 10 Group-C cases | All required-boundary primary checks pass | Primary deterministic |
| Correction minimality | case; all parseable corrections | Normalized token Levenshtein distance / max(original tokens, 1); lower is less editing | Descriptive deterministic |
| Pipeline completion | case; all 40 per active correction condition | All five CheckMyCoach stages complete without technical failure; generic condition records one completion event | Primary deterministic |
| Parse/schema success | case; all outputs | Output and trace conform to frozen run schema | Primary deterministic |

Report condition-specific integer numerators and denominators, percentages, and exact lists of technical failures. Target removal does not imply no new unsupported claims. Retention does not imply minimality. Pipeline completion does not imply scientific success.
