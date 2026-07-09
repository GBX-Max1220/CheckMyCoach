# CheckMyCoach — 基准测试报告

> 测试条件：Raw DeepSeek-chat（无证据上下文） vs 经 `calibrate()` 管线处理
> 样本量：10 questions | 2026.7.5

---

## 核心结果

| 指标 | 值 |
|------|-----|
| Raw LLM 平均 UCS | 2.0 (Hedged) |
| 校准后平均 UCS | 2.0 (Hedged) |
| 平均 UCS Delta | 0.0 |
| 触发校准次数 | 0/10 |
| Raw LLM 延迟 | 1.5s avg |
| 校准管线延迟 | 0.8s avg |

## 结论

**DeepSeek-chat 对健身问题天然保守，校准管线不触发。** 对比测试中 raw LLM 和校准后的 UCS 分布完全相同（100% UCS=2）。

但这不等于校准系统无效——**之前的 template_dominance 测试已证实当检测到过度自信时（UCS=0），管线正确完成检测→诊断→修正→验证全链路（delta +2.0）**。

校准系统的真实使用场景：
1. **Path B Human Study** — 参与者可能给出过度自信的回答
2. **其他模型** — GPT-3.5 / 微调模型可能不如 DeepSeek-chat 保守
3. **对抗测试** — 故意构造的过度自信样本

## 基础设施验证

| 要求 | 状态 |
|------|------|
| 管线不崩溃 | ✅ 50/50 + 10/10 零异常 |
| 检测能力 | ✅ UCS=0 正确触发 M1-M4 |
| 诊断能力 | ✅ template_dominance 正确分类 |
| 修正能力 | ✅ 英文输出，降低断言强度 |
| 验证能力 | ✅ M4 长度/断言/非空/非复制全检验 |
| 回退机制 | ✅ 不通过时回到原文，不抛异常 |
| 审计追踪 | ✅ 完整 JSONL 记录每步决策 |
| CLI | ✅ `python cli.py "问题"` 可用 |
| MCP | ✅ 3 tools (retrieve / calibrate / health) |
