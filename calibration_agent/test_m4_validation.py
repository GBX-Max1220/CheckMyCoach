"""
M4 验证层测试：3 个通过案例 + 3 个回退案例。
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from m4_validation import validate, ABSOLUTE_TERMS

# ==================== 通过案例 ====================

def test_pass_template_dominance():
    """TEMPLATE_DOMINANCE 修正 → 验证通过"""
    original = "按摩疗法是目前公认最有效的运动恢复手段，没有任何其他恢复方法可以相比。"
    corrected = "按摩疗法在运动恢复中被广泛应用，一些研究表明可能有助于缓解酸痛，但效果因人而异。"
    result = validate(corrected, original)
    assert result.passed is True
    assert result.fallback_triggered is False
    assert result.final_text == corrected
    print("  ✅ TEMPLATE_DOMINANCE 修正通过")


def test_pass_cue_leakage():
    """CUE_LEAKAGE 修正 → 验证通过"""
    original = "科学研究表明38.7%的受试者获益，最佳压力为3.2kg/cm²。"
    corrected = "一些研究显示部分受试者可能获益，最佳压力因人而异。"
    result = validate(corrected, original)
    assert result.passed is True
    assert result.fallback_triggered is False
    assert result.final_text == corrected
    print("  ✅ CUE_LEAKAGE 修正通过")


def test_pass_context_mismatch():
    """CONTEXT_MISMATCH 修正 → 验证通过"""
    original = "力量训练绝对是最有效的降压方法。"
    corrected = "力量训练被认为是控制血压的一种有效方法，但效果因个体差异而不同。"
    result = validate(corrected, original)
    assert result.passed is True
    assert result.final_text == corrected
    print("  ✅ CONTEXT_MISMATCH 修正通过")


# ==================== 回退案例 ====================

def test_fallback_length_too_short():
    """修正过短 → 回退"""
    original = "按摩疗法是目前公认最有效的运动恢复手段，没有任何其他恢复方法可以与之相比。大量研究已经明确证实按摩的效果。"
    corrected = "太短"  # 2字 vs 原文约60字
    result = validate(corrected, original)
    assert result.passed is False
    assert result.fallback_triggered is True
    assert "长度" in result.fallback_reason
    assert result.final_text == original  # 回退为原文
    print("  ✅ 长度过短触发回退")


def test_fallback_length_too_long():
    """修正过长 → 回退"""
    original = "力量训练能降压。"
    corrected = "力量训练被认为是一种可能有效的降压方法。但需要注意，不同的人群对力量训练的反应存在显著差异。年龄、性别、基础血压水平、训练频率和强度都会影响最终效果。因此建议根据个人情况制定方案。此外，有氧运动也被证明对降压有效。综合来看，结合有氧和力量训练可能效果更佳。专业指导下进行训练更为安全。"
    result = validate(corrected, original)
    assert result.passed is False
    assert result.fallback_triggered is True
    assert "长度" in result.fallback_reason
    assert result.final_text == original
    print("  ✅ 长度过长触发回退")


def test_fallback_assertion_not_reduced():
    """修正后的绝对性词汇数不低于原文 → 回退"""
    original = "这项研究有一定参考价值。"
    corrected = "这项研究绝对是最重要的，所有研究者都必须参考。"
    result = validate(corrected, original)
    assert result.passed is False
    assert result.fallback_triggered is True
    assert "断言" in result.fallback_reason
    assert result.final_text == original
    print("  ✅ 断言未降低触发回退")


def test_fallback_empty():
    """修正为空 → 回退"""
    original = "按摩疗法有助恢复。"
    corrected = ""
    result = validate(corrected, original)
    assert result.passed is False
    assert result.fallback_triggered is True
    assert "空" in result.fallback_reason
    assert result.final_text == original
    print("  ✅ 空文本触发回退")


def test_fallback_too_similar():
    """修正与原文几乎相同 → 回退"""
    original = "按摩疗法可能有助恢复，但效果因人而异。"
    corrected = "按摩疗法可能有助恢复，但效果因人而异。"  # 完全一样
    result = validate(corrected, original)
    assert result.passed is False
    assert result.fallback_triggered is True
    assert "相似" in result.fallback_reason
    assert result.final_text == original
    print("  ✅ 过度相似触发回退")


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
    print(f"\n🎯 全部 {len(tests)} 项测试通过")
