"""
CheckMyCoach — 50-question dogfooding batch

Runs 50 fitness questions through calibrate_full,
collects audit data, produces stats report.

Usage:
    python batch_dogfood.py              # run all 50
    python batch_dogfood.py --quick      # run first 10 only
    python batch_dogfood.py --analyze    # re-analyze existing audit data
"""

import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === 50 FITNESS QUESTIONS (8 categories) ===

QUESTIONS = [
    # --- Training basics (8) ---
    "Should I squat below parallel?",
    "Is it safe to deadlift every day?",
    "How many sets per exercise for muscle growth?",
    "Should beginners use free weights or machines?",
    "What is the ideal rep range for strength?",
    "Is cardio before or after weights better?",
    "How long should I rest between sets?",
    "Should I train to failure on every set?",

    # --- Running & Cardio (7) ---
    "Is running daily safe for beginners?",
    "Should I run on a treadmill or outside?",
    "What is a good 5K time for a beginner?",
    "Is barefoot running better for your feet?",
    "How much cardio should I do per week?",
    "Is high-intensity interval training safe for older adults?",
    "Should I stretch before running?",

    # --- Nutrition (7) ---
    "Is creatine safe for teenagers?",
    "How much protein do I need per day?",
    "Should I take BCAAs for muscle growth?",
    "Is intermittent fasting good for athletes?",
    "Should I eat before morning workouts?",
    "Are energy drinks safe before exercise?",
    "How much water should I drink during exercise?",

    # --- Safety & Injury (7) ---
    "Is it safe to exercise with a cold?",
    "Should I exercise if my muscles are still sore?",
    "What are the warning signs of overtraining?",
    "Is it safe to run with knee pain?",
    "Should I lift weights if I have high blood pressure?",
    "Can exercise prevent heart disease?",
    "Is it safe to exercise in hot weather?",

    # --- Special Populations (7) ---
    "Can pregnant women do strength training?",
    "Is exercise safe for people with diabetes?",
    "Should older adults lift heavy weights?",
    "Can children do resistance training?",
    "Is exercise safe for people with asthma?",
    "Should people with arthritis avoid exercise?",
    "Can people with back pain do deadlifts?",

    # --- Recovery (7) ---
    "How many rest days should I take per week?",
    "Is stretching after exercise important?",
    "Should I use foam rolling for recovery?",
    "Is ice bath or hot bath better for recovery?",
    "How much sleep do athletes need?",
    "Should I take rest weeks from training?",
    "Is massage good for muscle recovery?",

    # --- Supplements & Performance (7) ---
    "Should I take pre-workout supplements?",
    "Is caffeine before exercise safe?",
    "Do protein shakes help with muscle growth?",
    "Should I take vitamin D for athletic performance?",
    "Are beta-alanine supplements effective?",
    "Is it safe to take weight loss supplements?",
    "Should I take electrolytes during exercise?",
]


def run_batch(max_q=None, audit_path="audit/dogfood_trails.jsonl"):
    """Run questions through pipeline, collect audit data."""
    from pipeline.agent_pipeline import calibrate_full
    from config import Settings

    cfg = Settings(audit_path=audit_path, enable_audit=True)
    questions = QUESTIONS[:max_q] if max_q else QUESTIONS

    results = []
    for i, q in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] {q[:50]}...", end=" ")
        sys.stdout.flush()
        t0 = time.time()
        try:
            result = calibrate_full(question=q, settings=cfg)
            elapsed = time.time() - t0
            status = "OK" if result.get("success") else "ERR"
            ucs = result.get("ucs_score", "?")
            print(f"{status} UCS={ucs} ({elapsed:.1f}s)")
            results.append(result)
        except Exception as exc:
            elapsed = time.time() - t0
            print(f"FAIL ({elapsed:.1f}s): {exc}")
            results.append({"success": False, "error": str(exc), "question": q})

    return results


def analyze_audit(audit_path="audit/dogfood_trails.jsonl"):
    """Analyze collected audit data."""
    if not os.path.exists(audit_path):
        print(f"No audit data found at {audit_path}")
        return

    records = []
    with open(audit_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    n = len(records)
    if n == 0:
        print("No audit records found.")
        return

    print("=" * 60)
    print("Dogfooding Report: %d questions" % n)
    print("=" * 60)
    print()

    # Success rate
    successes = [r for r in records if "error" not in r or r.get("error") is None]
    print("Success rate: %d/%d (%.1f%%)" % (len(successes), n, len(successes)/n*100))

    # UCS distribution
    ucs_scores = [r.get("ucs_score", -1) for r in records if r.get("ucs_score") is not None and r["ucs_score"] >= 0]
    ucs_labels = {0: "Overconfident", 1: "Pseudo-precise", 2: "Hedged", 3: "Calibrated"}
    if ucs_scores:
        ucs_dist = Counter(ucs_scores)
        print("\nUCS Distribution:")
        for score in sorted(ucs_dist):
            label = ucs_labels.get(score, f"Level {score}")
            pct = ucs_dist[score] / len(ucs_scores) * 100
            print("  %d (%s): %d (%.1f%%)" % (score, label, ucs_dist[score], pct))
    else:
        print("\nUCS scores not found in audit records.")

    # Failure types
    failures = [r.get("m2_failure_type") for r in records if r.get("m2_failure_type")]
    if failures:
        ft_dist = Counter(failures)
        print("\nFailure Type Distribution:")
        for ft, count in ft_dist.most_common():
            print("  %s: %d" % (ft, count))

    # Latency
    latencies = [r.get("latency_ms", {}) for r in records if r.get("latency_ms")]
    if latencies:
        print("\nLatency (ms):")
        for key in ["retriever", "llm", "ucs_engine", "m1", "m2", "m3", "m4"]:
            vals = [l.get(key, 0) for l in latencies if l.get(key)]
            if vals:
                avg = sum(vals) / len(vals)
                print("  %s: avg %.0fms (min %.0f, max %.0f)" % (key, avg, min(vals), max(vals)))
        totals = [sum(v for v in l.values() if isinstance(v, (int, float))) for l in latencies]
        if totals:
            print("  total: avg %.0fms" % (sum(totals)/len(totals)))

    # Token usage
    token_records = [r.get("token_usage", {}) for r in records if r.get("token_usage")]
    if token_records:
        total_cost = sum(t.get("cost", 0) for t in token_records)
        print("\nAPI Cost: $%.4f total (%.4f avg per question)" % (
            total_cost, total_cost / len(token_records)))

    print()
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run first 10 only")
    parser.add_argument("--analyze", action="store_true", help="Re-analyze existing audit data")
    args = parser.parse_args()

    if args.analyze:
        analyze_audit()
    elif args.quick:
        results = run_batch(max_q=10)
    else:
        results = run_batch()
