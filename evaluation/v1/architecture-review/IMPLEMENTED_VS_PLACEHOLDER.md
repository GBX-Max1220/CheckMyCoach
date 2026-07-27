# Implemented vs Placeholder

## Actually Implemented (Runs End-to-End)

| Component | Evidence | Dependencies |
|-----------|----------|--------------|
| CLI `python cli.py "question"` | `cli.py` — argparse, calls `calibrate_full()` | DeepSeek/OpenRouter API key |
| M1 Detection | `m1_detection.py` — rule-based, 9 passing tests | None |
| M2 Diagnosis | `m2_diagnosis.py` — rule-based, 16 passing tests | None |
| M3 Correction (fallback) | `m3_correction.py` — 9 tests pass in fallback mode | No API key needed for fallback |
| M4 Validation | `m4_validation.py` — 4 rule checks, 9 passing tests | None |
| Evidence Retrieval | `evidence/retriever.py` — keyword match on KC, verified working (5/5 results) | acsms12-manifest on disk |
| MCP Server (stdio) | `server/mcp_server.py` — 3 tools registered | Python `mcp` package |
| Pipeline Orchestration | `pipeline/agent_pipeline.py` — both paths | All of the above |
| Audit JSONL | `_write_audit()` in `agent_pipeline.py` | File system write access |
| 50-question Benchmark | `benchmark.py` — ran previously, results in `benchmark_results.json` | Full API access |
| 24-case Baseline | `baseline_comparison.py` — ran previously, results in `baseline_comparison.json` | Full API access |

## Implemented but Unconnected

| Component | Where | Why Unconnected |
|-----------|-------|-----------------|
| `multimodel_benchmark.py` | Root | Calls DeepSeek only; model switch is config change but no multi-model results are integrated into the pipeline |
| `batch_dogfood.py` | Root | Standalone script, not part of pipeline or any test runner |
| UCS Engine Stage 4 (LLM judge) | `FitCalib-Bench/evaluation/ucs_engine.py` | Implemented but only fires on extraction JSON parse failure; the default path is deterministic (Stage 1-3) |
| HCI fields in schema | `schema.py` lines 88-93 | `pre_trust_score`, `decision_change`, `user_profile` — TypedDict fields exist but never populated by any code path |

## Placeholders (Stubs / Not Yet Implemented)

| Component | File | Line Ref | Current Behaviour |
|-----------|------|----------|-------------------|
| Conversation history | `agent_pipeline.py` `calibrate()` | L134 | `history` parameter accepted but ignored; docstring says "预留，当前未实现" |
| Metadata passthrough | `agent_pipeline.py` `calibrate()` | L136 | `metadata` parameter accepted but ignored |
| Evidence per-case evaluation | `evidence/retriever.py` | L42-74 | Keyword matching only; embedding reserved for "Phase 1.5" per ADR-002 |
| Multi-backend retriever | `evidence/base.py` | L17-32 | ABC exists, but only `KnowledgeCompilerBackend` is implemented |
| Dogfood audit trails | `audit/dogfood_trails.jsonl` | N/A | File exists with 0 entries |
| `e2e_screening.py` | `calibration_agent/e2e_screening.py` | N/A | Exists but not inspected — not a regular test file |
| `NSCA` objects in retriever | `evidence/retriever.py` | L33 | Book path defaults to `books/acsm12` only; NSCA (`books/nsca-cscs`) not configured |

## What Is MOCK vs Real in Tests

| Test File | Test Name | MOCK/Real | Evidence |
|-----------|-----------|-----------|----------|
| `test_m1_detection.py` | All 9 tests | **Real** | Pure functions, no external calls |
| `test_m2_diagnosis.py` | All 16 tests | **Real** | Pure functions, no external calls |
| `test_m3_correction.py` | `test_template_dominance_correction` | **Fallback** | No OPENROUTER_API_KEY → triggers `_call_llm` → returns None → fallback prefix |
| `test_m3_correction.py` | `test_cue_leakage_correction` | **Fallback** | Same |
| `test_m3_correction.py` | `test_context_mismatch_correction` | **Fallback** | Same |
| `test_m3_correction.py` | Remaining 6 tests | **Real** | Test schema/template structure, no LLM call |
| `test_m4_validation.py` | All 9 tests | **Real** | Pure functions, no external calls |
| `e2e_test.py` | Manual run | **Real M1/M2/M4, Fallback M3** | M1/M2/M4 rule-based; M3 hits fallback in CI |

**Key finding**: All 41 pytest tests pass without any API key. M3 tests gracefully fall back to prefix mode. No test requires network access.
