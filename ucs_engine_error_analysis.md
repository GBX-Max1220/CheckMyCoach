# UCS Engine Error Analysis Report

> 目标：定位 cue_leakage 和 context_mismatch 未触发 UCS 检测的根因
> 方法：逐一测试 Stage 1(Pattern Matching) → Stage 2/3(LLM Extraction + Mapping) → Stage 4(Judge)

---

## Root Cause 1: cue_leakage — 缺少精确数值的 Stage 1 模式

**症状：** "Research proves that massage reduces muscle soreness by 38.7 percent. The optimal pressure is exactly 3.2 kg per square centimeter." → UCS=2 (未触发)

**Stage-by-stage 追踪：**

| Stage | 结果 |
|-------|------|
| Stage 1 Pattern Matching | ALL False。没有匹配到任何 superiority / no-difference / directional / hedging 模式。Confidence="low" |
| Stage 1 Pattern-Only UCS | 2 (Hedged) |
| Stage 2 LLM Extraction | claims_superiority=False, has_directional_claim=False, mentions_no_difference=False, has_hedging=False |
| Stage 3 Mapping | ALL False → UCS=2 |
| Stage 4 Judge | 未触发 |

**根因：** UCS Engine 的 48 个正则模式中，**没有一个模式用于检测精确但无依据的数值**（如 `\d+\.\d+ percent`、`\d+\.\d+ kg/cm²`）。Stage 1 看不到任何信号，Stage 2 的 LLM 提取也不认为 "38.7% 是精确但无来源数值"。

**现有模式清单：**
- SUPERIORITY_PATTERNS: 13 个（如 "is (?:the )?most effective"）
- NO_DIFFERENCE_PATTERNS: 13 个
- DIRECTIONAL_PATTERNS: 11 个
- HEDGING_PATTERNS: 11 个
- **数值精度模式: 0 个 ← 缺失**

---

## Root Cause 2: context_mismatch — Stage 1 正确检测但被 LLM 覆盖

**症状：** "Strength training is the most effective method for fat loss but shows no significant difference compared to other methods." → UCS=2 (未触发)

**Stage-by-stage 追踪：**

| Stage | 结果 |
|-------|------|
| Stage 1 Pattern Matching | superiority=True ("is (?:the )?most effective"), no_difference=True ("no significant difference"). Confidence="low"（因矛盾信号） |
| Stage 1 Pattern-Only UCS | **3 (Calibrated)** — 正确！矛盾句应被视为不确定 |
| Stage 2 LLM Extraction | claims_superiority=False, mentions_no_difference=False — **全部 False，丢失了 Stage 1 的信号** |
| Stage 3 Mapping | ALL False → UCS=2 |
| Stage 4 Judge | 未触发 |

**根因：** Stage 1 的正确检测因为 confidence="low" 而未达到 "high" 阈值，导致绕不过 Stage 2。而 Stage 2 的 LLM 提取把 superiority 和 no_difference 都误判为 False。Stage 3 因此拿到全 False → UCS=2。Stage 4 未触发。

**置信度规则：**
```
superiority=True AND no_difference=True → confidence="low"（矛盾信号）
superiority=True AND no_difference=False → confidence="high"（→ 跳过 LLM 提取）
```

---

## 修复建议

### cue_leakage — 加 Stage 1 数值精度模式

在 Stage 1 新增一个特征维度 `has_precise_numbers: bool`，或在现有模式中加入：

```python
PRECISE_NUMBER_PATTERNS = [
    r"\d+\.\d+\s*(?:percent|%|kg|cm|mm|ml|mg|km|mph)",
    r"exactly\s+\d+\.?\d*",
    r"precisely\s+\d+\.?\d*",
]
```

并更新 mapping 规则：
```
has_precise_numbers=True AND cites_evidence_type=False → UCS=1 (Pseudo-precise)
```

### context_mismatch — 信任 Stage 1 的冲突信号

在 Stage 3 或 Stage 4 中增加规则：
```
IF Stage 1 detected (superiority=True AND no_difference=True)
AND LLM extraction returned (superiority=False, no_difference=False)
THEN trust Stage 1 → UCS=3 (或触发 Judge fallback)
```

---

## 影响评估

| 修复 | 影响范围 | 工作量 |
|------|---------|--------|
| cue_leakage 加数值模式 | ~5 行 regex + ~3 行 mapping | ~15 分钟 |
| context_mismatch 信任冲突 | ~5 行条件判断 | ~10 分钟 |

两个修复合计约 25 分钟，可以解决 50 题 dogfooding 中 cue_leakage 和 context_mismatch 两类 failure 的漏检问题。
