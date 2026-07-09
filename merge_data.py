"""
Path B 数据合并工具。
将多个被试的 JSON 数据文件合并为一个 CSV，用于 LMM 分析。

用法：
    1. 将收到的所有 JSON 文件放入一个目录（如 data_raw/）
    2. python merge_data.py --input data_raw/ --output path_b_clean.csv
"""

import json, csv, os, glob, argparse, sys
from datetime import datetime


def merge(input_dir: str, output_csv: str):
    """合并目录下所有 JSON 数据文件。"""
    files = sorted(glob.glob(os.path.join(input_dir, "*.json")))
    if not files:
        print(f"未在 {input_dir} 中找到 JSON 文件")
        return

    all_rows = []
    errors = []

    for fpath in files:
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            errors.append((os.path.basename(fpath), f"读取失败: {e}"))
            continue

        verify_code = data.get("verifyCode", "unknown")
        tlx = data.get("tlx", {})
        total_time_s = round(data.get("totalTimeMs", 0) / 1000, 1)

        responses = data.get("responses", [])
        for r in responses:
            all_rows.append({
                "participant": verify_code,
                "item_idx": r.get("itemIdx", ""),
                "source": r.get("source", ""),
                "ucs_category": r.get("ucs", ""),
                "text": r.get("text", ""),
                "judge": r.get("judge", ""),
                "confidence": r.get("confidence", ""),
                "certainty": r.get("certainty", ""),
                "rt_ms": r.get("rtMs", ""),
                "attention_check": r.get("attentionCheck", False),
                "tlx_mental": tlx.get("mental", ""),
                "tlx_effort": tlx.get("effort", ""),
                "tlx_frustration": tlx.get("frustration", ""),
                "total_time_s": total_time_s,
            })

    # 写 CSV
    if not all_rows:
        print("无有效数据")
        return

    fields = [
        "participant", "item_idx", "source", "ucs_category", "text",
        "judge", "confidence", "certainty", "rt_ms", "attention_check",
        "tlx_mental", "tlx_effort", "tlx_frustration", "total_time_s",
    ]

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)

    # 报告
    n_subj = len(set(r["participant"] for r in all_rows))
    n_items = len(all_rows)
    print(f"✅ 合并完成")
    print(f"   被试数: {n_subj}")
    print(f"   总行数: {n_items}")
    print(f"   输出: {output_csv}")
    if errors:
        print(f"   错误 ({len(errors)}):")
        for name, reason in errors:
            print(f"     - {name}: {reason}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Path B 数据合并工具")
    parser.add_argument("--input", default="data_raw",
                        help="JSON 文件所在目录")
    parser.add_argument("--output", default="path_b_clean.csv",
                        help="输出 CSV 路径")
    args = parser.parse_args()
    merge(args.input, args.output)
