# CheckMyCoach 项目快照 — 给 Claude Code

> 请你基于以下信息审查 CheckMyCoach 项目的当前状态，
> 评价 ChatGPT 给出的判断，并给出你自己的建议。

---

## 一、项目定位

**研究方向：** Human-AI Trust Calibration / LLM Evaluation & Intervention
**身份：** 独立研究者（本科，无实验室/导师）
**约束：** 无 GPU，月 API 预算 ¥500，C 盘 < 15GB
**三重能力：** ML 工程（Python/PyTorch）+ HCI 实验设计（LMM）+ 心理测量学（construct validity）

---

## 二、目录结构

```
FitCalib-Bench/                      ← GitHub 主仓库（已上线）
├── evaluation/
│   ├── ucs_engine.py                ← UCS 分类引擎（4级：Overconfident/Pseudo-precise/Hedged/Calibrated）
│   ├── call_model.py                ← 多 provider API 调用器
│   ├── ucs_scorer.py                ← UCS 评分管线
│   ├── evaluate_responses.py        ← HYPO 约束打分
│   └── questions/                   ← 126 道基准测试题（8类别）
├── data/baselines/                  ← DeepSeek + Qwen baseline 数据
├── rules/                           ← UCS 设计文档
├── README.md
└── CheckMyCoach/                    ← 校准管线 + 实验方案
    ├── README.md                    ← Path A 管线文档
    ├── calibration_agent/
    │   ├── m1_detection.py          ← M1 检测层（ucs_score/ecs → 是否需要校准）
    │   ├── m2_diagnosis.py          ← M2 诊断层（template_dominance / cue_leakage / context_mismatch）
    │   ├── m3_correction.py         ← M3 修正层（LLM 改写，三种失败类型各一套硬编码 prompt）
    │   ├── m4_validation.py         ← M4 验证层（长度/断言/非空/非复制 + 否定语境过滤）
    │   ├── test_m1_detection.py     ← 10 tests ✅
    │   ├── test_m2_diagnosis.py     ← 14 tests ✅
    │   ├── test_m3_correction.py    ← 9 tests ✅
    │   ├── test_m4_validation.py    ← 8 tests ✅
    │   ├── e2e_test.py              ← 端到端 3 条全部通过 ✅
    │   └── e2e_screening.py         ← 筛选脚本
    ├── 刺激材料_48条_验证版.csv       ← 12基材×4UCS版本
    ├── 盲评问卷_48条_匿名.csv         ← 盲评用
    ├── 盲评页面.html                 ← 手机友好盲评（已发5人，等数据）
    ├── 实验方案_PathB_v1.1.md        ← Path B 实验方案
    ├── 预注册_OSF_PathB_v1.md        ← OSF 预注册草稿
    ├── PathB_问卷页面.html           ← 完整问卷（25题随机 + NASA-TLX + 文件下载）
    ├── merge_data.py                 ← 数据合并脚本（多JSON → CSV）
    ├── 20260624_工作日志.md           ← 完整日志
    ├── IRB等待期_执行计划_v1.md
    └── .env                          ← OPENROUTER_API_KEY（gitignored）
```

---

## 三、项目状态

### ✅ 已完成
| 项目 | 说明 |
|------|------|
| MaxFitCalib-Bench | 已提交 arXiv，等待 ID |
| GitHub 仓库 | 代码已推送，README 完整 |
| 48 条刺激材料 | 12 基材 × 4 UCS 版本，中文字数 140-180 |
| 盲评页面 | 已发出 5 人，等待回收 |
| G*Power 样本量 | N=90（目标 N=105） |
| OSF 预注册草稿 | 待 IRB + 盲评通过后发布 |
| M1-M4 校准管线 | 41 项测试通过，端到端 3/3 |
| Path B 问卷页面 | 可独立部署（25 题 + NASA-TLX + 注意力检查） |
| 数据合并脚本 | merge_data.py |
| OpenAI / Claude 账户被封 | 不影响 Reasonix + Claude Code + Hermes 工具链 |

### ⏳ 等待中
| 事项 | 依赖 |
|------|------|
| 盲评数据回收（5人） | 明天 |
| IRB 批准 | 学校审批（暂无进度） |

### ❌ 争议/明确不做
| 事项 | 决策 |
|------|------|
| 问卷星付费版 | 不用（¥480/年），自建 HTML 页面替代 |
| 红包激励 | 改为口头感谢 + 微信提交数据 |
| 新项目/新方向 | 不启动，冻结在现有弧线上 |

---

## 四、架构细节：Path A 校准管线

### 决策表

| UCS | ECS | needs_review | M1 决策 | M2 诊断 |
|-----|-----|-------------|---------|---------|
| 0 | — | — | CALIBRATE | template_dominance |
| 1 | — | — | CALIBRATE | cue_leakage |
| 2 | — | — | PASS | — |
| 3 | — | — | PASS | — |
| — | — | True | REVIEW | context_mismatch |

- needs_manual_review 不单独决定诊断结果，仅降低 confidence 至 0.6
- 只在无特征时兜底为 CONTEXT_MISMATCH（confidence=0.5）

### M3 Prompt 模板（硬编码，不动态生成）
三种失败类型各一套 system/user prompt，通过 `{original_text}` 注入。

### M4 验证规则
- 长度：50%-400%
- 断言：绝对词（"最/所有/一定/绝对"等）计数 ≤ 原文
- 否定语境过滤（"不/没有/无法/不能/并非"前 5 字符）
- "有一定"语义排除
- 非空 + 字符重叠比 < 0.9

### 环境
```bash
# .env 单行
OPENROUTER_API_KEY=sk-or-v1-...
# M3 使用 gpt-4o-mini，单次成本 < ¥0.01
```

---

## 五、架构细节：Path B 实验

### 设计
- 2×4 Mixed Design（UCS类别被试内 × 运动知识连续协变量）
- 24 条刺激材料（盲评后从 48 条中选区分度最高的 24 条）
- 每条三问：事实判断（正确/错误/不确定）+ 确信度 1-7 + 感知确定性 1-7
- 问卷末尾 NASA-TLX 精简 3 题（脑力/努力/挫败感）
- 每道题记录 RT（performance.now()，毫秒级）

### 被试
- 公众号 2.5 万粉丝（60-100 人）+ 东北师大被试库（30-50 人）
- N=105（含 ~15% 排除率）

### 分析
```r
appropriate_reliance ~ ucs_category * knowledge_continuous + 
  ai_familiarity + order_position + cognitive_load +
  (1 | participant_id) + (1 | item_id)
```

### 问卷实现
自包含 HTML（25 题 + NASA-TLX + 注意力检查 + 随机顺序 + 文件下载/邮件提交）

---

## 六、ChatGPT 评价要点

（以下为 ChatGPT 的核心判断，请你审查其准确性）

### 正面
- "项目弧线（评估→干预→验证）是最大优势，比大多数本科 AI 项目更像研究"
- "Path A + Path B 双路径设计符合 HCI 论文结构"
- "M1-M4 的 confidence-aware design 避免了下游失败"
- "不训练模型是正确决策"
- "阶段转换：从执行阶段进入发表准备阶段"

### 批评
- "UCS 理论创新性可能不足，审稿人可能问与已有 calibration research 有何不同"
- "Path B 实验需要加 perceived diagnosticity 来揭示 trust 变化的机制"
- "CheckMyCoach 工程 demo 感重，需要包装成研究贡献"
- "30 天内拿到 Path B 初始结果 + 一版论文 draft"

### 概率判断
- CHI LBW：60%
- CHI full paper：20-30%
- CSCW：40%
- 投稿路线未具体指定

---

## 七、请你回答的问题

1. ChatGPT 的三个批评是否站得住脚？各打几分（1-10）？
2. ChatGPT 建议的"30 天出 Path B 结果 + paper draft"是否可行？
3. 以 CSCW 为目标 venue，我现在最应该做的一件事是什么？
4. 投稿时间线如何安排？考虑：盲评（3天）→ IRB（2-4周）→ 数据回收（2-4周）→ 分析（1周）→ 写作（3-4周）
5. 我的工具链（Reasonix + Claude Code + Hermes）在当前阶段是否有缺口？
