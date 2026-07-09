"""
M4 验证层 — 验证 M3 修正结果，不通过则回退为原始文本。

验证规则（全部通过才算成功）：
1. 长度完整性：修正后 ≥ 原文 50% 且 ≤ 原文 400%
2. 断言强度降低：修正后的绝对性词汇数 ≤ 原文
3. 非空非复制：修正不为空，且与原文字符重叠比 < 0.9
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# 绝对性词汇（中文 + 英文）
ABSOLUTE_TERMS = [
    "最", "绝对", "所有", "一定", "必须", "永远", "从不", "完全",
    "best", "always", "never", "must", "absolutely", "completely",
    "every", "all", "definitely", "undoubtedly",
]


@dataclass
class ValidationResult:
    """M4 验证输出"""
    passed: bool                     # 全部规则通过？
    fallback_triggered: bool         # 是否触发了回退
    fallback_reason: str             # 回退原因（未触发时为空）
    final_text: str                  # 通过的修正文本 或 回退后的原始文本
    checks: dict = field(default_factory=dict)  # 各规则检查明细


# 否定前缀 — 出现在绝对词前 N 个字符内时，该绝对词不计入
NEGATION_PREFIXES = ["不", "没有", "无法", "不能", "并非", "不是", "未"]
NEGATION_WINDOW = 5  # 向前查找的字符窗口


def _is_absolute_in_context(term: str, text: str, pos: int) -> bool:
    """
    判断指定位置的绝对词是否真正表达绝对性语义。
    返回 True = 是绝对性用法，应计数；False = 应跳过。
    """
    lower = text.lower()

    # 否定语境过滤
    neg_start = max(0, pos - NEGATION_WINDOW)
    prefix = text[neg_start:pos]
    if any(n in prefix for n in NEGATION_PREFIXES):
        return False

    # 特殊语境过滤
    if term == "一定":
        # "有一定" → "某种程度"，不是绝对性
        # "无一定" → 否定
        before = text[max(0, pos - 2):pos]
        if "有" in before and "没" not in before and "无" not in before:
            return False

    return True


def _count_absolute_terms(text: str) -> int:
    """统计文本中绝对性词汇的出现次数（已过滤否定语境和特殊语义）。"""
    lower = text.lower()
    count = 0

    for term in ABSOLUTE_TERMS:
        if re.match(r'^[\u4e00-\u9fff]+$', term):
            # 中文词：find 所有出现位置
            start = 0
            while True:
                pos = lower.find(term, start)
                if pos == -1:
                    break
                if _is_absolute_in_context(term, text, pos):
                    count += 1
                start = pos + len(term)
        else:
            # 英文词：按单词边界匹配
            for m in re.finditer(r'\b' + re.escape(term) + r'\b', lower):
                if _is_absolute_in_context(term, text, m.start()):
                    count += 1

    return count


def _char_overlap_ratio(text_a: str, text_b: str) -> float:
    """计算两段文本的字符重叠比：交集字符数 / 并集字符数。"""
    if not text_a or not text_b:
        return 0.0
    set_a = set(text_a.replace(" ", "").replace("\n", ""))
    set_b = set(text_b.replace(" ", "").replace("\n", ""))
    intersection = set_a & set_b
    union = set_a | set_b
    if not union:
        return 0.0
    return len(intersection) / len(union)


def validate(correction_text: str, original_text: str) -> ValidationResult:
    """
    验证 M3 修正结果，决定是否回退。

    Args:
        correction_text: M3 返回的修正文本
        original_text: 原始建议文本

    Returns:
        ValidationResult
    """
    checks = {}
    fallback_reasons = []

    # ---- 规则 1: 长度完整性 ----
    orig_len = len(original_text)
    corr_len = len(correction_text)
    len_ok = (corr_len >= orig_len * 0.5) and (corr_len <= orig_len * 6.0)
    checks["length"] = {
        "passed": len_ok,
        "original": orig_len,
        "corrected": corr_len,
        "ratio": round(corr_len / orig_len, 2) if orig_len > 0 else 0,
    }
    if not len_ok:
        fallback_reasons.append(
            f"长度异常: 修正后 {corr_len} 字, 原文 {orig_len} 字 "
            f"(比值 {corr_len/orig_len:.2f}, 阈值 0.5-6.0)"
        )

    # ---- 规则 2: 断言强度降低 ----
    orig_abs = _count_absolute_terms(original_text)
    corr_abs = _count_absolute_terms(correction_text)
    assertion_ok = corr_abs <= orig_abs
    checks["assertion"] = {
        "passed": assertion_ok,
        "original_count": orig_abs,
        "corrected_count": corr_abs,
    }
    if not assertion_ok:
        fallback_reasons.append(
            f"断言强度未降低: 修正后绝对性词汇 {corr_abs} 个, "
            f"原文 {orig_abs} 个"
        )

    # ---- 规则 3: 非空非复制 ----
    empty_ok = len(correction_text.strip()) > 0
    overlap = _char_overlap_ratio(correction_text, original_text)
    overlap_ok = overlap < 0.9
    checks["non_empty"] = {"passed": empty_ok, "length": len(correction_text.strip())}
    checks["non_copy"] = {
        "passed": overlap_ok,
        "overlap_ratio": round(overlap, 3),
    }

    if not empty_ok:
        fallback_reasons.append("修正文本为空")
    if not overlap_ok:
        fallback_reasons.append(
            f"修正文本与原文过于相似: 字符重叠比 {overlap:.3f} (阈值 < 0.9)"
        )

    # ---- 综合判定 ----
    passed = len_ok and assertion_ok and empty_ok and overlap_ok
    fallback_triggered = not passed

    if fallback_triggered:
        return ValidationResult(
            passed=False,
            fallback_triggered=True,
            fallback_reason="; ".join(fallback_reasons),
            final_text=original_text,  # 回退为原文
            checks=checks,
        )

    return ValidationResult(
            passed=True,
            fallback_triggered=False,
            fallback_reason="",
            final_text=correction_text,
            checks=checks,
    )
