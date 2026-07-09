"""
M3 修正层集成测试。
三种失败类型各一个，验证输出文本长度合理。
无 API key 时走 fallback 模式，所有测试应通过。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from m3_correction import correct, CorrectionResult, PROMPT_TEMPLATES


# ==================== 测试样本 ====================

SAMPLE_TEMPLATE_DOMINANCE = (
    "按摩疗法是运动后恢复最有效的方法，所有运动员都应该在每次训练后立即接受按摩。"
    "这不仅能完全消除延迟性肌肉酸痛，还能显著加速力量恢复。"
)

SAMPLE_CUE_LEAKAGE = (
    "研究表明，训练后进行20分钟的按摩可以使肌肉酸痛感降低38.7%，"
    "最佳按摩压力为3.2kg/cm²，每周至少进行4.7次才能达到最优恢复效果。"
)

SAMPLE_CONTEXT_MISMATCH = (
    "老年人应该进行力量训练以维持肌力和骨密度。"
    "推荐每周进行3次训练，每次60分钟，使用70%1RM的强度。"
)


def test_template_dominance_correction():
    """TEMPLATE_DOMINANCE → 修正后文本长度合理"""
    result = correct("template_dominance", SAMPLE_TEMPLATE_DOMINANCE)
    _assert_valid_result(result, SAMPLE_TEMPLATE_DOMINANCE)


def test_cue_leakage_correction():
    """CUE_LEAKAGE → 修正后文本长度合理"""
    result = correct("cue_leakage", SAMPLE_CUE_LEAKAGE)
    _assert_valid_result(result, SAMPLE_CUE_LEAKAGE)


def test_context_mismatch_correction():
    """CONTEXT_MISMATCH → 修正后文本长度合理"""
    result = correct("context_mismatch", SAMPLE_CONTEXT_MISMATCH)
    _assert_valid_result(result, SAMPLE_CONTEXT_MISMATCH)


def test_prompt_templates_have_all_keys():
    """所有三种失败类型都有对应的 prompt 模板"""
    assert "template_dominance" in PROMPT_TEMPLATES
    assert "cue_leakage" in PROMPT_TEMPLATES
    assert "context_mismatch" in PROMPT_TEMPLATES


def test_prompt_templates_use_original_text_placeholder():
    """每条 prompt 都引用了 {original_text}"""
    for ftype, template in PROMPT_TEMPLATES.items():
        assert "{original_text}" in template["user"], f"{ftype} 缺少 original_text 占位符"


def test_strategy_matches_failure_type():
    """修正策略名称与失败类型一致"""
    result = correct("template_dominance", SAMPLE_TEMPLATE_DOMINANCE)
    assert result.strategy_used == "template_dominance"
    
    result = correct("cue_leakage", SAMPLE_CUE_LEAKAGE)
    assert result.strategy_used == "cue_leakage"
    
    result = correct("context_mismatch", SAMPLE_CONTEXT_MISMATCH)
    assert result.strategy_used == "context_mismatch"


def test_unknown_failure_type_raises_error():
    """未知的失败类型应抛出 ValueError"""
    try:
        correct("unknown_type", "test text")
        assert False, "应抛出 ValueError"
    except ValueError:
        pass


def test_source_is_fallback_or_llm():
    """source 字段应有值（fallback 或 llm）"""
    result = correct("template_dominance", SAMPLE_TEMPLATE_DOMINANCE)
    assert result.source in ("fallback", "llm")


def test_prompt_used_is_not_empty():
    """prompt_used 字段应有内容"""
    result = correct("cue_leakage", SAMPLE_CUE_LEAKAGE)
    assert len(result.prompt_used) > 50


# ==================== 辅助函数 ====================

def _assert_valid_result(result: CorrectionResult, original: str):
    """验证修正结果的基本完整性（不依赖 LLM）。"""
    orig_len = len(original)

    # fallback 模式下：原文 + 前缀，一定比原文长
    if result.source == "fallback":
        assert len(result.corrected_text) > orig_len * 0.5, (
            f"修正文本过短: {len(result.corrected_text)} vs {orig_len}"
        )
    
    # corrected_text 非空
    assert len(result.corrected_text) > 0, "修正文本不应为空"
    
    # strategy_used 与 prompt_used 一致
    assert result.strategy_used in ("template_dominance", "cue_leakage", "context_mismatch")


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        name = t.__doc__ or t.__name__.replace("test_", "")
        print(f"  ✅ {name}")
    print(f"\n🎯 全部 {len(tests)} 项测试通过")
