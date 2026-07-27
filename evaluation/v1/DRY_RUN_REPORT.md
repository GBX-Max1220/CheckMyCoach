# Dry Run Report

## Execution
- **Date:** 2026-07-26
- **Command 1:** `python -m evaluation.v1.runner.run_single_case --case-id CMC-EVAL-0001 --condition all --dry-run`
- **Command 2:** `python -m evaluation.v1.runner.run_evaluation --dry-run`
- **No API calls made. No paid model invoked.**

## Results

### Single Case Dry Run (`--condition all`)

| Condition | Pipeline | Status |
|-----------|----------|--------|
| original  | calibrate_full -> UCS score | [DRY RUN] no API calls |
| generic   | calibrate_full -> generic correction prompt | [DRY RUN] no API calls |
| checkmycoach | calibrate_full -> M1 -> M2 -> M3 -> M4 | [DRY RUN] no API calls |

All three conditions print their expected pipeline flow without network access.

### Batch Dry Run

- Cases discovered: 1 (`CMC-EVAL-0001` in `cases/sample/`)
- Conditions: original, generic, checkmycoach
- No API calls logged, no ledger written

## Verification

The runner correctly:
1. Discovers case files from `evaluation/v1/cases/`
2. Iterates cases x conditions
3. Prints pipeline description for each cell
4. Does NOT make any API calls
5. Does NOT write to the ledger when dry-run is active

## Next Steps

To execute for real (requires Hermes audit + API key):
```powershell
cd C:\Users\gbx12\projects\CheckMyCoach
python -m evaluation.v1.runner.run_single_case --case-id CMC-EVAL-0001 --condition original
python -m evaluation.v1.runner.run_evaluation --condition all --limit 5
```
