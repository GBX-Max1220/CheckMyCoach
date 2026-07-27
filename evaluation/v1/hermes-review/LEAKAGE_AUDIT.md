# Leakage Audit — CheckMyCoach Evaluation v1

**Auditor:** Hermes Agent 4 (independent red-team)
**Date:** 2026-07-27

---

## Audit Targets

Verify that CheckMyCoach does NOT receive:

1. Target failure span
2. Reference correction
3. Failure label when detection is being evaluated
4. Evaluator rules (primary/secondary checks)
5. Forbidden claims (for Group B and C cases)
6. Condition-specific hints (which condition this is)

---

## Input Schema Inspection

### `input.schema.json` — Runner's input schema

```json
{
  "properties": {
    "case_id": {"type": "string"},
    "question": {"type": "string"},
    "category": {"type": "string", "enum": [...]},
    "source": {"type": "string"},
    "evidence_text": {"type": "string"},
    "tags": {"type": "array"}
  },
  "required": ["case_id", "question", "category", "source"]
}
```

**Verified absences:**
- `target_failure_span` — NOT present
- `reference_correction` — NOT present
- `failure_family` — NOT present
- `failure_statement` — NOT present
- `content_required_to_change` — NOT present
- `required_boundary` — NOT present
- `forbidden_new_claims` — NOT present
- `primary_checks` — NOT present
- `secondary_checks` — NOT present
- `adjudication_status` — NOT present

**Result: PASS — no forbidden fields in input schema.**

---

## Sample Case Inspection

`cases/sample/CMC-EVAL-0001.json` contains only:
- `case_id`, `question`, `category`, `source`, `tags`, `evidence_text`

**Verified absences:** Same list as above.

**Result: PASS.**

---

## Production Case Data Inspection

`data/cases.jsonl` contains the full gold schema (`CASE_SCHEMA.json`) with
all gold fields. These files are stored in `data/`, not in `cases/`.

### Runner isolation:

| File | Used by runner? | Gold fields present? |
|------|:---:|:---:|
| `cases/sample/*.json` | YES (runner discovers) | NO — sample format |
| `data/cases.jsonl` | NO (runner doesn't read) | YES — but not ingested |
| `data/knowledge-links.jsonl` | NO (runner doesn't read) | Partial |
| `data/reference-corrections.jsonl` | NO (runner doesn't read) | YES |

The runner's `discover_cases()` only reads from `cases/` directory. The
production gold data at `data/cases.jsonl` is never loaded by the runner.

**However**, there is a structural gap: the runner discovers cases with field
name `"question"` but the production schema uses `"input_question"`. This
means even if properly stored, no production case would be discovered.

**Result: PASS (no gold leakage) with a caveat: the isolation is accidental
rather than enforced — the field name mismatch guarantees it.**

---

## Generic Correction Function

`generic_correction.py:correct(original_text)` — receives only the text.

**Verified:**
- No `failure_type` parameter — test `test_generic_no_failure_type` confirms.
- No `target_failure_span` parameter.
- No `failure_family` parameter.
- The function signature is `correct(original_text: str) -> GenericCorrectionResult`.

**Result: PASS — no leakage to generic condition.**

---

## CheckMyCoach Pipeline (M1–M4)

The CMC pipeline receives:
- `question` (from case)
- Retrieved evidence (from KC retriever)
- The pipeline's own generated output

**Verified:**
- M1 receives only UCS score and extraction features — no gold labels.
- M2 receives only UCS score and features — no gold labels.
- M3 receives only M2 diagnosis output — no gold labels, no target span, no reference correction.
- M4 receives only M3 output + original text — no gold labels.

The protocol explicitly states: "No gold labels, no hidden failure type are injected."
The implementation is consistent with this.

**Result: PASS — no leakage in pipeline path.**

---

## Potential Indirect Leakage: KC Object Names

KC object names and IDs include content that could hint at the failure:

- `warning.ballistic_stretching` — "warning" may bias correction toward more caution
- `warning.contraindication_for_exercise_in_extreme_cold` — same

The runner calls the KC retriever which returns these objects. If M3's prompt
includes the retrieved object content, object names containing "warning" could
indirectly hint that a safety boundary is needed.

**Verdict:** Low risk. M3's correction prompt is failure-type-driven, not
object-name-driven. The type-aware prompts already include safety considerations
for `context_mismatch` cases. This is consistent with production behavior and
does not constitute "leakage" in the experimental-design sense.

---

## Leakage from `forbidden_new_claims`

Group B cases populate `forbidden_new_claims` with the same text as the
original answer's failure statement. In the production data:

```python
for row in factual:
    cases.append(case(row[0], B, row[1], *row[2:], forbidden=[row[4]]))
```

Where `row[4]` is the original_answer text. This means `forbidden_new_claims`
contains the exact failure statement.

**But:** This field is in `data/cases.jsonl` only. The runner reads from
`cases/`. Since the runner never ingests `data/cases.jsonl`, this field
cannot leak.

**Result: PASS.**

---

## Verdict

**NO LEAKAGE FOUND.** Gold fields are stored in `data/` and never reach the
runner or any condition. The isolation is maintained by file-level separation
(runner reads `cases/`, gold lives in `data/`). The field name mismatch
(`question` vs `input_question`) accidentally but effectively prevents any
production case with gold fields from being loaded by the runner.
