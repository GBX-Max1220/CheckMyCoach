# Execution Freeze Report — CheckMyCoach Evaluation v1

**Date:** 2026-07-27
**Status after freeze:** READY FOR SMOKE RUN

---

## 1. Files Changed Since Phase 1

### New files (execution freeze package)
| File | Purpose |
|------|---------|
| `execution/model_config.json` | Frozen model configuration for all three conditions |
| `execution/execution_manifest.json` | SHA-256 hashes of all evaluation artifacts |

### Other new files (Phase 1)
| File | Purpose |
|------|---------|
| `IMPLEMENTATION_FIX_REPORT.md` | Documentation of blocking-defect fixes |
| `PRE_EXECUTION_CHECKLIST.md` | Verification checklist for gate sign-off |

### Modified files (Phase 1)
| File | Change |
|------|--------|
| `runner/generic_correction.py` | Temperature 0.3→0.5; fallback logs model/temp |
| `runner/run_single_case.py` | `collect_case_evidence()`: added `evidence_excerpt`; removed UCS from all conditions; cleaned dry-run messages |
| `runner/run_evaluation.py` | Progress printing: removed UCS references |
| `runner/result.schema.json` | Removed `ucs_score`, `ucs_features` from properties |
| `runner/test_evaluation_runner.py` | 12 new tests (27 total) |

### Files confirmed unchanged
| File | Hash (SHA-256) | Note |
|------|---------------|------|
| `data/cases.jsonl` | `49bb577d...` | Not modified |
| `protocol/EVALUATION_PROTOCOL.md` | `c13b7e76...` | Not modified |
| `protocol/PRIMARY_METRICS.md` | `9ba2b5e4...` | Not modified |
| `protocol/CLAIM_BOUNDARY.md` | `2a4cb219...` | Not modified |
| `protocol/CASE_SCHEMA.json` | `c1b2a941...` | Not modified |
| `protocol/GENERIC_BASELINE_PROMPT.txt` | `dcbcd0d7...` | Not modified |
| `protocol/PROVENANCE_REPORT.md` | `85af0c1f...` | Not modified |
| `runner/input.schema.json` | `f6c71eb1...` | Not modified |

---

## 2. Hashes Created

### Combined artifact hash
```
3726e5874acb6d1611944c43d01cbcde9c6c83799a2053084ce8d101db2a27ee
```

This hash represents the complete evaluation artifact set at freeze time. Any change to any file after this point invalidates the execution.

### Per-file hashes
Recorded in `execution/execution_manifest.json`. Key artifacts:

| Artifact | SHA-256 |
|----------|---------|
| 40 evaluation cases | `49bb577dd65051fc4a9d07dbb0e67cdaa8a3443129f2c3d485555b998b748ed3` |
| Evaluation protocol | `c13b7e7657bfe2cd46317a4509b500a1a3e06549626855f763decc8b43e2ec52` |
| Primary metrics spec | `9ba2b5e4a10d2bdcb09d21c0c634c6f61f68957f2eecd51f84dc3a2e06abab4a` |
| Claim boundary rules | `2a4cb2198c6bc57cb8915d717b8b43c76b96c29ab212e2ab09f19e5d79a39bef` |
| Frozen generic prompt | `dcbcd0d762110266a74770a9b8def271675a6525c3bf3aa9eb78b0be792fa1ba` |
| Run evaluation (batch) | `cd0669a4ec44d9ff23ef1dd28b1d5262c62ac518fa418da4952cf4e07c65a189` |
| Run single case | `828b95cd0e7cdb02fc1bb8d2aa9fae567115ce13f2964e8ebd0e62958686962c` |
| Generic correction | `792ac94ac4693e69e70b405c3c10bf546ce3212f9b6e3916d8dec267d7ad6a26` |
| Model config | `9b24c68715a06c68a41e8a6045698c29f0686441722765818b440fa17e00b2c6` |

---

## 3. Tests Passed

| Test Suite | Count | Result |
|-----------|-------|--------|
| Evaluation runner tests | 27/27 | ✅ ALL PASS |
| M1 detection (pytest) | 9/9 | ✅ ALL PASS |
| M2 diagnosis (pytest) | 16/16 | ✅ ALL PASS |
| M3 correction (pytest) | 9/9 | ✅ ALL PASS |
| M4 validation (pytest) | 9/9 | ✅ ALL PASS |
| **Total** | **68/68** | **✅ ALL PASS** |

### Schema validation
| Check | Result |
|-------|--------|
| result.schema.json: 10 required fields | ✅ PASS |
| result.schema.json: no ucs_score | ✅ PASS |
| result.schema.json: no ucs_features | ✅ PASS |
| result.schema.json: 3 conditions defined | ✅ PASS |
| input.schema.json: no gold fields | ✅ PASS |
| input.schema.json: case_id exists | ✅ PASS |

### Dry-run verification
| Check | Result |
|-------|--------|
| Single case, all 3 conditions | ✅ Three distinct pipelines shown |
| Batch run, 1 sample case | ✅ Discovery + iteration complete |
| No API calls made | ✅ Dry-run flag enforced |
| No UCS in output | ✅ Clean messages |

---

## 4. Model Configuration (Frozen)

| Condition | Provider | Model | Temperature | Tokens |
|-----------|----------|-------|-------------|--------|
| Original generation | DeepSeek API | `deepseek-chat` | 0.3 | 1024 |
| Generic correction | OpenRouter | `openai/gpt-4o-mini` | 0.5 | 1024 |
| CMC M3 correction | OpenRouter | `openai/gpt-4o-mini` | 0.5 | 300 |

Generic and CMC M3 use **identical model and temperature** (`openai/gpt-4o-mini`, 0.5).

---

## 5. Hermes Audit Defect Resolution

| ID | Type | Status | Evidence |
|----|------|--------|----------|
| SD-1 | Wrong prompt | ✅ FIXED | `_load_prompt()` reads from `GENERIC_BASELINE_PROMPT.txt` |
| SD-2 | No evidence | ✅ FIXED | `collect_case_evidence()` supports `evidence_excerpt` |
| SD-3 | LLM baseline | ✅ ACCEPTED | Documented as limitation |
| SD-4 | Pipeline sharing | ✅ ACCEPTED | No Condition D added per scope |
| ID-1 | CMC uses wrong fn | ✅ FIXED | `run_checkmycoach()` calls `calibrate()` |
| ID-2 | Wrong field name | ✅ FIXED | `_get_case_field` supports both formats |
| ID-3 | Hardcoded prompt | ✅ FIXED | Prompt loaded from file with FileNotFoundError |
| ID-4 | No post-UCS | ✅ RESOLVED | UCS removed entirely per protocol |
| MN-1 | retry_count | ✅ RESOLVED | Set to 0 in all records |
| MN-2 | No temp logging | ✅ FIXED | Temperature and model logged in GenericCorrectionResult |
| MN-3 | No preflight | ✅ RESOLVED | Preflight called in `run_batch()` |

---

## 6. Remaining Limitations (Documented)

1. **Evidence path asymmetry.** Generic receives pre-retrieved evidence. CMC retrieves internally. Both use same KC backend.
2. **No raw-LLM condition.** All conditions start from evidence-augmented generation.
3. **Constructed answers.** 40 original_answer fields are hand-authored, not sampled.
4. **Single domain.** Fitness only (ACSM12 + NSCA-CSCS).
5. **Human secondary review.** Protocol requires human reviewers for secondary checks — not yet recruited.
6. **Generic baseline prompt asymmetry.** 18-word prompt vs ~200 words of CMC templates.

---

## 7. What Would Invalidate This Freeze

- Modifying any file in `protocol/`, `runner/`, `data/`, or `execution/`
- Adding new conditions, metrics, or evaluation logic
- Running API calls before the checklist is signed off
- Tuning CheckMyCoach on the 40 evaluation cases

---

## 8. Status

```

┌─────────────────────────────────────┐
│       READY FOR SMOKE RUN          │
│                                     │
│  Next action:                       │
│  1. Complete PRE_EXECUTION_CHECKLIST │
│  2. Obtain Hermes re-audit sign-off │
│  3. One-case API execution          │
│  4. Verify output format/provenance │
└─────────────────────────────────────┘
```
