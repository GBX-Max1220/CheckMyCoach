"""
从 12 条基材中筛选 M1→M2→M3 端到端测试样本。
选一条 TEMPLATE_DOMINANCE、一条 CUE_LEAKAGE、一条 CONTEXT_MISMATCH。
"""

import sys, csv, json
sys.path.insert(0, r"C:\Users\gbx12\projects\MaxFitCalib-Bench\FitRAG-Bench\evaluation")

from ucs_engine import stage1_pattern_match, stage3_map_to_ucs, ExtractionResult
sys.path.insert(0, r"C:\Users\gbx12\projects\CheckMyCoach")
from calibration_agent.m1_detection import needs_calibration
from calibration_agent.m2_diagnosis import diagnose

CSV_PATH = r"C:\Users\gbx12\projects\MaxFitCalib-Bench\FitRAG-Bench\CheckMyCoach\刺激材料_12条基材.csv"

items = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        items.append(row)

results = []
for item in items:
    sid = item["source_id"]
    text = item["ai_response_raw"]

    # UCS Engine Stage 1: 模式匹配
    pattern = stage1_pattern_match(text)
    extraction = ExtractionResult(
        claims_superiority=pattern.has_superiority,
        has_directional_claim=pattern.has_directional,
        mentions_no_difference=pattern.has_no_difference,
        has_hedging=pattern.has_hedging,
        extraction_source="pattern_only",
        json_parse_success=True,
    )
    ucs_score = stage3_map_to_ucs(extraction)

    # M1 检测
    calibrate, m1_reason = needs_calibration(
        ucs_score=ucs_score,
        ecs_score=extraction.cites_evidence_type,
    )

    # 只打印需要校准的条目
    if calibrate:
        # M2 诊断
        diag = diagnose(
            ucs_score=ucs_score,
            claims_superiority=extraction.claims_superiority,
            has_directional_claim=extraction.has_directional_claim,
            mentions_no_difference=extraction.mentions_no_difference,
            has_hedging=extraction.has_hedging,
        )
        results.append((sid, ucs_score, diag.failure_type, diag.confidence, text[:80]))

    print(f"{sid:12s} UCS={ucs_score}  M1={'CALIBRATE' if calibrate else 'PASS':10s}  {m1_reason or ''}")

print(f"\n{'='*60}")
print(f"需要校准的条目：{len(results)} 条")
for sid, ucs, ftype, conf, preview in results:
    print(f"  {sid} UCS={ucs} → {ftype} (conf={conf}) | {preview}...")
