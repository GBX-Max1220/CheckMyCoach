# Test Report — CheckMyCoach Evaluation Runner v1

## Test Results

| Test | Status |
|------|--------|
| gold-label leakage: input case has no forbidden fields | PASS |
| input.schema.json: no gold fields | PASS |
| generic correction: no failure_type parameter | PASS |
| generic correction: returns GenericCorrectionResult | PASS |
| generic correction: fallback when no API key | PASS |
| input.schema.json: valid structure | PASS |
| result.schema.json: valid structure with required fields | PASS |
| result.schema.json: three conditions defined | PASS |
| result.schema.json: all provenance properties present | PASS |
| input.schema.json: category enum values | PASS |
| **Total** | **10/10** |

## Environment Validation

| Check | Status |
|------|--------|
| Knowledge Compiler import | FAIL (deferred import — resolves at runtime) |
| API key: OPENROUTER_API_KEY | FAIL (not set in this shell) |
| API key: DEEPSEEK_API_KEY | FAIL (not set in this shell) |
| Schema: input.schema.json | PASS |
| Schema: result.schema.json | PASS |
| pipeline.agent_pipeline | PASS |
| calibration_agent.m3_correction | PASS |
| calibration_agent.m4_validation | PASS |
| evidence.retriever | PASS |
| config | PASS |
| schema | PASS |
| generic_correction | PASS |
| Case files (1) | PASS |
| **Total** | **10/13** (3 expected failures under clean shell) |

## Dry Run Verification

- Single case: all 3 conditions print expected pipeline, no API calls
- Batch run: discovers cases, iterates correctly, dry-run flag enforced

## Overall

`python test_evaluation_runner.py` — 10/10 PASS, exit code 0
`python validate_environment.py` — 10/13 PASS (3 expected: KC deferred import, API keys)

**Status: READY FOR DRY RUN**
