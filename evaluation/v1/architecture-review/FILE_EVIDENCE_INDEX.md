# File Evidence Index

Every claim in the architecture review documents is backed by a specific file and line number. This index lists the evidence files, what they prove, and which document references them.

## Pipeline Implementation Evidence

| Claim | File | Lines | Referenced In |
|-------|------|-------|---------------|
| M1 is rule-based, no LLM | `calibration_agent/m1_detection.py` | 36-66 | FORENSICS, PIPELINE_MAP, DO_NOT_TOUCH |
| M2 is rule-based, 3 failure types | `calibration_agent/m2_diagnosis.py` | 43-115 | FORENSICS, PIPELINE_MAP |
| M3 uses LLM + fallback prefix | `calibration_agent/m3_correction.py` | 106-157 | FORENSICS, PIPELINE_MAP, RISK_R2 |
| M4 has 4 rule checks | `calibration_agent/m4_validation.py` | 99-180 | FORENSICS, PIPELINE_MAP, DO_NOT_TOUCH |
| Pipeline has 2 entry points | `pipeline/agent_pipeline.py` | 130-282 (calibrate), 283-377 (calibrate_full) | FORENSICS, PIPELINE_MAP |
| TypedDict schema with NotRequired | `schema.py` | 36-94 | FORENSICS, DO_NOT_TOUCH |
| sys.path inserts to FitCalib-Bench | `pipeline/agent_pipeline.py` | 32, 39, 46, 53, 60 | RISK_R6 |
| UCS score 0-3 (not semantic) | `schema.py` | 66-68, plus DECISIONS.md ADR-005 | PIPELINE_MAP |

## Retriever Evidence

| Claim | File | Lines | Referenced In |
|-------|------|-------|---------------|
| Retriever uses keyword matching | `evidence/retriever.py` | 42-74 | FORENSICS, RISK_R1 |
| RetrievalBackend ABC | `evidence/base.py` | 14-35 | FORENSICS, DO_NOT_TOUCH |
| Book path defaults to acsm12 | `evidence/retriever.py` | 33 | RISK_R7 |
| KC Skill uses dict lookup | `acsms12-manifest/knowledge_compiler/skill.py` | 58-95 | FORENSICS |
| KC registry: 695 entries | Verified at runtime | N/A | FORENSICS |
| KC index: 707 objects | Verified at runtime | N/A | FORENSICS |
| Retriever returns 5 results | Verified at runtime: "protein intake" → 5 results | N/A | FORENSICS, RISK_R1 |

## Test Evidence

| Claim | File | Lines | Referenced In |
|-------|------|-------|---------------|
| 41 tests pass (no API key) | Run `pytest calibration_agent/ -v` | All | FORENSICS, PLACEHOLDER |
| M1: 9 tests | `calibration_agent/test_m1_detection.py` | 1-82 | PLACEHOLDER |
| M2: 16 tests | `calibration_agent/test_m2_diagnosis.py` | 1-193 | PLACEHOLDER |
| M3: 9 tests (fallback mode) | `calibration_agent/test_m3_correction.py` | 1-121 | PLACEHOLDER |
| M4: 9 tests | `calibration_agent/test_m4_validation.py` | 1-109 | PLACEHOLDER |
| E2E: 3 scenarios (manual) | `calibration_agent/e2e_test.py` | 1-173 | PLACEHOLDER |

## Configuration Evidence

| Claim | File | Lines | Referenced In |
|-------|------|-------|---------------|
| Only OPENROUTER_API_KEY in .env | `.env` | 1 | RISK_R2 |
| Settings: model, temperature, paths | `config.py` | 23-56 | DO_NOT_TOUCH |
| DEV/PROD/TEST presets | `config.py` | 59-73 | FORENSICS |

## Architecture Decision Evidence

| Claim | File | Lines | Referenced In |
|-------|------|-------|---------------|
| ADR-001: TypedDict chosen | `DECISIONS.md` | 8-24 | FORENSICS |
| ADR-002: keyword retriever | `DECISIONS.md` | 27-43 | PLACEHOLDER, RISK_R1 |
| ADR-003: dual-path API | `DECISIONS.md` | 46-64 | PIPELINE_MAP |
| ADR-005: UCS int 0-3 | `DECISIONS.md` | 81-90 | PIPELINE_MAP |
| ADR-007: score_delta approximate | `DECISIONS.md` | 104-113 | PIPELINE_MAP |
| HCI fields as placeholder | `schema.py` | 88-93 | PLACEHOLDER |
| history/metadata as placeholder | `pipeline/agent_pipeline.py` | 134, 136 | PLACEHOLDER |

## Evaluation Artifact Evidence

| Claim | File | Lines | Referenced In |
|-------|------|-------|---------------|
| 50-question benchmark results | `benchmark_results.json` | Full | FORENSICS |
| 24-case baseline comparison | `baseline_comparison.json` | Full | DO_NOT_TOUCH |
| Benchmark runner | `benchmark.py` | 1-251 | IMPLEMENTED |
| Baseline comparison runner | `baseline_comparison.py` | 1-93 | IMPLEMENTED |

## UCS Engine Evidence

| Claim | File | Lines | Referenced In |
|-------|------|-------|---------------|
| 4-stage architecture | `FitCalib-Bench/evaluation/ucs_engine.py` | 1-120+ | DO_NOT_TOUCH |
| Stage 1: regex patterns | Same file | 33-100+ | PATCH_PLAN |
| Stage 4: LLM judge fallback | Same file | Not fully read — mentioned | RISK_R5 |

## Repository Structure Evidence

| Claim | File | Referenced In |
|-------|------|---------------|
| 46 source files (excl. caches) | Full `find` listing | FORENSICS |
| 41 pass on pytest | `pytest calibration_agent/ -v` output | PLACEHOLDER |
| Duplicate at FitCalib-Bench/CheckMyCoach | `ls FitCalib-Bench/CheckMyCoach/` | FORENSICS |
| Single initial commit | `git log --oneline` | FORENSICS |
