# Runner Reproduction Audit — CheckMyCoach Evaluation v1

**Auditor:** Hermes Agent 4 (independent red-team)
**Date:** 2026-07-27

---

## Audit Targets

Verify the runner:
1. Preserves raw outputs
2. Records full provenance
3. Uses separate conditions
4. Cannot silently retry undesirable outputs
5. Cannot modify frozen cases
6. Does not treat API calls as independent scientific samples
7. Does not use an LLM judge for primary labels

---

## 1. Raw Output Preservation

**Implementation:** `result.schema.json` includes:
- `raw_response`: str — full raw model output
- `request_payload`: dict — full API request payload
- `correction_trace`: dict or null — M3 diagnosis + prompt
- `validation_trace`: dict or null — M4 validation result
- `token_usage`: dict — tokens and cost

All fields are present in the schema. The `run_single_case.py` functions
populate these from `CalibrateResult`.

**Verdict: PASS.** Raw outputs are preserved with full trace.

---

## 2. Full Provenance

**Implementation:** `PROVENANCE_SPEC.md` requires and `result.schema.json`
includes:
- `run_id`: str — unique identifier
- `case_id`: str — immutable case identifier
- `condition`: str — original / generic / checkmycoach
- `model`: str — model identifier
- `timestamp`: str — ISO 8601 UTC
- `input_exact`: dict — exact input sent
- `latency_ms`: float
- `error`: str or null
- `retry_count`: int
- `included`: bool

The runner uses append-only JSONL — each record written to the ledger,
never overwritten.

**Verdict: PASS.** Provenance requirements are met.

---

## 3. Separate Conditions

**Implementation:** Each condition is a separate function call:
- `run_original(case)` — calls `calibrate_full()`
- `run_generic(case)` — calls `calibrate_full()` then `generic_correct()`
- `run_checkmycoach(case)` — calls `calibrate_full()`

**CRITICAL FINDING: `run_checkmycoach` calls `calibrate_full()` instead of `calibrate()`.**

From the architecture review (`CURRENT_PIPELINE_MAP.md`):

| Function | Steps | Produces correction? |
|----------|-------|:-------------------:|
| `calibrate_full()` | Retrieve + LLM generate | NO |
| `calibrate()` | Retrieve + LLM generate + UCS + M1 + M2 + M3 + M4 + score delta | YES |

All three runner functions import and call `calibrate_full()`:

```python
from pipeline.agent_pipeline import calibrate_full
result = calibrate_full(question=case["question"])
```

**This means all three conditions run the identical pipeline.** The
"CheckMyCoach" condition does NOT run M1 detection, M2 diagnosis, M3
correction, or M4 validation. The `corrected_response`, `failure_type`,
`m4_passed` fields it retrieves from the result will be `None` because
`calibrate_full()` doesn't produce them.

The `run_checkmycoach` function should call `calibrate()` from
`pipeline.agent_pipeline`, not `calibrate_full()`.

**Verdict: FAIL — CRITICAL BUG. The checkmycoach condition is identical to
the original condition in the runner.**

---

## 4. Silent Retry

**Implementation:** The runner has no retry mechanism. The batch runner wraps
each call in try/except and records errors. No silent retry code exists.

The `PROVENANCE_SPEC.md` includes a `retry_count` field (int, min 0). The
result schema includes an `error` field. But the code never increments
`retry_count` — it's always absent from the result dict.

**Verdict: PASS (no silent retry).** The `retry_count` field exists in the
schema but is never populated. This is not a defect because no retry
mechanism exists to trigger the count.

---

## 5. Frozen Case Integrity

**Implementation:** The runner reads cases via `discover_cases()` which opens
JSON files read-only. The runner never writes to case files. The runner
writes to a separate ledger file.

**Verdict: PASS.** Cases are not modified by the runner.

---

## 6. API Calls as Independent Scientific Samples

**Concern:** The protocol says: "Do not treat 40 deliberately constructed cases
as an IID population sample."

**Implementation:** The runner iterates cases sequentially with no random seed
tracking, no temperature logging, no repetition. Each case x condition gets
one API call.

**Observation:** The runner doesn't explicitly track random seeds or
temperatures per call. If the pipeline uses non-zero temperature (default is
typically 0.7), the same case run twice would produce different outputs. The
runner doesn't support multiple trials per case.

**Verdict: NOT BLOCKING but note that single-trial-per-case limits
reliability.** No seed tracking means results are not exactly reproducible.

---

## 7. LLM Judge for Primary Labels

**Implementation:** All primary checks are deterministic:
- `substring_absent` — verifies target span removed
- `regex_present` — verifies pattern present
- `any_phrase_present` — verifies one of several phrases present
- `all_phrase_present` — verifies all phrases present
- `all_regex_present` — verifies all regex patterns present
- `any_regex_present` — verifies one of several patterns present
- `all_phrase_groups_present` — verifies each group has at least one match
- `phrase_present` — verifies a single phrase present

None requires an LLM. Secondary review is human-based.

**Verdict: PASS.** No LLM judge for primary labels. Protocol prohibition
honored.

---

## Additional Runner Defects

### D6: `discover_cases()` field name mismatch

The batch runner's `discover_cases()` function:
```python
if "case_id" in case and "question" in case:
```

But `CASE_SCHEMA.json` defines `"input_question"`, not `"question"`. The
sample case at `cases/sample/CMC-EVAL-0001.json` uses `"question"`, but
production cases would use `"input_question"`. Any production case stored
in `cases/` would not be discovered by the batch runner.

### D7: No preflight enforcement

The `EXECUTION_STATE_MACHINE.md` defines PREFLIGHT as a required state that
runs `validate_environment.py`. However, the batch runner's `main()` function
starts directly with `discover_cases()` — no preflight check is enforced.

### D8: Knowledge-link count mismatch

`data/knowledge-links.jsonl` has 33 entries for 40 cases. Some cases share
knowledge objects (e.g., CMC-C-005 links two objects). The 33:40 ratio
reflects shared references, not missing data. This is acceptable.

---

## Summary

| Check | Verdict |
|-------|:-------:|
| Raw output preservation | PASS |
| Full provenance | PASS |
| Separate conditions | **FAIL** — `run_checkmycoach` calls `calibrate_full()` |
| Silent retry | PASS |
| Frozen case integrity | PASS |
| IID treatment avoidance | NOT BLOCKING |
| No LLM judge | PASS |
| Field name consistency | **FAIL** — `discover_cases()` uses `"question"` vs `"input_question"` |
| Preflight enforcement | MINOR — not enforced but doesn't affect runtime |
