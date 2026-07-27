# Execution State Machine

## States

PREFLIGHT -> RUNNING -> COMPLETED
                     -> STOPPED
                     -> ABORTED

### PREFLIGHT
- validate_environment.py runs
- Checks: KC import, API key presence, schema validity, case file integrity
- All preflight checks must pass before any case is processed

### RUNNING
- Cases are processed sequentially
- Each case x condition generates a complete result record
- After each case, a provenance entry is appended (never overwritten)

### COMPLETED
- All cases x all conditions processed successfully
- Final manifest hash computed and saved

### STOPPED
- A non-fatal stop condition was hit (e.g. partial batch failure on some cases)
- All data collected up to the stop point is preserved
- Resume possible with --resume flag

### ABORTED
- A fatal condition: hash mismatch, schema violation, gold-label leak detected
- No further processing
- Raw data preserved up to abort point
