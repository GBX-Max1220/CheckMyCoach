#!/usr/bin/env python
"""
CheckMyCoach CLI — 命令行校准入口。

Usage:
    python -m checkmycoach "Should I squat below parallel?"
    python -m checkmycoach "Should I squat below parallel?" --json
    python -m checkmycoach "Should I squat below parallel?" --no-audit

Architecture Decisions:
    - JSON 输出优先（ChatGPT v2 review 建议）。默认 pretty print，--json 输出纯 JSON。
    - 支持 --no-audit（ChatGPT v2 review 建议），调试时避免产生大量 JSONL。
    - 统一错误格式 {success, result, error, audit_id}（ChatGPT v2 review 建议）。
"""

import argparse
import json
import sys
import os

# __init__.py 让 python -m checkmycoach 能 work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description="CheckMyCoach — AI fitness advice calibration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m checkmycoach \"Should I squat below parallel?\"\n"
            "  python -m checkmycoach \"Should I squat below parallel?\" --json\n"
            "  python -m checkmycoach \"Is running daily safe?\" --no-audit"
        ),
    )
    parser.add_argument("question", nargs="?", help="The fitness question to calibrate")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON (pipeable to jq)")
    parser.add_argument("--no-audit", action="store_true",
                        help="Skip writing audit JSONL")
    parser.add_argument("--model", default=None,
                        help="Override LLM model (default: deepseek-chat)")

    args = parser.parse_args()

    if not args.question:
        parser.print_help()
        sys.exit(1)

    # 配置
    from config import DEV, Settings
    cfg = DEV
    if args.no_audit:
        cfg = Settings(enable_audit=False)
    if args.model:
        cfg = Settings(model=args.model, enable_audit=cfg.enable_audit)

    # 跑管线
    from pipeline.agent_pipeline import calibrate_full
    result = calibrate_full(question=args.question, settings=cfg)

    # 输出
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _pretty_print(result)


def _pretty_print(result: dict):
    """Human-readable output."""
    if not result.get("success"):
        print("[Error]", result.get("error", "Unknown error"))
        if result.get("audit_id"):
            print("   audit_id:", result["audit_id"])
        return

    print("=" * 60)
    print("CheckMyCoach - Calibration Report")
    print("=" * 60)
    print()
    print("Question:  %s" % result.get("question", "?"))
    print("Audit ID:  %s" % result.get("audit_id", "?"))
    print()

    # Evidence
    evidence = result.get("evidence", [])
    if evidence:
        print("Evidence sources:")
        for e in evidence:
            print("  - [%s] %s" % (e.get("id", "?"), e.get("source", "")))
    else:
        print("Evidence:  none found")
    print()

    # UCS
    ucs = result.get("ucs_score", -1)
    ucs_labels = {0: "Overconfident", 1: "Pseudo-precise", 2: "Hedged", 3: "Calibrated"}
    print("UCS Score: %d (%s)" % (ucs, ucs_labels.get(ucs, "Unknown")))

    # Calibration decision
    if result.get("needs_calibration"):
        ft = result.get("failure_type", "?")
        print("Decision:  NEEDS CALIBRATION (%s, conf=%.2f)" % (
            ft, result.get("m2_confidence", 0)))
    else:
        print("Decision:  PASS (no calibration needed)")
    print()

    # Corrected response
    orig = result.get("response")
    corrected = result.get("corrected_response")
    if corrected and corrected != orig:
        print("Original:")
        print("  " + ((orig[:200] + "...") if len(orig or "") > 200 else orig))
        print()
        print("Calibrated:")
        print("  " + ((corrected[:200] + "...") if len(corrected or "") > 200 else corrected))
        if result.get("score_delta") is not None:
            print("  (UCS delta: %+.1f - approximate)" % result["score_delta"])
    elif orig:
        print("Response:")
        print("  " + ((orig[:200] + "...") if len(orig) > 200 else orig))
    print()

    # Latency
    lat = result.get("latency_ms", {})
    if lat and lat.get("total", 0) > 0:
        print("Latency:  %.0fms total" % lat["total"])
        for step, ms in sorted(lat.items()):
            if step != "total" and ms:
                print("          %s: %.0fms" % (step, ms))

    print("=" * 60)


if __name__ == "__main__":
    main()
