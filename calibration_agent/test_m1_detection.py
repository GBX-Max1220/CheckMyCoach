"""
M1 检测层单元测试。
覆盖所有决策路径：
  - UCS=0 → calibrate
  - UCS=1 → calibrate
  - UCS=2 → pass（不论 ECS）
  - UCS=3 → pass
  - needs_manual_review → review（覆盖 UCS=2/3）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calibration_agent.m1_detection import needs_calibration, detect, CalibrationDecision


def test_ucs0_overconfident():
    should, reason = needs_calibration(ucs_score=0)
    assert should is True
    assert "过度自信" in reason


def test_ucs1_pseudo_precise():
    should, reason = needs_calibration(ucs_score=1)
    assert should is True
    assert "伪精确" in reason


def test_ucs2_hedged_no_ecs():
    """UCS=2, ECS=0 → 跳过（不因无证据引用就送校准管线）"""
    should, reason = needs_calibration(ucs_score=2, ecs_score=0)
    assert should is False, f"UCS=2 应跳过, 得到 {should}"
    assert reason == ""


def test_ucs2_hedged_with_ecs():
    """UCS=2, ECS=1 → 跳过"""
    should, reason = needs_calibration(ucs_score=2, ecs_score=1)
    assert should is False
    assert reason == ""


def test_ucs3_calibrated():
    should, reason = needs_calibration(ucs_score=3)
    assert should is False
    assert reason == ""


def test_manual_review():
    """needs_manual_review 覆盖 UCS=0~3"""
    for score in range(4):
        should, reason = needs_calibration(ucs_score=score, needs_manual_review=True)
        assert should is True, f"UCS={score} + needs_manual_review → True"


def test_review_reason_passthrough():
    """review_reason 透传到返回值"""
    should, reason = needs_calibration(ucs_score=3, needs_manual_review=True,
                                       review_reason="矛盾信号")
    assert "矛盾信号" in reason


def test_detect_calibrate():
    assert detect(ucs_score=0) == CalibrationDecision.CALIBRATE


def test_detect_pass():
    assert detect(ucs_score=3) == CalibrationDecision.PASS


def test_detect_review():
    assert detect(ucs_score=2, needs_manual_review=True) == CalibrationDecision.REVIEW


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        name = t.__name__.replace("test_", "")
        print(f"  ✅ {name}")
    print(f"\n🎯 全部 {len(tests)} 项测试通过")
