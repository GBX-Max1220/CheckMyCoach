"""
CheckMyCoach — 数据 Schema

所有的管道输入/输出/审计均使用此处的 TypedDict 定义。
固定 schema 的目的是确保各方（CLI / MCP / Python API / Audit）使用一致的字段名。
（ChatGPT v2 review 建议：schema 必须固定，否则 Agent 全部会炸）

Architecture Decision:
    TypedDict 而非 dataclass（ChatGPT v1 建议 dict 优先，v2 建议固定 schema）
    TypedDict 同时满足：schema 固定 + 字段可选 + 无需重构旧数据
"""

from typing import TypedDict, NotRequired


class TokenUsage(TypedDict, total=False):
    """LLM token 使用统计。"""
    prompt_tokens: int
    completion_tokens: int
    cost: float
    """USD。暂以 DeepSeek API 价格估算。"""


class LatencyMs(TypedDict, total=False):
    """各阶段延迟（毫秒）。"""
    retriever: float
    llm: float
    ucs_engine: float
    m1: float
    m2: float
    m3: float
    m4: float
    total: float


class CalibrateResult(TypedDict, total=False):
    """校准结果统一 schema。

    所有返回点（成功/失败/异常）均使用此结构。
    错误时：success=False, error="ERROR_CODE", result 可能为空。
    """

    # ---- 状态 ----
    success: bool
    """true=管线正常完成, false=管线中途失败"""
    error: NotRequired[str | None]
    """统一错误码（如 KC_IMPORT_ERROR, LLM_TIMEOUT, AUDIT_WRITE_FAIL）。
       成功时为 None。"""
    audit_id: str
    """本次运行的唯一 ID，用于关联 audit JSONL 记录。"""

    # ---- 输入 ----
    question: str
    path: str
    """"calibrate" | "calibrate_full" """

    # ---- 检索 ----
    evidence: NotRequired[list[dict]]
    """结构化证据列表，每项含 id/type/source/content。"""

    # ---- 原始回答 ----
    response: NotRequired[str]
    """AI 生成的原始回答（calibrate_full 由管线内部生成，calibrate 由外部传入）。"""
    ucs_score: int
    """UCS 评分（0-3）。注意：这是数字，不是语义标签。
       0=Overconfident, 1=Pseudo-precise, 2=Hedged, 3=Calibrated"""
    extraction_features: NotRequired[dict]
    """UCS Engine Stage 2 提取的 5 个二元特征。"""

    # ---- 校准 ----
    needs_calibration: bool
    failure_type: NotRequired[str | None]
    """"TEMPLATE_DOMINANCE" | "CUE_LEAKAGE" | "CONTEXT_MISMATCH" | None"""
    m2_confidence: NotRequired[float | None]
    """M2 诊断置信度（0-1）。"""
    corrected_response: NotRequired[str | None]
    """M3 校准后的回答。如果 M4 验证不通过则回退为原文。"""
    score_delta: NotRequired[float | None]
    """校准前后 UCS 差值。⚠️ 近似值：UCS Engine 的 LLM 分支有随机性，
       此数据包含测量噪声，目前不作为论文定量指标。"""
    m4_passed: bool

    # ---- 审计 ----
    latency_ms: NotRequired[LatencyMs]
    token_usage: NotRequired[TokenUsage]

    # ---- HCI 字段占位 ----
    # （Coze v1 review 建议：预设占位，不要求填，保持 schema 兼容）
    pre_trust_score: NotRequired[float | None]
    """先验信任度（1-5）。Human Study 数据回填。"""
    decision_change: NotRequired[bool | None]
    """决策改变意愿。Human Study 数据回填。"""
    user_profile: NotRequired[dict | None]
    """用户 Profile（年龄/训练年限/目标）。Human Study 数据回填。"""
