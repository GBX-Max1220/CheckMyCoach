# CheckMyCoach

> Engineering prototype that routes selected outputs, assigns rule-based tags, generates candidate revisions, and runs deterministic surface checks.

**Pipeline:** Retrieved records (Knowledge Compiler) → LLM → historical UCS heuristic → M1-M4 → Audit

The module names and UCS fields are implementation interfaces, not validated detection, diagnosis, repair, confidence, or calibration measures.

---

## Architecture

```
                User
                  |
                  v
              CLI / MCP
                  |
                  v
         Agent Orchestrator
          +-------------+
          v             v
    Retriever        LLM Client
    (KC Backend)   (deepseek-chat)
          |             |
          +------+------+
                 |
                 v
         Calibration Engine
         (M1 -> M2 -> M3 -> M4)
                 |
                 v
           Audit Logger
           (JSONL)
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/GBX-Max1220/FitCalib-Bench.git
cd FitCalib-Bench/CheckMyCoach

# 2. Install dependencies
pip install pyyaml requests python-dotenv mcp

# 3. Set API key
#    (edit .env or set env vars)
echo "DEEPSEEK_API_KEY=sk-..." > .env

# 4. Run
python cli.py "Should I squat below parallel?"

# 5. JSON output (pipeable to jq)
python cli.py "Should I squat below parallel?" --json
```

## API

### CLI

```bash
python cli.py "question"           # Pretty print
python cli.py "question" --json    # JSON (pipe to jq)
python cli.py "question" --no-audit # Skip audit log
```

### Python

```python
from pipeline.agent_pipeline import calibrate, calibrate_full

# Path A: calibrate existing response
result = calibrate(response="...", question="Should I squat below parallel?")

# Path B: full pipeline (demo-friendly)
result = calibrate_full(question="Should I squat below parallel?")

print(result["ucs_score"])       # int 0-3
print(result["failure_type"])    # "CUE_LEAKAGE" | None
print(result["corrected_response"])  # candidate revision, if generated
```

### MCP

```bash
# Start MCP server
python -m server.mcp_server

# Then connect from any MCP client (Claude Desktop, Cursor, etc.)
# Tools: retrieve(question), calibrate(question), health()
```

## Output Schema

See `schema.py` for the full `CalibrateResult` TypedDict.

Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Pipeline completed normally |
| `ucs_score` | int | 0-3 (not semantic label) |
| `needs_calibration` | bool | Whether the historical M1 routing heuristic flagged it |
| `failure_type` | str or null | Rule tag: TEMPLATE_DOMINANCE / CUE_LEAKAGE / CONTEXT_MISMATCH |
| `score_delta` | float or null | Internal UCS-heuristic delta; not a validated calibration outcome |
| `latency_ms` | dict | Per-step latency |
| `evidence` | list | Retrieved Knowledge Compiler records; presence does not establish source support or scientific validity |

## Project Structure

```
CheckMyCoach/
├── config.py                   # @dataclass Settings
├── schema.py                   # TypedDict definitions
├── cli.py                      # CLI entry point
├── pipeline/
│   └── agent_pipeline.py       # calibrate() + calibrate_full()
├── evidence/
│   ├── base.py                 # RetrievalBackend (ABC)
│   └── retriever.py            # KnowledgeCompilerBackend
├── audit/
│   └── trail.py                # JSONL audit logger
├── server/
│   └── mcp_server.py           # MCP stdio (3 tools)
├── calibration_agent/          # M1-M4 (existing, unchanged)
├── DECISIONS.md                # Architecture Decision Record
└── path_a_plan.md              # Development plan
```

## Dependencies

- **Runtime:** pyyaml, requests, python-dotenv, mcp
- **Knowledge Base:** [acsms12-manifest](https://github.com/GBX-Max1220/knowledge-compiler) (2,305 historical files; 2,294 unique IDs; partial provenance recovery)
- **LLM:** DeepSeek Chat (api.deepseek.com) or OpenRouter

## Related

- [MaxFitCalib-Bench](https://github.com/GBX-Max1220/FitCalib-Bench) — UCS evaluation framework and 126-question benchmark
- [Knowledge Compiler](https://github.com/GBX-Max1220/knowledge-compiler) — Structured knowledge from textbooks
- [CalTrust](https://github.com/GBX-Max1220/FitCalib-Bench/tree/main/CalTrust) — Adaptive trust-calibrated agent (Streamlit UI)

## Citation

```bibtex
@software{guo_checkmycoach_2026,
  author = {Guo, Max},
  title = {CheckMyCoach: Calibration Agent Pipeline for AI Fitness Advice},
  year = {2026},
  url = {https://github.com/GBX-Max1220/FitCalib-Bench}
}
```
