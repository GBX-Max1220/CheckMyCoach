"""
M1 检测层 — 判断 AI 建议是否需要进入校准管线。

校准管线的设计方向：将过高的置信度降低至证据匹配水平。
因此仅处理 Overconfident (UCS=0) 和 Pseudo-precise (UCS=1) 的"过度自信"类错误。
Hedged (UCS=2) 是"置信度偏低"，修正方向相反，不由本管线处理。

输入：UCSResult（来自 ucs_engine.evaluate_ucs）
输出：(needs_calibration: bool, reason: str)

判断规则：
  - UCS=0 (Overconfident)         → 需要校准（置信度过高）
  - UCS=1 (Pseudo-precise)        → 需要校准（伪精确同样过信）
  - needs_manual_review=True      → 需要校准（人工确认优先级最高）
  - UCS=2 (Hedged)                → 跳过（置信度偏低，方向相反）
  - UCS=3 (Calibrated)            → 跳过（已校准）
"""

from enum import Enum


class CalibrationDecision(Enum):
    """校准决策类型"""
    PASS = "pass"             # 不需要校准
    CALIBRATE = "calibrate"   # 需要校准（降低置信度）
    REVIEW = "review"         # 需要人工复查


REASON_MAP = {
    "ucs0": "UCS=0: 过度自信 — 无充分证据时做出绝对性声明",
    "ucs1": "UCS=1: 伪精确 — 使用看似精确但无依据的数字或说法",
    "review": "需人工复查: UCS Engine 检测到矛盾信号或降级处理",
}


def needs_calibration(ucs_score: int, ecs_score: int = 0,
                      needs_manual_review: bool = False,
                      review_reason: str = "") -> tuple[bool, str]:
    """
    判断一条 AI 建议是否需要进入校准管线。

    Args:
        ucs_score: UCS 评分 (0-3)
        ecs_score: 证据引用信号 (0/1)
        needs_manual_review: 是否需要人工复查
        review_reason: 复查原因

    Returns:
        (needs_calibration: bool, reason: str)
        reason 将传递给 M2 诊断层作为诊断依据。
    """
    # 优先级 1: 需要人工复查 → 一定进入校准管线
    if needs_manual_review:
        reason = f"需人工复查: {review_reason}" if review_reason else REASON_MAP["review"]
        return True, reason

    # 优先级 2: UCS=0 (Overconfident) 或 UCS=1 (Pseudo-precise)
    if ucs_score == 0:
        return True, REASON_MAP["ucs0"]

    if ucs_score == 1:
        return True, REASON_MAP["ucs1"]

    # UCS=2 (Hedged) 和 UCS=3 (Calibrated) 均不需要校准
    # Hedged 的修正方向是"增加置信度"，由独立分支处理，不进 M2-M4
    return False, ""


def detect(ucs_score: int, ecs_score: int = 0,
           needs_manual_review: bool = False,
           review_reason: str = "") -> CalibrationDecision:
    """
    返回 CalibrationDecision 枚举（比 tuple 更语义化）。

    用于需要区分"跳过/校准/回收"三种状态的上层调用。
    """
    should, reason = needs_calibration(
        ucs_score=ucs_score,
        ecs_score=ecs_score,
        needs_manual_review=needs_manual_review,
        review_reason=review_reason,
    )

    if needs_manual_review:
        return CalibrationDecision.REVIEW
    if should:
        return CalibrationDecision.CALIBRATE
    return CalibrationDecision.PASS
