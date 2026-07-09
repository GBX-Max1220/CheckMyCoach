"""
M2 诊断层单元测试。
覆盖三种失败类型各至少 2 个案例 + 边界情况。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calibration_agent.m2_diagnosis import diagnose, FailureType


# ===================== TEMPLATE_DOMINANCE =====================

def test_template_dominance_typical():
    """claims_superiority=True + cites_evidence=False → TEMPLATE_DOMINANCE"""
    result = diagnose(
        ucs_score=0,
        claims_superiority=True,
        cites_evidence_type=False,
    )
    assert result.failure_type == FailureType.TEMPLATE_DOMINANCE.value
    assert result.confidence >= 0.6
    assert len(result.evidence) >= 1


def test_template_dominance_overconfident_only():
    """UCS=0, 无条件声明特征 → 保守诊断为 TEMPLATE_DOMINANCE"""
    result = diagnose(
        ucs_score=0,
        claims_superiority=False,
        cites_evidence_type=False,
    )
    assert result.failure_type == FailureType.TEMPLATE_DOMINANCE.value
    assert result.confidence == 0.5


def test_template_dominance_with_evidence_citation():
    """claims_superiority=True + cites_evidence=True → 不是模板优越"""
    result = diagnose(
        ucs_score=0,
        claims_superiority=True,
        cites_evidence_type=True,
    )
    # 有证据引用，不走 TEMPLATE_DOMINANCE → 进入 CUE_LEAKAGE 判断
    # 但 UCS=0 且无 directional_claim → 兜底回 TEMPLATE_DOMINANCE
    assert result.confidence == 0.5


# ===================== CUE_LEAKAGE =====================

def test_cue_leakage_typical():
    """UCS=1 + directional → CUE_LEAKAGE"""
    result = diagnose(
        ucs_score=1,
        has_directional_claim=True,
        claims_superiority=False,
    )
    assert result.failure_type == FailureType.CUE_LEAKAGE.value
    assert result.confidence >= 0.8
    assert any("伪精确" in e for e in result.evidence)


def test_cue_leakage_with_precise_numbers():
    """UCS=1 + directional + 无证据 → CUE_LEAKAGE, 高置信度"""
    result = diagnose(
        ucs_score=1,
        has_directional_claim=True,
        cites_evidence_type=False,
    )
    assert result.failure_type == FailureType.CUE_LEAKAGE.value
    assert result.confidence >= 0.8


def test_cue_leakage_fallback():
    """UCS=1 但无方向性声明 → 保守诊断为 CUE_LEAKAGE"""
    result = diagnose(
        ucs_score=1,
        has_directional_claim=False,
    )
    assert result.failure_type == FailureType.CUE_LEAKAGE.value
    assert result.confidence == 0.5


# ===================== CONTEXT_MISMATCH =====================

def test_manual_review_modulates_template_dominance():
    """needs_manual_review=True + claims_superiority → TEMPLATE_DOMINANCE（不是 CONTEXT_MISMATCH）"""
    result = diagnose(
        ucs_score=0,
        claims_superiority=True,
        cites_evidence_type=False,
        needs_manual_review=True,
    )
    assert result.failure_type == FailureType.TEMPLATE_DOMINANCE.value
    assert result.confidence <= 0.6
    assert any("需人工复查" in e for e in result.evidence)


def test_manual_review_modulates_cue_leakage():
    """needs_manual_review=True + UCS=1/directional → CUE_LEAKAGE（不是 CONTEXT_MISMATCH）"""
    result = diagnose(
        ucs_score=1,
        has_directional_claim=True,
        needs_manual_review=True,
    )
    assert result.failure_type == FailureType.CUE_LEAKAGE.value
    assert result.confidence <= 0.6
    assert any("需人工复查" in e for e in result.evidence)


def test_manual_review_no_features_context_mismatch():
    """needs_manual_review=True + 无明确特征 → CONTEXT_MISMATCH, 0.5"""
    result = diagnose(
        ucs_score=3,
        needs_manual_review=True,
    )
    assert result.failure_type == FailureType.CONTEXT_MISMATCH.value
    assert result.confidence == 0.5


def test_context_mismatch_contradictory():
    """claims_superiority + mentions_no_difference → CONTEXT_MISMATCH"""
    result = diagnose(
        ucs_score=0,
        claims_superiority=True,
        mentions_no_difference=True,
    )
    assert result.failure_type == FailureType.CONTEXT_MISMATCH.value
    assert result.confidence >= 0.7


def test_manual_review_hedged_no_features():
    """UCS=2 + needs_manual_review=True + 无特征 → CONTEXT_MISMATCH"""
    result = diagnose(
        ucs_score=2,
        needs_manual_review=True,
    )
    # UCS=2 不走兜底规则，failure 保持 UNKNOWN
    # needs_manual_review 将 UNKNOWN → CONTEXT_MISMATCH
    assert result.failure_type == FailureType.CONTEXT_MISMATCH.value
    assert result.confidence == 0.5
    assert any("未指定" in e for e in result.evidence)


# ===================== BOUNDARY =====================

def test_unknown_fallback():
    """无任何匹配特征 → UNKNOWN"""
    result = diagnose(
        ucs_score=3,
        claims_superiority=False,
        has_directional_claim=False,
        cites_evidence_type=True,
    )
    assert result.failure_type == FailureType.UNKNOWN.value
    assert result.confidence == 0.0


def test_raw_features_included():
    """raw_features 包含所有 extraction 字段"""
    result = diagnose(
        ucs_score=0,
        claims_superiority=True,
        cites_evidence_type=False,
    )
    assert "ucs_score" in result.raw_features
    assert "claims_superiority" in result.raw_features
    assert result.raw_features["ucs_score"] == 0
    assert result.raw_features["claims_superiority"] is True


def test_manual_review_does_not_override_features():
    """manual_review 不覆盖特征诊断，仅降低置信度"""
    result = diagnose(
        ucs_score=1,
        claims_superiority=True,
        has_directional_claim=True,
        needs_manual_review=True,
    )
    # claims_superiority=True → TEMPLATE_DOMINANCE（规则2 先于规则3）
    assert result.failure_type == FailureType.TEMPLATE_DOMINANCE.value
    assert result.confidence <= 0.6
    assert any("需人工复查" in e for e in result.evidence)


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        name = t.__doc__ or t.__name__.replace("test_", "")
        print(f"  ✅ {name}")
    print(f"\n🎯 全部 {len(tests)} 项测试通过")
