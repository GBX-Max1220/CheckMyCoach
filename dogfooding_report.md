# CheckMyCoach — Dogfooding Report (50 questions)

> 运行时间：2026.7.5 | 工具：batch_dogfood.py
> 问题范围：训练/跑步/营养/安全/特殊人群/恢复/补剂 8 大类

---

## 核心指标

| 指标 | 值 |
|------|-----|
| 成功率 | **50/50 (100%)** |
| UCS=0 (Overconfident) | 1 (2%) — 冰浴 vs 热浴 |
| UCS=1 (Pseudo-precise) | 0 (0%) |
| UCS=2 (Hedged) | 49 (98%) |
| UCS=3 (Calibrated) | 0 (0%) |
| 平均 LLM 延迟 | ~4.1s |
| 总 API 成本 | ~¥0.50 |

## 校准事件

唯一一次触发校准（UCS=0 → template_dominance）：
- M2 诊断 ✅ 正确识别失败类型
- M3 修正 ❌ 返回中文文本（prompt 语言不匹配），M4 回退到原文
- score_delta: 0.0（因回退未产生变化）

## 发现的问题

### Bug 1: M3 修正 prompt 是中文
`calibration_agent/m3_correction.py` 的 prompt 模板是中文。
M3 调用 LLM 时生成中文修正 → M4 验证不通过 → 回退到原文。
**影响：校准结果永远不会生效。** M1-M2 能正确检测，但 M3-M4 的修正→回退循环导致无实际改变。

### Bug 2: UCS Engine LLM 提取过于保守
对于 "absolutely the most effective" + "Everyone must do it" 这类明显过度自信语句，
LLM 提取返回全 False（claims_superiority=False），导致 UCS=2。
**影响：绝大多数过度自信未触发校准。** 这是 UCS Engine 本身的限制，不是新管线的 bug。

### Bug 3: Latency 追踪未完全穿透
`calibrate_full` → `calibrate` 的 latency 合并逻辑在 audit 中不稳定。
**影响：audit 中 retriever 和 llm 延迟显示为 0ms。** 已修复但需验证。

## 改进建议（按优先级）

1. **高** — M3 prompt 改为英文，或复用原回答语言
2. **高** — 测试 `calibrate()`（非 `calibrate_full`）的端到端校准能力，使用真实 LLM 回答（来自 ChatGPT/GPT 等，而非本管线生成的保守回答）
3. **中** — 验证 latency 合并修复效果
4. **低** — UCS Engine LLM 提取 prompt 调优（增加过度自信检测灵敏度）

## 结论

**Pipeline 基础设施稳定可靠（50/50 不崩溃），但校准有效性受限于两个预存 bug。**
新代码（config/schema/retriever/pipeline/CLI/MCP）质量通过了 dogfooding 验证。
下一步建议：修 M3 prompt 语言问题，然后用真实外部 LLM 回答测试 `calibrate()`。
