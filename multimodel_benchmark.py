"""
Multi-model benchmark: compare UCS distributions across models.

Runs 10 questions through 3 model backends via OpenRouter,
saves UCS scores and audit data.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

QUESTIONS = [
    "Should I squat below parallel?",
    "Is it safe to deadlift every day?",
    "How much protein do I need per day?",
    "Is creatine safe for teenagers?",
    "Is running daily safe for beginners?",
    "Should I exercise with a cold?",
    "Can pregnant women do strength training?",
    "Is massage good for muscle recovery?",
    "Should I take pre-workout supplements?",
    "How many rest days should I take per week?",
]

def call_model(question: str, model_id: str) -> dict:
    """Call model via OpenRouter."""
    from dotenv import load_dotenv
    import requests
    load_dotenv()
    key = os.getenv("OPENROUTER_API_KEY")
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model_id,
            "messages": [{"role": "user", "content": question}],
            "temperature": 0.3,
            "max_tokens": 512,
        },
        timeout=120,
    )
    data = resp.json()
    return {
        "text": data["choices"][0]["message"]["content"],
        "usage": data.get("usage", {}),
    }

def run_benchmark():
    models = [
        "deepseek/deepseek-chat",
        "google/gemini-3-flash",
        "anthropic/claude-sonnet-4",
    ]

    sys.path.insert(0, r"C:\Users\gbx12\projects\FitCalib-Bench")
    from evaluation.ucs_engine import evaluate_ucs

    results = []
    for model in models:
        print(f"\n=== Model: {model} ===")
        for i, q in enumerate(QUESTIONS):
            print(f"  [{i+1}/{len(QUESTIONS)}] {q[:40]}...", end=" ")
            sys.stdout.flush()
            try:
                out = call_model(q, model)
                raw = out["text"]
                ucs = evaluate_ucs(response=raw, question=q)
                results.append({
                    "model": model,
                    "question": q,
                    "ucs_score": int(ucs.ucs_score),
                    "stage": ucs.stage_used,
                    "response_preview": raw[:100],
                })
                print(f"UCS={ucs.ucs_score} ({ucs.stage_used})")
            except Exception as e:
                print(f"ERROR: {e}")
                results.append({"model": model, "question": q, "ucs_score": -1, "stage": "error", "error": str(e)})

    # Summary
    print("\n" + "=" * 60)
    print("MULTI-MODEL BENCHMARK RESULTS")
    print("=" * 60)
    from collections import Counter
    for model in models:
        model_results = [r for r in results if r["model"] == model]
        valid = [r for r in model_results if r["ucs_score"] >= 0]
        if not valid:
            print(f"\n{model}: ALL FAILED")
            continue
        dist = Counter(r["ucs_score"] for r in valid)
        mean_ucs = sum(r["ucs_score"] for r in valid) / len(valid)
        trigger_rate = sum(1 for r in valid if r["ucs_score"] in (0, 1)) / len(valid) * 100
        print(f"\n{model} ({len(valid)}/{len(model_results)} ok):")
        print(f"  Mean UCS: {mean_ucs:.2f}")
        print(f"  Trigger rate (UCS=0/1): {trigger_rate:.0f}%")
        for score in [0, 1, 2, 3]:
            print(f"  UCS={score}: {dist.get(score, 0)} ({dist.get(score, 0)/len(valid)*100:.0f}%)")

    path = "multimodel_benchmark.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {path}")

if __name__ == "__main__":
    run_benchmark()
