"""
完整管线端到端测试：M1 → M2 → M3 → M4
3 条样本：RCV-006 Overconfident, RCV-006 Pseudo-precise, SYNTHETIC ContextMismatch
"""

import sys, csv
sys.path.insert(0, r"C:\Users\gbx12\projects\FitCalib-Bench\CheckMyCoach")
from calibration_agent.m1_detection import needs_calibration
from calibration_agent.m2_diagnosis import diagnose
from calibration_agent.m3_correction import correct
from calibration_agent.m4_validation import validate

CSV = r"C:\Users\gbx12\projects\FitCalib-Bench\CheckMyCoach\刺激材料_48条_验证版.csv"

items = []
with open(CSV, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        items.append(row)

# 从 CSV 中找出指定条目
def find(source_id, category):
    for r in items:
        if r["source_id"] == source_id and r["ucs_category"] == category:
            return r["stimulus_text"], r["source_id"]
    return None, None

# ==================== 构造 3 条样本 ====================

over_text, _ = find("RCV-006", "Overconfident")
pseu_text, _ = find("RCV-006", "Pseudo-precise")

samples = []

# 1. TEMPLATE_DOMINANCE: RCV-006 Overconfident
samples.append({
    "name": "TEMPLATE_DOMINANCE — RCV-006 Overconfident",
    "text": over_text,
    "ucs_feats": {"ucs_score": 0, "claims_superiority": True, "cites_evidence_type": False},
    "manual_review": False,
})

# 2. CUE_LEAKAGE: RCV-006 Pseudo-precise
samples.append({
    "name": "CUE_LEAKAGE — RCV-006 Pseudo-precise",
    "text": pseu_text,
    "ucs_feats": {"ucs_score": 1, "has_directional_claim": True, "has_hedging": True, "cites_evidence_type": False},
    "manual_review": False,
})

# 3. CONTEXT_MISMATCH: 构造的矛盾案例
samples.append({
    "name": "CONTEXT_MISMATCH — 矛盾特征 + 需复查",
    "text": "大量研究表明力量训练就是控制血压最有效的方法，效果远胜有氧运动。但同时大量研究也显示有氧运动和力量训练在降压效果上没有显著差异。",
    "ucs_feats": {"ucs_score": 3, "claims_superiority": True, "mentions_no_difference": True, "cites_evidence_type": False},
    "manual_review": True,
    "review_reason": "矛盾特征: superiority claim + no-difference statement 并存",
})


# ==================== 运行管线 ====================

def run_pipeline(sample):
    text = sample["text"]
    feats = sample["ucs_feats"]
    name = sample["name"]

    print(f"\n{'=' * 66}")
    print(f"📦 {name}")
    print(f"{'=' * 66}")
    print(f"\n📝 原文 ({len(text)} 字): {text}")

    # --- M1 检测 ---
    if sample.get("manual_review"):
        cal, m1_reason = needs_calibration(
            ucs_score=feats["ucs_score"],
            needs_manual_review=True,
            review_reason=sample.get("review_reason", ""),
        )
    else:
        cal, m1_reason = needs_calibration(ucs_score=feats["ucs_score"])

    print(f"\n🔍 M1 检测层: {'需要校准' if cal else '跳过'}")
    print(f"   理由: {m1_reason}")

    if not cal:
        print(f"\n  → 管线终止（无需校准），最终输出 = 原始文本")
        return text, "pass", "", "", text

    # --- M2 诊断 ---
    if sample.get("manual_review"):
        diag = diagnose(
            ucs_score=feats["ucs_score"],
            claims_superiority=feats.get("claims_superiority", False),
            mentions_no_difference=feats.get("mentions_no_difference", False),
            needs_manual_review=True,
            review_reason=sample.get("review_reason", ""),
        )
    elif feats.get("ucs_score") == 0:
        diag = diagnose(
            ucs_score=0,
            claims_superiority=feats.get("claims_superiority", False),
            cites_evidence_type=feats.get("cites_evidence_type", False),
        )
    elif feats.get("ucs_score") == 1:
        diag = diagnose(
            ucs_score=1,
            has_directional_claim=feats.get("has_directional_claim", False),
            has_hedging=feats.get("has_hedging", False),
        )
    else:
        diag = diagnose(ucs_score=feats["ucs_score"])

    print(f"\n🔬 M2 诊断层: {diag.failure_type} (置信度: {diag.confidence})")
    for e in diag.evidence:
        print(f"   ├ {e}")

    # --- M3 修正 ---
    result = correct(diag.failure_type, text)

    print(f"\n✏️  M3 修正层: source={result.source}")
    print(f"   策略: {result.strategy_used}")
    print(f"   修正后 ({len(result.corrected_text)} 字):")
    print(f"   {result.corrected_text}")

    # --- M4 验证 ---
    vr = validate(result.corrected_text, text)

    print(f"\n✅ M4 验证层:")
    print(f"   长度: 原文{len(text)}字 → 修正{len(result.corrected_text)}字 "
          f"(比值 {len(result.corrected_text)/max(len(text),1):.2f}, "
          f"{'✅' if vr.checks['length']['passed'] else '❌'} 阈值0.5-4.0)")
    cnt_orig = vr.checks["assertion"]["original_count"]
    cnt_corr = vr.checks["assertion"]["corrected_count"]
    print(f"   断言: 原文{cnt_orig}个绝对词 → 修正{cnt_corr}个 "
          f"({'✅' if vr.checks['assertion']['passed'] else '❌'} 需≤原文)")
    print(f"   非空: {'✅' if vr.checks['non_empty']['passed'] else '❌'}")
    overlap = vr.checks["non_copy"]["overlap_ratio"]
    print(f"   非复制: 字符重叠比 {overlap:.3f} "
          f"({'✅' if vr.checks['non_copy']['passed'] else '❌'} 需<0.9)")

    if vr.fallback_triggered:
        print(f"\n⚠️  回退触发！原因: {vr.fallback_reason}")
    else:
        print(f"\n✅ 全部验证通过，管线正常输出")

    print(f"\n📤 最终输出 ({len(vr.final_text)} 字):")
    print(f"   {vr.final_text}")

    return text, diag.failure_type, result.corrected_text, vr, vr.final_text


# ==================== 主执行 ====================

print("=" * 66)
print("  CheckMyCoach 校准管线 — 端到端测试")
print("  M1 → M2 → M3 → M4")
print("=" * 66)

results = []
for sample in samples:
    result = run_pipeline(sample)
    results.append((sample["name"], result))

# 汇总
print(f"\n\n{'=' * 66}")
print("  汇总")
print(f"{'=' * 66}")
print(f"{'样本':40s} {'M2诊断':25s} {'M4结果':10s}")
print(f"{'─'*40} {'─'*25} {'─'*10}")
for name, (orig, ftype, corrected, vr, final) in results:
    status = "✅ 通过" if vr.passed else "⚠️ 回退"
    print(f"{name:40s} {ftype:25s} {status:10s}")
