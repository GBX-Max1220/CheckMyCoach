# Blockers — CheckMyCoach Evaluation Runner v1

## Identified Blockers: None

All infrastructure is in place for dry-run execution. No system defects prevent
the evaluation runner from functioning.

## Expected Non-Blocking Items

1. **Knowledge Compiler deferred import** — The `evidence/retriever.py` inserts
   the KC path into `sys.path` at module load time. When running from
   `evaluation/v1/runner/`, this path resolution works at actual retrieval time
   (first call to `retrieve()`), not at import time. The validator sees a
   "module not found" but this resolves during actual pipeline execution.

2. **API keys not set in clean shell** — Expected behavior. Keys must be loaded
   via `.env` before execution. The existing `.env` file at
   `C:\Users\gbx12\projects\FitCalib-Bench\.env` contains `OPENROUTER_API_KEY`.

3. **No production case set** — Only 1 sample case exists. The full 40-case set
   must be authored before final evaluation. This is a scientific input task,
   not an engineering blocker.

## Prerequisites Before Full Execution

- [ ] Hermes audit of runner architecture
- [ ] Production case set (40 questions)
- [ ] API key loaded from `.env`
- [ ] Generic correction model selected and funded

## Commands That Work Now

```powershell
# Dry run (no API calls)
cd C:\Users\gbx12\projects\CheckMyCoach
python evaluation/v1/runner/test_evaluation_runner.py
python -m evaluation.v1.runner.run_single_case --case-id CMC-EVAL-0001 --condition all --dry-run
python -m evaluation.v1.runner.run_evaluation --dry-run
```
