# Claim and Boundary Rules

Version: 1.0.0

## Atomic proposition

An atomic proposition is the smallest clause that can be independently supported, contradicted, or conditioned by the supplied evidence. Coordinated clauses with different truth conditions are split. Units, population, timing, direction, comparator, and modality belong to the same proposition when removing them would change what is being asserted.

## Unsupported numerical specificity

A number fails when the evidence supplies only a range, conditional schedule, approximate value, or unresolved timing but the answer presents one interior point or tuple as uniquely correct, exact, optimal, or universal. Merely adding decimals is not the rule. A point may be acceptable as an example only if explicitly marked as one admissible example and the evidence range/uncertainty is retained.

## Unsupported factual claim

A proposition fails when it contradicts the evidence excerpt or asserts content not licensed by the closed evidence payload. Reviewers do not search the web and do not rescue a claim with outside knowledge. Absence from the payload is evaluated only for the identified target proposition; the set is not a general truthfulness benchmark.

## Missing boundary

A boundary is required only when it is explicit in the case evidence and changes safety, population, timing, applicability, uncertainty, or the condition under which a recommendation holds. The target span is the under-scoped recommendation. A correction may use any wording that preserves the operative boundary.

## Retention and new claims

Retention atoms are content-level requirements, not mandated prose. Deterministic checks use aliases and regexes; secondary human review can credit a clear paraphrase. A new unsupported claim is an output proposition absent from both the original supported atoms and supplied evidence. It is coded by two independent humans under this closed-world rule, never by an LLM.

## Adjudication

Reviewers first apply case primary checks. Semantic review is secondary and labeled as such. Disagreements are resolved by a third reviewer who sees the evidence, original, output, and both rationales but not condition identity. No reviewer may use the reference correction as the only acceptable wording.
