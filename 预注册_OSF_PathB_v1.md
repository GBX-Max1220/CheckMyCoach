# OSF 预注册草稿 — Path B

> ⏳ IRB 审批中，刺激材料盲评进行中
> 本文件为 OSF 预注册模板格式，IRB 批准 + 操纵检验通过后正式发布

---

## 1. 研究标题

**AI 健身建议中的信任校准方向不对称性：基于 UCS 分类的 Appropriate Reliance 实验研究**
Asymmetry in Trust Calibration for AI Fitness Advice: An Experimental Study Using the UCS Taxonomy

## 2. 作者

Guo, Max (Independent Researcher)

## 3. 描述

### 3.1 摘要

LLM 越来越多地被部署为高利害领域（健康、医疗、法律）的建议提供者，但标准评估方法仅关注输出准确性，忽略了用户如何在接收建议时校准信任。本研究基于 UCS（不确定性校准评分）四层级分类框架，通过一个 2（AI 建议正确性）× 4（UCS 类别）被试内实验，测量用户在健身场景下对 AI 建议的恰当依赖（Appropriate Reliance）。核心假设是：Pseudo-precise（伪精确）类建议的误接受率显著高于 Hedged（对冲）类建议的误拒绝率，即用户的信任校准误差呈不对称分布——过度信任多于信任不足。

### 3.2 背景与理论基础

LLM 在提供专业建议时，其语言输出的确定性与实际证据基础之间经常存在错配。UCS 框架将这种错配分为四类：
- **Overconfident（过度自信）**：无充分证据时做出绝对性声明
- **Pseudo-precise（伪精确）**：使用看似精确但无依据的数字
- **Calibrated（良好校准）**：明确陈述证据状态，置信度与证据匹配
- **Hedged（过度对冲）**：仅给出模糊分析，低估已知结论

本研究借鉴双过程理论（Kahneman, 2011）和自动化偏见文献（Mosier et al., 1998; Skitka et al., 1999），假设不同 UCS 类别的建议会触发用户不同程度的系统 1（直觉）和系统 2（分析）处理，导致系统性的信任校准偏差。

### 3.3 研究问题

- **RQ1**：用户的 Appropriate Reliance 是否因建议的 UCS 类别而不同？Overconfident/Pseudo-precise 建议的误接受率是否显著高于 Hedged/Calibrated 建议的误拒绝率？
- **RQ2**：用户的运动专业知识（连续变量）是否调节这种关系？高知识用户是否能更好地拒绝 Overconfident 建议，但对 Pseudo-precise 建议同样易受误导？
- **RQ3（探索性）**：表层特征（感知确定性、术语密度、数字出现）能否预测 Appropriate Reliance，超越 UCS 类别自身的解释力？

## 4. 假设

### H1（主效应）
Pseudo-precise 建议的误接受率显著高于 Hedged 建议的误拒绝率。
- 检验：配对 t 检验（被试内），双尾
- 预期效应量：d = 0.30（保守估计）
- Power：0.80，α = .05，所需 N = 90

### H2（方向性）
总体误接受率 > 总体误拒绝率，即校准误差偏 over-trust 方向。
- 检验：配对 t 检验，双尾
- 方向性假设，不指定效应量

### H3（调节效应）
运动知识与 Overconfident 建议的误接受率负相关，但与 Pseudo-precise 建议的误接受率无显著相关（或正相关——专业知识反转效应）。
- 检验：UCS × 知识连续协变量的 LMM 交互项
- 预期效应量：η² ≈ 0.04-0.06（小到中等）

## 5. 设计

### 5.1 实验类型
2 × 4 Mixed Design
- 被试内因素：UCS 类别（Overconfident / Pseudo-precise / Hedged / Calibrated），24 条建议（每类 6 条）
- 连续协变量：运动专业知识（自评 + 客观题 composite）
- 控制变量：AI familiarity、题目呈现顺序

### 5.2 刺激材料
从 FitRAG-Bench 的 252 条评估回答中预选出 48 条（12 条基材 × 4 UCS 版本），涵盖 4 个 UCS 类别，每类 12 条。每条经人工改写至 150-180 中文字符，控制术语密度和格式结构。

进行独立盲评验证（N = 3-5）：对每条材料在 1-7 Likert 量表上评分感知确定性。验证通过标准为四类材料单因素 ANOVA 主效应显著（p < .05），且事后检验呈现 Overconfident > Pseudo-precise > Calibrated > Hedged 单调递减顺序。

从每类 12 条中选择盲评区分度最高的 6 条，最终形成 **24 条正式实验材料**（每类 6 条）。选材标准为事后检验中组间均值差异最大、置信区间最窄的材料。该选取在操纵检验通过后、预注册发布前完成并锁定，正式预注册中说明选取规则但不披露具体材料内容（避免 demand characteristics）。

### 5.3 因变量

**主要指标：** Appropriate Reliance Score（每条试次）
- 二分类：恰当=1（AI 正确时接受 / AI 错误时拒绝）vs 不恰当=0（AI 正确时拒绝 / AI 错误时接受）
- 不确定判断编码为缺失值

**衍生指标：**
- 误接受率 = 错误建议中被接受的比例
- 误拒绝率 = 正确建议中被拒绝的比例
- 校准不对称系数 = 误接受率 - 误拒绝率

**辅助变量（每条试次）：**
- 判断确信度（1-7 Likert）
- 感知确定性（1-7 Likert）— 操作检验

**Ground truth 判定规则：**
每条材料的真实正确性由 UCS Engine 自动评分与人工标注共同确定。当两者不一致时，以人工标注为准。人工标注采用双标独立标注（2 名标注者），IRR 要求 Cohen's κ ≥ 0.7。若 κ < 0.7 则退回讨论、统一标注标准后重新标注，直至达标方可进入正式实验。最终不一致的条目以 2 名标注者讨论达成一致后的判定为 ground truth。

## 6. 被试

### 6.1 招募来源
- 健身科普微信公众号（约 2.5 万粉丝）：60-100 人
- 东北师范大学被试库：30-50 人
- 目标样本量：N = 105（含~15% 排除率）

### 6.2 纳入标准
- ≥18 岁
- 中文母语
- 过去 3 个月内至少使用过一次 AI 助手（如 ChatGPT、DeepSeek、豆包等）

### 6.3 排除标准
- Attention check 失败 ≥ 2 道
- 完成时间 < 5 分钟
- Straight-lining（同一量表全部选同一选项）

### 6.4 Power Analysis
A priori power analysis for a two-tailed paired-samples t-test (H1) with α = .05, power = .80, and expected effect size d = 0.30 (conservative estimate based on similar overtrust effects in decision-aid literature) indicated a required sample of N = 90. Accounting for ~15% attrition (attention check failure, incomplete responses, straight-lining), target recruitment is N = 105.

For the UCS × knowledge interaction (H3, repeated-measures ANOVA with 4 within-subject conditions, between-subject continuous covariate), assuming correlation r = .50 between repeated measures and effect size f = 0.15, a sample of N = 62 achieves power = .80. The H1-power target of N = 90 is therefore sufficient for all planned analyses.

## 7. 操作检验

盲评验证（独立样本，N = 3-5）确认四类 UCS 材料在感知确定性评分上满足：
1. 单因素 ANOVA 主效应显著（p < .05）
2. 事后检验顺序：Overconfident > Pseudo-precise > Calibrated > Hedged

正式实验中的嵌入操作检验：每次试次后收集感知确定性评分（1-7），通过 LMM 验证 UCS 类别的主效应仍然成立。

## 8. 流程

### 8.1 问卷结构（总时长 ~12-15 分钟）

1. **知情同意**（30 秒）：泛化为"AI 建议质量评估"，不透露 UCS 分类
2. **人口学与筛选**（2 分钟）：年龄、AI 使用频率、运动知识自评（1-7）+ 3-5 道客观运动知识选择题
3. **主实验**（8-10 分钟）：24 条建议完全随机呈现，每条包含：
   - 阅读 AI 建议
   - Step 1 判断："你认为这条建议正确还是错误？"（正确 / 错误 / 不确定）
   - Step 2 确信度："你对自己的判断有多确定？"（1-7）
   - Step 3 感知确定性："这条建议听起来有多确定？"（1-7）— 内嵌操作检验
4. **开放式反馈**（1 分钟，选填）

### 8.2 Pilot
正式投放前会先运行 N = 10 的 Pilot 测试，验证操纵有效性与问卷可理解性。若 Pilot 中操作检验不通过（UCS 类别在感知确定性上不显著），则退回修改刺激材料，重新盲评。

## 9. 分析计划

### 9.1 主分析（LMM）

使用 R 包 lme4 拟合线性混合效应模型：

**模型 1（主效应）**
```r
appropriate_reliance ~ ucs_category + knowledge_continuous + 
  ai_familiarity + order_position + 
  (1 | participant_id) + (1 | item_id)
```

**模型 2（交互效应）**
```r
appropriate_reliance ~ ucs_category * knowledge_continuous + 
  ai_familiarity + order_position + 
  (1 | participant_id) + (1 | item_id)
```

### 9.2 校准方向分析
- 配对 t 检验：误接受率 vs 误拒绝率
- 单样本 t 检验：校准不对称系数 vs 0

### 9.3 操作检验
```r
perceived_certainty ~ ucs_category + (1 | participant_id) + (1 | item_id)
```
验证标准：UCS 类别主效应显著，事后检验呈现 Overconfident > Pseudo-precise > Calibrated > Hedged。

### 9.4 探索性分析
将表层特征（字数、术语密度、数字出现次数）作为额外预测变量加入 LMM，通过似然比检验判定其是否在 UCS 类别之上增加解释力。

### 9.5 多重比较校正
所有事后比较使用 Tukey HSD 或 Holm 校正。

### 9.6 缺失值处理
"不确定"判断编码为缺失值，不纳入 Appropriate Reliance 分析。如果缺失率 > 10%，则补充敏感性分析（将不确定编码为不恰当进行稳健性检验）。

## 10. 预期结果与解释规则

- 如果 H1 显著 + H2 显著：确认信任校准存在不对称性（over-trust 主导）
- 如果 H1 显著但 H2 不显著：不对称性仅在特定 UCS 类别间存在，不在整体水平
- 如果 H1 不显著：可能原因 (a) 刺激材料操纵无效、(b) 效应量小于预期需要更大样本、(c) 信任校准在健身场景中不存在不对称性
- H3 显著 + 交互方向符合预期 → 专业知识反转效应成立
- H3 不显著 → 运动知识不调节 UCS 分类效应，或效应量过小

## 11. 参考文献（选列）

Buçinca, Z., Malaya, M. B., & Gajos, K. Z. (2021). To trust or to think: Cognitive forcing functions can reduce overreliance on AI in AI-assisted decision-making. *Proceedings of the ACM on Human-Computer Interaction*, 5(CSCW1), 1-21.

Kahneman, D. (2011). *Thinking, fast and slow*. Farrar, Straus and Giroux.

Mosier, K. L., Skitka, L. J., Heers, S., & Burdick, M. (1998). Automation bias: Decision making and performance in high-tech cockpits. *The International Journal of Aviation Psychology*, 8(1), 47-63.

Skitka, L. J., Mosier, K. L., & Burdick, M. (1999). Does automation bias decision-making? *International Journal of Human-Computer Studies*, 51(5), 991-1006.

Yin, M., Wortman Vaughan, J., & Wallach, H. (2020). Understanding the effect of accuracy on trust in machine learning models. *Proceedings of the SIGCHI Conference on Human Factors in Computing Systems*.

---

*草稿版本：v1 | 2026.6.24 | 状态：待发布（待 IRB 批准 + 操纵检验通过）*
