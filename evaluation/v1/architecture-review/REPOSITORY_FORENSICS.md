# Repository Forensics

## Repository Identity

| Field | Value |
|-------|-------|
| Exact path | `C:\Users\gbx12\projects\CheckMyCoach` |
| Git remote | Single initial commit `07fad80` (2026-07-09) |
| Working tree | Clean (no uncommitted changes at time of inspection) |
| Duplicate | Also mounted as subdirectory at `C:\Users\gbx12\projects\FitCalib-Bench\CheckMyCoach\` (exact copy) |
| Python version | 3.12 (confirmed by `.pyc` cache) |

## File Inventory (46 source files excluding `.git`, `__pycache__`, binaries)

### Core Pipeline (4 files)
| File | Lines | Status |
|------|-------|--------|
| `calibration_agent/m1_detection.py` | 89 | Complete. Rule-based, no LLM dependency |
| `calibration_agent/m2_diagnosis.py` | 146 | Complete. Rule-based, no LLM dependency |
| `calibration_agent/m3_correction.py` | 158 | Complete. LLM (GPT-4o-mini via OpenRouter) + fallback prefix |
| `calibration_agent/m4_validation.py` | 181 | Complete. Rule-based, no LLM dependency |

### Orchestration (3 files)
| File | Lines | Status |
|------|-------|--------|
| `pipeline/agent_pipeline.py` | 423 | Complete. Two entry points: `calibrate()` and `calibrate_full()` |
| `config.py` | 74 | Complete. `@dataclass Settings` with DEV/PROD/TEST presets |
| `schema.py` | 95 | Complete. `CalibrateResult` TypedDict with `NotRequired` fields |

### Evidence Retrieval (3 files)
| File | Lines | Status |
|------|-------|--------|
| `evidence/base.py` | 35 | Complete. `RetrievalBackend` ABC with typed return contract |
| `evidence/retriever.py` | 100 | Complete. `KnowledgeCompilerBackend` uses keyword matching |
| `evidence/__init__.py` | 0 | Present. |

### Tests (5 files)
| File | Tests | Status |
|------|-------|--------|
| `calibration_agent/test_m1_detection.py` | 9 | All pass |
| `calibration_agent/test_m2_diagnosis.py` | 16 | All pass |
| `calibration_agent/test_m3_correction.py` | 9 | All pass (fallback mode, no API key) |
| `calibration_agent/test_m4_validation.py` | 9 | All pass |
| `calibration_agent/e2e_test.py` | 3 scenarios | Manual run (not pytest) |

### Interfaces (3 files)
| File | Lines | Status |
|------|-------|--------|
| `cli.py` | 138 | Complete. `argparse` with `--json`, `--no-audit`, `--model` |
| `server/mcp_server.py` | 142 | Complete. 3 tools: `retrieve`, `calibrate`, `health` |
| `benchmark.py` | 251 | Runs 50 questions, raw vs calibrated UCS comparison |

### Evaluation Artifacts (4 files)
| File | Status |
|------|--------|
| `baseline_comparison.py` | 93 lines. 24-case balanced comparison (6 per UCS category) |
| `baseline_comparison.json` | Results saved from 24-case run |
| `benchmark_results.json` | Results from 50-question benchmark run |
| `multimodel_benchmark.py` | 87 lines. Multi-model comparison scaffold (uses only DeepSeek) |

### Architecture Records (2 files)
| File | Status |
|------|--------|
| `DECISIONS.md` | 7 ADRs covering schema, retriever, dual-path, provider, UCS score, MCP, score_delta |
| `README.md` | Complete. Setup, API, output schema, project structure |

## Dependency Graph

```
calibrate()              calibrate_full()
    |                         |
    v                         v
retriever.py ------> Knowledge Compiler Skill (sys.path insert to acsms12-manifest)
    |                         |
    v                         v
ucs_engine.py <---- sys.path insert to FitCalib-Bench/evaluation/
    |
    v
m1_detection.py (rule-based, pure Python)
    |
    v
m2_diagnosis.py  (rule-based, pure Python)
    |
    v
m3_correction.py (LLM: OpenRouter GPT-4o-mini, fallback prefix)
    |
    v
m4_validation.py (rule-based, pure Python)
    |
    v
audit/trails.jsonl
```

## Cross-Repository Dependencies

| Repository | Path | Interface |
|------------|------|-----------|
| FitCalib-Bench | `C:\Users\gbx12\projects\FitCalib-Bench` | `evaluation/ucs_engine.py` via `sys.path.insert` |
| acsms12-manifest | `C:\Users\gbx12\projects\acsms12-manifest` | `knowledge_compiler.Skill` via `sys.path.insert` |

Both dependencies are loaded via runtime `sys.path.insert()`, not pip-installed.
