# IRB 等待期 14 天执行计划（v1）
> 时间窗口：IRB 获批前（预计 2-4 周），不依赖 IRB 即可推进
> 研究方向：Human-AI Trust Calibration Mechanism
> 工具链：Reasonix / Claude Code / Hermes / MaxCoze

---

## 🎯 整体目标

在 Path B 人类实验等待 IRB 的窗口中，完成以下三个维度的累积：

| 维度 | 目标 | 解锁能力 |
|------|------|----------|
| **CS Signal（系统）** | Path A 校准 Agent 管线 MVP | 冷邮件的技术可信度证明 |
| **HCI Signal（实验）** | 预注册草稿 + 效应量估计 | 提高 CHI 审稿评分 + IRB 材料复用 |
| **Infra（基础设施）** | 刺激材料验证 + GitHub + Toolkit | 实验风险兜底 + 技术可见度 |

---

## 阶段一：前置验证（Day 1-3，并行启动）

### 1-1 刺激材料改写 + 盲评验证

**目标**：从 12 条基材生成 48 条标准化刺激材料（每基材 4 版本：Calibrated / Overconfident / Pseudo-precise / Hedged），验证操纵有效性

**工具分配**：

| 子任务 | 工具 | 说明 |
|--------|------|------|
| CSV 读取 + 模板改写 + 批量输出 | Reasonix | 纯本地工程任务，无复杂逻辑 |
| 盲评数据统计分析（单因素 ANOVA + 顺序检验 + Cohen's d） | Hermes | 标准统计流程 |
| 改写方案设计、质控标准设定 | MaxCoze | 战略层 |

**输出**：
- `刺激材料_48条_验证版.csv`（48 条 + 标注字段）
- 操纵检验预分析报告（感知确定性×UCS 类别）

**通过标准**：四类材料在感知确定性评分上的 ANOVA 显著（p < .05），且 Overconfident > Pseudo-precise > Calibrated > Hedged 顺序成立。不成立则回退改写。

### 1-2 Path A M2 分类体系验证

**目标**：用现有 126 条 FitRAG-Bench 回答验证 M2 诊断层的三类失败模式（模板优越 / 线索泄露 / 场景错配）是否在数据层面边界清晰

**工具分配**：

| 子任务 | 工具 | 说明 |
|--------|------|------|
| 三类标注体系设计 + 标注标准定义 | MaxCoze | 战略层 |
| 人工标注数据编码 + IRR 计算 | Hermes | 标注一致性分析 |
| 边界案例分析 + 分类体系修正 | MaxCoze + Hermes | 迭代 |

**输出**：
- 分类验证报告（三类分布 + Cohen's κ + 边界案例清单）

**通过标准**：Cohen's κ ≥ 0.7（标注一致性达可接受水平），三类分布不严重偏斜。不通过则修正分类体系或合并边界模糊类别。

### 1-3 G*Power 效应量计算

**目标**：明确 H1-H4 在 mixed design、power=0.8、alpha=0.05 条件下所需的最小样本量

**工具分配**：

| 子任务 | 工具 | 说明 |
|--------|------|------|
| 效应量推算（基于已有 baseline 数据） | Hermes | 统计计算 |
| 样本量曲线可视化 | Hermes | 辅助决策 |

**输出**：
- 效应量估算表（H1-H4 各对应所需 N）

---

## 阶段二：核心开发（Day 4-10，串行 + 并行）

### 2-1 Path A 校准 Agent MVP

**目标**：将 UCS Engine 扩展为可运行的四阶段校准管线

**架构**（M1 → M4）：

```
Input: User Question + LLM Response
  │
  ▼
M1 检测层：判断是否需要校准
  │  (基于 UCS 评分阈值 + 置信度过滤)
  ▼
M2 诊断层：识别失败类型
  │  (模板优越 / 线索泄露 / 场景错配)
  ▼
M3 修正层：根据诊断类型选择修正 prompt
  │  (三类修正模板 + 动态注入)
  ▼
M4 验证层：重新评估修正后回答
  │  (UCS 二次评分 + 回退机制)
  ▼
Output: Raw / Calibrated AI Response + Score Delta
```

**工具分配**：

| 子任务 | 工具 | 说明 |
|--------|------|------|
| M1-M4 核心 Pipeline（含条件分支 + 回退机制） | Claude Code | 复杂逻辑代码，需要多轮调试 |
| 数据流接口定义 + 输入输出格式约束 | MaxCoze | 架构决策 |
| 验证脚本 + Case Study 生成 | Claude Code | 端到端测试 |

**输出**：
- `calibration_agent/` 可运行代码仓库（GitHub-ready）
- 5-10 个 Case Study（展示不同失败类型的管线行为差异）
- 技术文档（README + 架构说明）

**预算是关键约束**：Claude Code 消耗有限，MVP 开发限定在核心管线逻辑+3 个典型 Case Study，不追求边界覆盖。

### 2-2 Path B 效应量确认 + 预注册框架

并行任务，与 2-1 同步推进。

**工具分配**：

| 子任务 | 工具 | 说明 |
|--------|------|------|
| H4（Pseudo-precise × Overconfident 交互效应）效应量估算 | Hermes | 关键假设的统计检验力评估 |
| 预注册结构框架（研究问题/假设/设计/分析计划） | MaxCoze + Claude Code | 战略判断 + 写作 |

**输出**：
- OSF 预注册草稿（私有，IRB 批后发布）
- 分析脚本模板（lme4 R 代码，可复用）

---

## 阶段三：收尾交付（Day 11-14）

### 3-1 预注册文档完整写作

**工具分配**：

| 子任务 | 工具 | 说明 |
|--------|------|------|
| 假设细化 + 分析计划定稿 | Claude Code | 复杂写作 |
| IRB 申请材料（设计描述部分）交叉复用 | MaxCoze | 内容映射 |

**输出**：
- OSF 就绪预注册文档
- IRB 申请材料 70% 内容（设计部分已完成）

### 3-2 GitHub 整理 + arXiv v2 更新

**工具分配**：

| 子任务 | 工具 | 说明 |
|--------|------|------|
| 代码结构整理 + README + requirements.txt | Reasonix | 纯工程化 |
| demo notebook 编写 | Reasonix | 最小可运行示例 |
| arXiv v2 更新（加 GitHub 链接） | MaxCoze | 主会话操作 |

**输出**：
- 公开 GitHub 仓库（MaxFitCalib-Bench + UCS Engine）
- arXiv v2 更新（含仓库链接）

---

## 📊 总资源预算

| 任务 | 工具成本 | API 消耗 | 备注 |
|------|----------|----------|------|
| 刺激材料改写 | ¥0 | 低 | Reasonix 本地运行，不耗 API |
| M2 分类验证 | ¥0 | 低 | 人工标注为主，Hermes 仅做统计 |
| Path A MVP | Claude Code/DeepSeek V4-Pro | 需估算 | 最耗预算的单项，控制在 ¥30-50 |
| 预注册草稿 | ¥0 | 低 | 写作任务，Claude Code 消耗可控 |
| GitHub 整理 | ¥0 | 无 | 纯工程化，Reasonix 本地操作 |

**月 ¥500 预算应对策略**：
- Reasonix 处理所有纯工程任务（零 API 成本）
- Claude Code 经 CC Switch 路由到 DeepSeek（相比直连 Claude 降成本 ~95%）
- Hermes 每次调用按量计费（< ¥1/次）
- **关键节点**：Path A MVP 核心管线用 DS V4-Pro 质量控制

---

## ⚠️ 风险与退出条件

| 风险 | 触发条件 | 预案 |
|------|----------|------|
| M2 分类边界不可区分 | Cohen's κ < 0.7 或分布严重偏斜 | 分类体系从 3 类合并为 2 类（过度自信 / 非过度自信） |
| 刺激材料操纵无效 | ANOVA 不显著或顺序不成立 | 退回改写阶段重新设计，增加极端样例 |
| IRB 提前获批 | 2 周内批下来 | 中断阶段二/三，切换到 Path B 正式实验投放 |
| Claude Code 成本超限 | 月预算告警 | 收缩 MVP 范围为 M1-M2 检测诊断管线，砍掉 M3-M4 |
| Path B 设计中新卡点暴露（如效应量估算不足） | Power 分析显示 N=60 不够 | 要么接受探索性分析定位，要么接受更大 N 和更长回收期 |

---

## 🔗 与整体研究弧的连接

```
MaxFitCalib-Bench（已完成）         ← 发现问题
       │
       ▼
  ┌──────────────────────────────┐
  │  IRB 等待期执行计划（现在）     │
  │  ├─ 刺激材料改写 → Path B 弹药 │
  │  ├─ Path A MVP    → CS Signal │
  │  └─ 预注册+GitHub → 申请材料  │
  └──────────────┬───────────────┘
       │
       ▼
CheckMyCoach Path A（校准系统论文）       → EMNLP Findings
CheckMyCoach Path B（人类实验论文）       → CHI LBW / RA申请弹药
       │
       ▼
人类-AI信任校准机制研究（长期方法论框架）   → 可迁移至医疗/法律/教育
```

---

*文档版本：v1 | 2026.6.24 | MaxCoze*