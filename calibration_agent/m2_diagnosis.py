"""
M2 诊断层 — 对 M1 标记为 CALIBRATE 的建议，诊断失败类型。

输入：UCSResult + 原始建议文本
输出：DiagnosisResult（failure_type + confidence + evidence）

三种失败类型（基于 extraction_features 做规则判断，不调 LLM）：

1. TEMPLATE_DOMINANCE（模板优越）
   - 信号：claims_superiority=True, cites_evidence_type=False
   - 特征：听起来权威但无证据支撑

2. CUE_LEAKAGE（线索泄露）
   - 信号：ucs_score=1 (Pseudo-precise), has_directional_claim=True
   - 特征：看似精确的数字/参数但无来源

3. CONTEXT_MISMATCH（场景错配）
   - 信号：needs_manual_review=True 或 extraction 特征矛盾
   - 特征：建议本身可能正确，但忽略了用户情境
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FailureType(Enum):
    TEMPLATE_DOMINANCE = "template_dominance"
    CUE_LEAKAGE = "cue_leakage"
    CONTEXT_MISMATCH = "context_mismatch"
    UNKNOWN = "unknown"


@dataclass
class DiagnosisResult:
    """M2 诊断输出"""
    failure_type: str                # failure_type.value
    confidence: float                # 0.0 ~ 1.0
    evidence: list[str] = field(default_factory=list)
    raw_features: dict = field(default_factory=dict)


def diagnose(ucs_score: int, ecs_score: int = 0,
             claims_superiority: bool = False,
             has_directional_claim: bool = False,
             mentions_no_difference: bool = False,
             has_hedging: bool = False,
             cites_evidence_type: bool = False,
             needs_manual_review: bool = False,
             review_reason: str = "",
             text: str = "") -> DiagnosisResult:
    """
    诊断失败类型，基于 extraction_features 做规则判断。

    优先规则（按优先级从高到低）：
      1. needs_manual_review=True        → CONTEXT_MISMATCH（需要人工介入）
      2. 矛盾特征（superiority + no-difference）→ CONTEXT_MISMATCH
      3. claims_superiority=True, no evidence → TEMPLATE_DOMINANCE
      4. UCS=1 (Pseudo-precise) + directional → CUE_LEAKAGE
      5. 以上都不匹配                   → UNKNOWN（留给 M3 灵活处理）
    """
    evidence_list: list[str] = []
    failure = FailureType.UNKNOWN
    confidence = 0.0

    # ================================================================
    # 第一步：基于特征做诊断（不考虑 needs_manual_review）
    # ================================================================

    # --- 规则 1: 矛盾特征 → 场景错配 ---
    if claims_superiority and mentions_no_difference:
        failure = FailureType.CONTEXT_MISMATCH
        confidence = 0.7
        evidence_list.append("矛盾信号: claims_superiority=True 和 mentions_no_difference=True 并存")

    # --- 规则 2: 模板优越 (有优越性声明，无证据引用) ---
    elif claims_superiority and not cites_evidence_type:
        failure = FailureType.TEMPLATE_DOMINANCE
        confidence = _calc_confidence(claims_superiority, False, ecs_score)
        evidence_list.append("claims_superiority=True 且 cites_evidence_type=False")
        if ucs_score == 0:
            evidence_list.append("UCS=0: 过度自信 — 绝对性声明无证据支撑")

    # --- 规则 3: 线索泄露 (UCS=1 + 方向性声明) ---
    elif ucs_score == 1 and has_directional_claim:
        failure = FailureType.CUE_LEAKAGE
        confidence = _calc_confidence(ucs_score == 1, has_directional_claim, ecs_score)
        evidence_list.append("UCS=1: 伪精确 — 数字或参数看似精确但无来源")
        evidence_list.append("has_directional_claim=True — 带有方向性倾向")

    # --- 规则 4: 兜底 — 虽标记为 CALIBRATE 但无明确诊断特征 ---
    elif ucs_score == 0:
        failure = FailureType.TEMPLATE_DOMINANCE
        confidence = 0.5
        evidence_list.append("UCS=0 但无典型模板优越特征 — 保守诊断为模板优越")
    elif ucs_score == 1:
        failure = FailureType.CUE_LEAKAGE
        confidence = 0.5
        evidence_list.append("UCS=1 但无方向性声明 — 保守诊断为线索泄露")

    # ================================================================
    # 第二步：needs_manual_review 作为修饰器，不单独决定类型
    # ================================================================
    if needs_manual_review:
        evidence_list.append(f"需人工复查: {review_reason or '未指定原因'}")
        if failure != FailureType.UNKNOWN:
            # 有明确的特征诊断 → 保持原诊断，降低置信度
            confidence = min(confidence, 0.6)
        else:
            # 特征无法判断 → 兜底为 CONTEXT_MISMATCH，低置信度
            failure = FailureType.CONTEXT_MISMATCH
            confidence = 0.5
            evidence_list.append("needs_manual_review=True 且无明确特征模式 — 保守诊断为场景错配")

    return _build_result(failure, confidence, evidence_list, locals())


def _calc_confidence(feature_a: bool, feature_b: bool, ecs: int) -> float:
    """根据特征数量计算置信度。两个特征都匹配时置信度更高。"""
    base = 0.6
    if feature_a and feature_b:
        base += 0.25
    if ecs == 0:
        base += 0.05
    return min(base, 1.0)


def _build_result(failure: FailureType, confidence: float,
                  evidence: list[str], local_vars: dict) -> DiagnosisResult:
    """构建 DiagnosisResult，提取 raw_features 供 M3 使用。"""
    return DiagnosisResult(
        failure_type=failure.value,
        confidence=round(confidence, 2),
        evidence=evidence,
        raw_features={
            "ucs_score": local_vars.get("ucs_score"),
            "ecs_score": local_vars.get("ecs_score"),
            "claims_superiority": local_vars.get("claims_superiority"),
            "has_directional_claim": local_vars.get("has_directional_claim"),
            "mentions_no_difference": local_vars.get("mentions_no_difference"),
            "has_hedging": local_vars.get("has_hedging"),
            "cites_evidence_type": local_vars.get("cites_evidence_type"),
            "needs_manual_review": local_vars.get("needs_manual_review"),
        }
    )
