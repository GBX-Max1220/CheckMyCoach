# CheckMyCoach Path A — 执行计划 v3（第二轮三方审后）

> **版本说明：** v3 是在 v2 基础上，吸收了 ChatGPT 第二轮 (9.6/10)、Claude Code 第二轮、Coze 第二轮的审查意见后的最终版。
> 变更摘要见 `changelog_v2_to_v3.md`。

---

## 现状（已完成的）

| 组件 | 状态 | 位置 |
|------|------|------|
| M1 Detection | ✅ 10 tests | `CheckMyCoach/calibration_agent/m1_detection.py` |
| M2 Diagnosis | ✅ 14 tests | `CheckMyCoach/calibration_agent/m2_diagnosis.py` |
| M3 Correction | ✅ 9 tests | `CheckMyCoach/calibration_agent/m3_correction.py` |
| M4 Validation | ✅ 8 tests | `CheckMyCoach/calibration_agent/m4_validation.py` |
| E2E Pipeline (M1→M4) | ✅ 3 samples | `CheckMyCoach/calibration_agent/e2e_test.py` |
| UCS Engine (输出 int 0-3) | ✅ | `FitCalib-Bench/evaluation/ucs_engine.py` |
| Knowledge Compiler (2305 对象 + Skill API) | ✅ 可 pip install | `acsms12-manifest/` |
| CalTrust (Streamlit UI + XGBoost + Orchestrator) | ✅ 已构建 | `CalTrust/` |
| arXiv preprint | ✅ 已提交等 ID | MaxFitCalib-Bench |

不阻塞工程：盲评 ⏳1/5 回 · IRB ⏳ 待批 · 论文 Discussion ⏳ 待数据

---

## 目标

```
python -m checkmycoach "Should I squat below parallel?"
```

→ 一条命令，输出完整校准报告（含证据来源 · UCS 评分 · 校准结果 · 审计追踪）。

---

## Phase 0: 依赖验证（Day 1, 前 30 分钟）

**在写任何代码之前，先跑 smoke test。**

```bash
# 1a. 安装 Knowledge Compiler（优先 pip install -e）
pip install -e C:\Users\gbx12\projects\acsms12-manifest

# 1b. 如果失败 → fallback：仅装 pyyaml，用 sys.path 导入
#     pip install pyyaml
#     代码里加 sys.path.insert(0, r'...\acsms12-manifest')
#     （CalTrust 同款模式）

# 2. 验证 KC 检索能力（确认 Skill.resolve 是 exact match）
python -c "
from knowledge_compiler import Skill
s = Skill('books/acsm12')
# exact match 验证
assert s.resolve('Squat Test') == 'table_row.squat_test', 'exact match failed'
# 关键词遍历验证
matches = [name for name in s.registry if 'squat' in name.lower()]
print(f'keyword matches for squat: {matches}')
print('KC OK:', s.list_types())
"

# 3. 验证 UCS Engine 可 import
python -c "
import sys; sys.path.insert(0, r'C:\Users\gbx12\projects\FitCalib-Bench')
from evaluation.ucs_engine import evaluate_ucs, UCSResult
print('UCS OK, returns:', UCSResult.__dataclass_fields__['ucs_score'].type)
"

# 4. 验证 M1-M4 可 import
python -c "
import sys; sys.path.insert(0, r'C:\Users\gbx12\projects\FitCalib-Bench\CheckMyCoach')
from calibration_agent.m1_detection import needs_calibration
from calibration_agent.m2_diagnosis import diagnose
from calibration_agent.m3_correction import correct
from calibration_agent.m4_validation import validate
print('M1-M4 OK')
"

# 5. 确认 DeepSeek API key + 模型名
python -c "
from dotenv import load_dotenv; import os
load_dotenv(r'C:\Users\gbx12\projects\FitCalib-Bench\CheckMyCoach\.env')
print('Has DeepSeek key:', bool(os.getenv('DEEPSEEK_API_KEY')))
print('Has OpenRouter key:', bool(os.getenv('OPENROUTER_API_KEY')))
# 确认模型名：已有代码用 deepseek-chat（直连 api.deepseek.com）
# 如果走 OpenRouter，slug 格式为 deepseek/deepseek-chat
"

# 6. 确认 mcp SDK 版本
pip show mcp
```

**通过标准：** 全部 6 步无报错 + 有 API key。

---

## Phase 1: Agent Pipeline（Day 1 剩余 + Day 2）

### 1.1 config.py

```python
from dataclasses import dataclass

@dataclass
class Settings:
    model: str = "deepseek-chat"               # 直连 api.deepseek.com
    temperature: float = 0.3
    top_k: int = 5
    audit_path: str = "audit/trails.jsonl"
    log_path: str = "audit/logs.log"
    api_provider: str = "deepseek"              # "deepseek" | "openrouter"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    kc_book_path: str = "books/acsm12"

# 预设配置
DEV = Settings()
PROD = Settings(model="deepseek-reasoner", temperature=0.1)
TEST = Settings(audit_path="audit/test_trails.jsonl")
```

### 1.2 Evidence Retriever（含 Backend 抽象）

```python
from abc import ABC, abstractmethod
from knowledge_compiler import Skill

class RetrievalBackend(ABC):
    """抽象后端：为多数据源预留（ChatGPT 建议）"""
    @abstractmethod
    def search(self, query: str, top_k: int) -> list[dict]: ...

class KnowledgeCompilerBackend(RetrievalBackend):
    """KC 后端 — 第一版：遍历 registry 做关键词匹配"""
    def __init__(self, book_path: str = "books/acsm12"):
        # book_path 解析：如果 pip install 了，相对 KC 项目根
        # 如果 sys.path fallback，需转绝对路径
        self.skill = Skill(book_path)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        # KC Skill 不支持关键词搜索（resolve/get 都是 exact match）
        # 所以遍历 registry 做字符串匹配
        keywords = query.lower().split()
        matches = []
        for name, oid in self.skill.registry.items():
            if any(kw in name.lower() or kw in oid.lower() for kw in keywords):
                obj = self.skill.get(name)
                matches.append({
                    "id": oid,
                    "type": oid.split(".")[0],
                    "canonical_name": name,
                    "content": obj.get("definition", "")[:200],
                    "source": f"ACSM12 ({name})",
                })
        return matches[:top_k]

class EvidenceRetriever:
    def __init__(self, backend: RetrievalBackend | None = None):
        self.backend = backend or KnowledgeCompilerBackend()

    def retrieve(self, question: str, top_k: int = 5) -> list[dict]:
        return self.backend.search(question, top_k=top_k)
```

### 1.3 Schema（TypedDict，固定结果格式）

**文件：** `CheckMyCoach/schema.py`

```python
from typing import TypedDict, NotRequired

class TokenUsage(TypedDict, total=False):
    prompt_tokens: int
    completion_tokens: int
    cost: float          # USD

class CalibrateResult(TypedDict, total=False):
    success: bool
    audit_id: str
    question: str

    # evidence
    evidence: list[dict]

    # 原始结果
    response: str
    ucs_score: int                # 0-3，不是语义标签
    extraction_features: dict

    # 校准结果
    needs_calibration: bool
    failure_type: str | None      # TEMPLATE_DOMINANCE | CUE_LEAKAGE | CONTEXT_MISMATCH | None
    corrected_response: str | None
    score_delta: float | None     # ⚠️ 近似值：UCS LLM 分支非确定性，不充当论文定量指标
    m4_passed: bool

    # 审计
    latency_ms: dict
    token_usage: TokenUsage

    # 错误
    error: str | None             # 统一错误码

    # HCI 扩展字段（schema 兼容占位，不要求填）
    pre_trust_score: NotRequired[float | None]
    decision_change: NotRequired[bool | None]
    user_profile: NotRequired[dict | None]
```

### 1.4 Agent Pipeline

**文件：** `CheckMyCoach/pipeline/agent_pipeline.py`

```python
# 路径 A：校准已有回答
def calibrate(question: str,
              response: str,
              context: list[dict] | None = None,
              history: list[dict] | None = None,
              metadata: dict | None = None) -> CalibrateResult:
    """
    1. 检索证据（如果有 context 则跳过）
    2. UCS Engine 评分 → extraction features
    3. M1 Detection → 是否需校准
    4. M2 Diagnosis → 失败类型
    5. M3 Correction → 校准
    6. M4 Validation → 通过/回退
    7. 再次 UCS 评分 → score_delta（近似值）
    8. Audit 记录
    """
    ...

# 路径 B：全自动（demo 友好）
def calibrate_full(question: str,
                   context: list[dict] | None = None,
                   history: list[dict] | None = None,
                   metadata: dict | None = None) -> CalibrateResult:
    """
    calibrate() 的 wrapper：
    0. 检索证据 → LLM(deepseek-chat) → 生成回答 → 然后走 calibrate()
    """
    ...
```

**非正常路径处理**（每步 try-except）：

| 节点 | 失败模式 | 降级策略 |
|------|---------|---------|
| Retriever | 空结果 / 异常 | 跳过证据，直接调 LLM |
| LLM | API 超时 / 限流 | 重试 1 次 → `success: false, error: "LLM_TIMEOUT"` |
| UCS Engine | 非预期值 | 记录 warning，降级到 score=1 |
| M1-M4 | 异常 | 记录异常，跳过校准，返回原始回答 |
| Audit | 写入失败 | stderr warning，不影响主流程 |

### 1.5 Audit Trail

**文件：** `CheckMyCoach/audit/trail.py`

JSONL 每行记录（与 `CalibrateResult` schema 一致，UCS **全部用 int 0-3**）：

```python
{
  "audit_id": "cmc_20260705_170000_abc123",
  "timestamp": "2026-07-05T17:00:00Z",
  "path": "calibrate",
  "question": "Should I squat below parallel?",
  "evidence_ids": ["table_row.squat_test", "concept.squat_technique"],
  "response": "Yes, full depth squats are safe...",
  "ucs_score": 1,                          # int 0-3，不是语义标签
  "extraction_features": {"claims_superiority": true, ...},
  "m1_decision": "calibrate",
  "m2_failure_type": "CUE_LEAKAGE",
  "m2_confidence": 0.85,
  "m3_corrected": "Squatting to parallel may be safe...",
  "m4_passed": true,
  "score_delta": 1.5,        # ⚠️ 注释：近似值，UCS 有测量噪声
  "latency_ms": {
    "retriever": 340, "llm": 2100, "ucs_engine": 45,
    "m1": 2, "m2": 5, "m3": 1200, "m4": 3, "total": 3695
  },
  "token_usage": {
    "prompt_tokens": 450, "completion_tokens": 120, "cost": 0.0003
  },
  "pre_trust_score": null,     # HCI 字段占位
  "decision_change": null,
  "user_profile": null
}
```

### 1.6 test_samples（3 条新 pipeline 级样本）

不复用 `e2e_test.py`（那是为 M1-M4 设计的，从已有回答开始）。准备 3 条从 question 开始的全链路样本：

1. **需要校准的**（如模糊建议 "You should definitely squat to parallel"）
2. **不需要校准的**（如精确建议 "ACSM recommends 150 min/week moderate exercise"）
3. **KC 检索不到证据的**（如 "What is the best quantum computing algorithm" — 超出 fitness 领域）

---

## Phase 2: CLI（Day 2 下午）

**文件：** `CheckMyCoach/cli.py`

```bash
python -m checkmycoach "Should I squat below parallel?"          # 默认 pretty print
python -m checkmycoach "Should I squat below parallel?" --json    # JSON → 可 pipe 到 jq
python -m checkmycoach "Should I squat below parallel?" --no-audit # 不写 audit（调试用）
```

输出统一：`{success, result, error, audit_id}` 格式。

---

## Phase 3: MCP Server（Day 3）

**文件：** `CheckMyCoach/server/mcp_server.py`

用 `mcp==<当前稳定版>` SDK，暴露 3 个 tool：

```
retrieve(question: str) → list[dict]    # 检索证据
calibrate(question: str) → dict         # 全自动校准
health() → {"status": "ok", "version": "0.1.0"}
```

**验证步骤：**
1. ✅ stdio 模式：`python mcp_server.py` → 任何 MCP 客户端可调
2. ✅ 再配置 Claude Desktop（冷启动 import 不能报错）

---

## Phase 4: Docker + README + DECISIONS.md（Day 4）

### Docker

先检查 C 盘：
```powershell
docker info | Select-String "Docker Root Dir"
```

- C 盘 < 15GB 且 Docker Root 在 C → 跳过 Docker，用 pip install 替代
- 否则 build：`python:3.12-slim`，入口 CLI，docker-compose 可选

### README（边开发边更新）

含一张**数据流架构图**（ChatGPT 建议画 data flow 而非 module）：

```
                User
                  │
                  ▼
              CLI / MCP
                  │
                  ▼
         Agent Orchestrator
          ├─────────────┐
          ▼             ▼
    Retriever        LLM Client
    (KC Backend)   (deepseek-chat)
          │             │
          └──────┬──────┘
                 ▼
         Calibration Engine
         (M1 → M2 → M3 → M4)
                 │
                 ▼
           Audit Logger
           (JSONL)
```

### DECISIONS.md

记录关键架构决策（Architecture Decision Record）：

| 决策 | 选项 | 选择 | 原因 |
|------|------|------|------|
| 结果格式 | dataclass vs dict vs TypedDict | TypedDict | 固定 schema + 灵活 |
| 检索方式 | Skill API vs embedding | 遍历 registry 关键词 | 零依赖，10 行代码 |
| LLM 位置 | 管线内 vs 外部 | 外部 calibrate + 内部 calibrate_full | 两条路径都支持 |
| MCP scope | 1 tool vs 3 tools | retrieve + calibrate + health | 可调试 + 可扩展 |
| 模型名 | deepseek-chat vs OpenRouter slug | deepseek-chat（直连） | 已有代码已验证 |

---

## 不做（与 v1/v2 一致）

| 事项 | 原因 |
|------|------|
| 新 UI | CalTrust Streamlit 已有，CLI + MCP 已够 demo |
| BM25 / Hybrid Search | 遍历 registry 关键词第一版够用 |
| 全量 Evaluation Pipeline | 已有 e2e_test.py + baseline (24 cases) |
| 论文写作 | 等 Path B 数据 |
| CalTrust 完善 | 启动 Path A 不依赖它 |

---

## 预算

| Phase | API 消耗 | 成本 |
|-------|----------|------|
| Phase 0 Smoke Test | 0 | ¥0 |
| Phase 1 Pipeline | DeepSeek × ~5 次调试 | ~¥0.05 |
| Phase 2 CLI | 0 | ¥0 |
| Phase 3 MCP | 0 | ¥0 |
| Phase 4 Docker/README | 0 | ¥0 |
| **总计** | | **< ¥10** |

---

## 文件结构（最终目标）

```
CheckMyCoach/
├── config.py                   # @dataclass Settings
├── schema.py                   # TypedDict: CalibrateResult, TokenUsage
├── pipeline/
│   ├── __init__.py
│   └── agent_pipeline.py       # calibrate() + calibrate_full()
├── evidence/
│   ├── __init__.py
│   ├── base.py                 # RetrievalBackend (ABC)
│   └── retriever.py            # KnowledgeCompilerBackend + EvidenceRetriever
├── audit/
│   ├── __init__.py
│   └── trail.py                # JSONL
├── server/
│   ├── __init__.py
│   └── mcp_server.py           # MCP stdio (3 tools)
├── cli.py                      # --json, --no-audit
├── test_samples/               # 3 pipeline-level test cases
│   ├── needs_calibration.json
│   ├── already_calibrated.json
│   └── no_evidence.json
├── Dockerfile
├── docker-compose.yml          # 可选
├── calibration_agent/          # 已有
├── requirements.txt
├── pyproject.toml
├── .env                        # 已有
├── README.md                   # 含 data flow 架构图
├── DECISIONS.md                # Architecture Decision Record
└── changelog_v2_to_v3.md       # 本轮变更摘要
```

---

## 修订记录

| 版本 | 来源 | 主要修改 |
|------|------|---------|
| v1 | Reasonix 调研 | 初始版本 |
| v2 | ChatGPT + Claude Code + Coze 第一轮 | Phase 0 · 双路径 API · Audit 增强 · config.py · Docker 后移 |
| v3 | ChatGPT 第二轮 + Claude Code 第二轮 + Coze 第二轮 | 事实修正（UCS int / 模型名 / KC 无关键词搜索）· @dataclass Settings · Backend 抽象 · TypedDict schema · token_usage · 统一错误格式 · 3 MCP tools · --no-audit · 非正常路径处理 · DECISIONS.md · data flow 图 |
