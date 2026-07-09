"""
CheckMyCoach — Benchmark: calibrated vs uncalibrated

Compares UCS scores across two conditions for the same questions:
    1. Raw LLM (no evidence, no calibration) → UCS
    2. Calibrated (calibrate_full) → UCS

Outputs a report with per-question deltas and aggregate stats.
"""

import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Same 50 questions as dogfooding
QUESTIONS = [
    "Should I squat below parallel?",
    "Is it safe to deadlift every day?",
    "How many sets per exercise for muscle growth?",
    "Should beginners use free weights or machines?",
    "What is the ideal rep range for strength?",
    "Is cardio before or after weights better?",
    "How long should I rest between sets?",
    "Should I train to failure on every set?",
    "Is running daily safe for beginners?",
    "Should I run on a treadmill or outside?",
    "What is a good 5K time for a beginner?",
    "Is barefoot running better for your feet?",
    "How much cardio should I do per week?",
    "Is high-intensity interval training safe for older adults?",
    "Should I stretch before running?",
    "Is creatine safe for teenagers?",
    "How much protein do I need per day?",
    "Should I take BCAAs for muscle growth?",
    "Is intermittent fasting good for athletes?",
    "Should I eat before morning workouts?",
    "Are energy drinks safe before exercise?",
    "How much water should I drink during exercise?",
    "Is it safe to exercise with a cold?",
    "Should I exercise if my muscles are still sore?",
    "What are the warning signs of overtraining?",
    "Is it safe to run with knee pain?",
    "Should I lift weights if I have high blood pressure?",
    "Can exercise prevent heart disease?",
    "Is it safe to exercise in hot weather?",
    "Can pregnant women do strength training?",
    "Is exercise safe for people with diabetes?",
    "Should older adults lift heavy weights?",
    "Can children do resistance training?",
    "Is exercise safe for people with asthma?",
    "Should people with arthritis avoid exercise?",
    "Can people with back pain do deadlifts?",
    "How many rest days should I take per week?",
    "Is stretching after exercise important?",
    "Should I use foam rolling for recovery?",
    "Is ice bath or hot bath better for recovery?",
    "How much sleep do athletes need?",
    "Should I take rest weeks from training?",
    "Is massage good for muscle recovery?",
    "Should I take pre-workout supplements?",
    "Is caffeine before exercise safe?",
    "Do protein shakes help with muscle growth?",
    "Should I take vitamin D for athletic performance?",
    "Are beta-alanine supplements effective?",
    "Is it safe to take weight loss supplements?",
    "Should I take electrolytes during exercise?",
]


def _raw_llm(question: str) -> str:
    """Call LLM with NO evidence context (simulates user asking ChatGPT directly)."""
    import os
    import requests
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    url = "https://api.deepseek.com/chat/completions"

    prompt = (
        f"Answer the following fitness question concisely:\n\n"
        f"Question: {question}"
    )

    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1024,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def run_benchmark(max_q=None):
    """Run benchmark: raw LLM vs calibrated for each question."""
    from pipeline.agent_pipeline import calibrate
    from config import DEV

    questions = QUESTIONS[:max_q] if max_q else QUESTIONS
    results = []

    for i, q in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] {q[:50]}...")

        # Condition 1: Raw LLM
        t1 = time.time()
        raw_response = _raw_llm(q)
        raw_elapsed = time.time() - t1

        # Get raw UCS
        import sys as _sys
        _sys.path.insert(0, r"C:\Users\gbx12\projects\FitCalib-Bench")
        from evaluation.ucs_engine import evaluate_ucs
        raw_ucs = evaluate_ucs(response=raw_response, question=q).ucs_score

        # Condition 2: Calibrated
        t2 = time.time()
        cal_result = calibrate(response=raw_response, question=q, settings=DEV)
        cal_elapsed = time.time() - t2

        cal_ucs = cal_result.get("ucs_score", -1)
        cal_delta = cal_result.get("score_delta", 0)
        cal_needed = cal_result.get("needs_calibration", False)
        cal_ftype = cal_result.get("failure_type")
        m4_pass = cal_result.get("m4_passed", False)

        delta = cal_ucs - raw_ucs

        results.append({
            "question": q,
            "raw_response": raw_response[:100],
            "raw_ucs": int(raw_ucs),
            "cal_ucs": int(cal_ucs),
            "cal_delta": cal_delta,
            "cal_needed": cal_needed,
            "cal_failure_type": cal_ftype,
            "cal_m4_pass": m4_pass,
            "latency_raw_s": round(raw_elapsed, 1),
            "latency_cal_s": round(cal_elapsed, 1),
        })

        status = "CAL" if cal_needed else "PASS"
        print(f"  raw UCS={raw_ucs} -> cal UCS={cal_ucs} ({status}, delta {cal_delta:+.1f})")

    return results


def print_report(results):
    """Print benchmark report."""
    n = len(results)
    if n == 0:
        print("No results.")
        return

    print("\n" + "=" * 70)
    print("BENCHMARK REPORT: Raw LLM vs Calibrated")
    print("=" * 70)

    # UCS distribution comparison
    raw_dist = Counter(r["raw_ucs"] for r in results)
    cal_dist = Counter(r["cal_ucs"] for r in results)

    ucs_labels = {0: "Overconfident", 1: "Pseudo-precise", 2: "Hedged", 3: "Calibrated"}
    print("\nUCS Distribution:")
    print(f"  {'Score':<8} {'Label':<20} {'Raw':<8} {'Calibrated':<12}")
    print(f"  {'-'*48}")
    for score in [0, 1, 2, 3]:
        label = ucs_labels.get(score, "?")
        rpct = raw_dist.get(score, 0) / n * 100
        cpct = cal_dist.get(score, 0) / n * 100
        print(f"  {score:<8} {label:<20} {raw_dist.get(score, 0):<3} ({rpct:.0f}%)   {cal_dist.get(score, 0):<3} ({cpct:.0f}%)")

    # Aggregate delta
    deltas = [r["cal_ucs"] - r["raw_ucs"] for r in results]
    avg_delta = sum(deltas) / n
    improved = sum(1 for d in deltas if d > 0)
    worsened = sum(1 for d in deltas if d < 0)
    unchanged = sum(1 for d in deltas if d == 0)
    print(f"\nAggregate:")
    print(f"  Avg UCS delta: {avg_delta:+.3f}")
    print(f"  Improved: {improved}/{n} ({improved/n*100:.0f}%)")
    print(f"  Worsened: {worsened}/{n} ({worsened/n*100:.0f}%)")
    print(f"  Unchanged: {unchanged}/{n} ({unchanged/n*100:.0f}%)")

    # Calibration events
    cal_events = [r for r in results if r["cal_needed"]]
    if cal_events:
        print(f"\nCalibration triggered: {len(cal_events)}/{n}")
        ft_dist = Counter(r["cal_failure_type"] for r in cal_events)
        for ft, count in ft_dist.most_common():
            m4_pass_count = sum(1 for r in cal_events if r["cal_failure_type"] == ft and r["cal_m4_pass"])
            print(f"  {ft}: {count} (M4 pass: {m4_pass_count}/{count})")
        avg_cal_delta = sum(r["cal_delta"] for r in cal_events if r["cal_delta"]) / len(cal_events)
        print(f"  Avg score_delta: {avg_cal_delta:+.2f}")
    else:
        print("\nNo calibration events triggered.")

    # Questions with largest UCS improvement
    print(f"\nTop 5 improvements:")
    sorted_results = sorted(results, key=lambda r: r["cal_ucs"] - r["raw_ucs"], reverse=True)
    for r in sorted_results[:5]:
        d = r["cal_ucs"] - r["raw_ucs"]
        if d > 0:
            print(f"  +{d}: {r['question'][:60]}")

    # Latency
    avg_raw_lat = sum(r["latency_raw_s"] for r in results) / n
    avg_cal_lat = sum(r["latency_cal_s"] for r in results) / n
    print(f"\nLatency:")
    print(f"  Raw LLM: avg {avg_raw_lat:.1f}s")
    print(f"  Calibrated: avg {avg_cal_lat:.1f}s")
    print(f"  Overhead: {avg_cal_lat - avg_raw_lat:.1f}s (M1-M4 is ~0.05s, rest is LLM)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run first 10 only")
    args = parser.parse_args()

    if args.quick:
        results = run_benchmark(max_q=10)
    else:
        results = run_benchmark()

    print_report(results)

    # Save to file
    import json
    path = "benchmark_results.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "summary": {
            "n": len(results),
            "avg_delta": sum(r["cal_ucs"] - r["raw_ucs"] for r in results) / len(results) if results else 0,
            "improved": sum(1 for r in results if r["cal_ucs"] - r["raw_ucs"] > 0),
            "cal_events": sum(1 for r in results if r["cal_needed"]),
        }}, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {path}")
