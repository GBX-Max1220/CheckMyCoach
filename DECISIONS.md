# CheckMyCoach — Architecture Decision Record

> 本文件记录关键架构决策、可选方案、选择理由和后续影响。
> 参考 ChatGPT v2 review 建议："半年后回看，这些记录会比继续修改计划更有价值。"

---

## ADR-001: 返回格式 TypedDict 而非 dataclass

**状态：** 已采纳（2026.7.5）

**背景：** 管线结果需要固定的 schema 供 CLI / MCP / Python API / Audit 统一消费。
ChatGPT v1 建议用 dict（灵活），v2 建议固定 schema（避免 Agent 炸掉）。

**选项：**
1. dataclass — 类型安全，但加字段需要改所有调用点
2. TypedDict — schema 固定 + 字段可选 + 无需重构旧数据
3. 纯 dict — 最灵活，但字段名不一致会在多 Agent 场景下爆炸

**选择：** TypedDict（`schema.py` 中的 `CalibrateResult`）

**理由：** TypedDict 同时满足 schema 固定和字段可选。`NotRequired` 让 HCI 字段可以占位。
`total=False` 允许渐进扩展。

---

## ADR-002: Evidence Retriever 遍历 registry 而非 embedding

**状态：** 已采纳（2026.7.5）

**背景：** Knowledge Compiler Skill API 只支持 exact match（`resolve()` 和 `get()` 都是 dict lookup）。
Phase 0 已确认 `resolve("squat")` 返回 None，关键词搜索需要遍历 registry。

**选项：**
1. 遍历 registry 做子串匹配 — 零依赖，~10 行代码
2. embedding（sentence-transformers + numpy）— 精度高，但增加 ~200MB 依赖
3. 混合：先关键词再 embedding 精排 — 最优雅，但实现复杂

**选择：** 选项 1（遍历 registry 子串匹配）

**理由：** 1 小时后评估显示精度满足 MVP 需求（5 条证据中有 2 条直接相关）。
embedding 已预留接口（`RetrievalBackend` ABC），可在 Phase 1.5 替换。

---

## ADR-003: 双路径 API — calibrate + calibrate_full

**状态：** 已采纳（2026.7.5）

**背景：** Claude Code v1 review 指出 LLM 调用位置的分歧。
ChatGPT v1 建议管线内调 LLM，Claude Code 建议 LLM 是外部调用者的事。

**选项：**
1. 仅 `calibrate(response, question)` — 灵活，但 demo 需要外部先调 LLM
2. 仅 `calibrate_question(question)` — demo 友好，但无法校准已有回答
3. 两者都支持 — calibrate_full 是 calibrate 的 wrapper

**选择：** 选项 3

**理由：** Human Study 需要用 `calibrate()`（用户提供 GPT 回答），
产品 Demo 需要用 `calibrate_full()`（用户只提问）。代码量差不到 10 行。

**后续：** Coze v2 建议改名 `calibrate_full`（取代 `calibrate_question`）。已采纳。

---

## ADR-004: LLM Provider 默认为 DeepSeek 直连

**状态：** 已采纳（2026.7.5）

**背景：** Phase 0 发现 OpenRouter 401 错误（key 存在但可能无额度）。
已有代码（`baseline_comparison.py`）用 DeepSeek 直连已确认工作。

**选择：** 默认 `api_provider = "deepseek"`，通过 `api.deepseek.com` 直连。
OpenRouter 可通过 `api_provider = "openrouter"` 切换。

---

## ADR-005: UCS Score 统一为 int 0-3（非语义标签）

**状态：** 已采纳（2026.7.5）

**背景：** Coze v1 指出 Audit 中混用了数字和语义标签。
Phase 0 确认 UCS Engine 返回 `UCSResult.ucs_score: int`。

**选择：** 全系统统一用 int 0-3。语义标签仅在 CLI pretty print 中映射。

**影响：** Audit JSONL 中的 `ucs_label` 字段已删除，统一为 `ucs_score: int`。

---

## ADR-006: MCP Server 暴露 3 个 tool

**状态：** 已采纳（2026.7.5）

**背景：** ChatGPT v2 建议 MCP 不要只有 `calibrate` 一个 tool。

**选择：** `retrieve()` + `calibrate()` + `health()`

**理由：** `retrieve` 可独立测试检索质量，`health` 可用于 Debug 和冷启动验证。

---

## ADR-007: score_delta 不作为论文定量指标

**状态：** 已采纳（2026.7.5）

**背景：** Claude Code v2 指出 UCS Engine 的 LLM 分支有随机性，
两次 UCS 评分可能因分支选择不同而产生非确定性 delta。

**选择：** audit 中记录 score_delta 但注释标明测量噪声。
目前不作为 paper 定量指标。
