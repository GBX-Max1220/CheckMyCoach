## v2 → v3 变更摘要（2026.7.5）

### 事实修正（实锤验证后）
- **Audit schema 修正**：UCS Engine 输出 int (0-3)，不是语义标签。删掉 audit 里 `ucs_label: "PSEUDO_PRECISE"`，统一用 `ucs_score: int`
- **模型名修正**：`deepseek-v4-flash` 是幻觉命名。实际代码用 `deepseek-chat`（直连 `api.deepseek.com`），如果走 OpenRouter 用 `deepseek/deepseek-chat`
- **Evidence Retriever 修正**：KC Skill 不支持关键词搜索（`resolve("squat")` → None），需要遍历 registry 做字符串匹配

### 采纳 ChatGPT 第二轮
- `config.py` 改为 `@dataclass Settings`（可切 DEV/PROD/TEST）
- Retriever 加 Backend 抽象层（`Retriever → KnowledgeCompilerBackend`），为多数据源预留
- 结果加 `TypedDict` 定义 schema（`CalibrateResult`），写在 `schema.py` 或 `RESULT_SCHEMA.md`
- Audit 加 `token_usage: {prompt_tokens, completion_tokens, cost}`
- MCP Server 暴露 3 个 tool：`retrieve()` + `calibrate()` + `health()`
- CLI 加 `--no-audit` 参数
- 统一错误响应格式：`{success, result, error, audit_id}`
- 加 `DECISIONS.md`（Architecture Decision Record）

### 采纳 Claude Code 第二轮
- Phase 0 加 KC 安装 fallback：`pip install` 失败则 `sys.path` + 手动 pip install pyyaml
- score_delta 加注释说明测量噪声（UCS LLM 分支非确定性）
- MCP 验证分两步：先 stdio 模式 → 再 Claude Desktop 配置

### 采纳 Coze 第二轮
- Audit 统一为数值 UCS（如上）
- Retriever 加遍历 registry 的 fallback 方案
- 非正常路径处理表：每步的 try-except 降级策略
- 测试样本：3 条新 pipeline 级样本（非复用 e2e_test.py），覆盖：需要校准 / 不需要校准 / KC 检索不到
- 函数命名改为 `calibrate(response)` + `calibrate_full(question)`
