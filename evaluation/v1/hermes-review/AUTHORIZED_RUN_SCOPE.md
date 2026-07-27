# Authorized Run Scope — CheckMyCoach Evaluation v1

**Gatekeeper:** Hermes Agent 4 (independent red-team)
**Date:** 2026-07-27

---

## Current Status: NO EXECUTION AUTHORIZED

The evaluation runner is **not** ready for any execution — not a dry run, not
a one-case run, not a full 40-case execution.

---

## Why No Run Is Authorized

A dry run would not detect the **critical implementation defects** because
the dry run only prints pipeline descriptions without making API calls or
running M1-M4. The defects are in the function-call chain, not in the CLI
interface.

Specifically:
1. `run_checkmycoach` calls `calibrate_full()` instead of `calibrate()` — the dry run prints "calibrate_full -> M1 -> M2 -> M3 -> M4" but the actual code path never reaches M1-M4.
2. `discover_cases()` would find 0 production cases — but in a dry run with the sample case (which uses `"question"` format, not `"input_question"`), it would find exactly 1 case and appear to work.
3. The generic correction prompt is wrong — dry run doesn't exercise the prompt.

A dry run today would:
- Print the correct pipeline descriptions
- Find the sample case
- Print 3 dry-run lines
- Report "success"
- Mask every blocking defect

---

## Requirements Before Any Run

### Prerequisite: Fix Blocking Defects

All 8 blocking defects (see `BLOCKING_DEFECTS.md`) must be fixed before
any execution.

### Then: Authorized One-Case Dry Run

After fixing all defects, the authorized scope is:

| Property | Value |
|----------|-------|
| **Scope** | ONE case |
| **Case** | Any single case from the 40-case set (not the sample) |
| **Conditions** | All three (original, generic, checkmycoach) |
| **Run type** | Actual API execution (not dry run) |
| **Result interpretation** | No broader conclusions |
| **Output** | Verify runner output format, provenance, scores |

---

### Then: Final Gate for Full Evaluation

After the one-case dry run completes with verified outputs, a separate
final gate review is required before full 40-case execution. The final gate
must verify:

1. All 8 blocking defects are resolved
2. The one-case dry run produced correct outputs (all CMC trace fields populated, not None)
3. The generic correction uses the protocol-specified prompt
4. The generic correction receives question + evidence
5. All three conditions produce different outputs (the CMC condition differs from original)
6. Provenance records are complete
7. Pipeline completion is logged

---

## Conditions Not Authorized

| Request | Status |
|---------|:------:|
| Full 40-case execution | NOT AUTHORIZED (see above) |
| Tuning CheckMyCoach on these cases | EXPLICITLY PROHIBITED (protocol Section 1) |
| Public benchmark release | EXPLICITLY PROHIBITED (protocol Section 1) |
| Model claims about failure prevalence | NOT SUPPORTED by 40 constructed cases |
| Human subject claims | OUT OF SCOPE |
| LLM-as-judge scoring | EXPLICITLY PROHIBITED (protocol Section 4) |
| Composite headline score | EXPLICITLY PROHIBITED (protocol Section 5) |
