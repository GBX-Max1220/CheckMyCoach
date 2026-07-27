# Current Pipeline Map

## Topology

```
                         ┌─────────────────────┐
                         │     CLI / MCP         │
                         │  calibrate_full(q)   │
                         │  calibrate(r, q)     │
                         └──────┬──────────────┘
                                │
                   ┌────────────┴────────────┐
                   │  calibrate_full() only  │
                   │                        │
                   │  Step 0a: Retriever     │
                   │  (KC keyword match)     │
                   │                        │
                   │  Step 0b: LLM generate  │
                   │  (DeepSeek Chat API)    │
                   └────────────┬────────────┘
                                │
                   ┌────────────┴────────────┐
                   │  calibrate() BOTH paths │
                   │                        │
                   │  Step 1: UCS Engine     │
                   │  (FitCalib-Bench)       │
                   │                        │
                   │  Step 2: M1 Detection   │
                   │  (rule: UCS 0/1→cal)   │
                   │                        │
                   │  Step 3: M2 Diagnosis   │
                   │  (rule: features→type) │
                   │                        │
                   │  Step 4: M3 Correction  │
                   │  (LLM or prefix fb)    │
                   │                        │
                   │  Step 5: M4 Validation  │
                   │  (4 rule checks)       │
                   │                        │
                   │  Step 6: Score Delta    │
                   │  (2nd UCS call, approx)│
                   └────────────┬────────────┘
                                │
                   ┌────────────┴────────────┐
                   │    Audit Logger          │
                   │  (JSONL append)          │
                   └─────────────────────────┘
```

## Data Flow for One Case

```
Input: question="Should I squat below parallel?",
       response="Yes, squatting below parallel maximizes..."

Step 0a: Retrieve evidence
  → KC keyword match on question
  → Returns list[dict] max 5 items
  → Empty if match fails (silent degrade)

Step 1: UCS Engine
  → evaluate_ucs(response, question)
  → Returns UCSResult {ucs_score, extraction, needs_manual_review, ...}
  → extraction has 5 binary features: claims_superiority, has_directional_claim,
    mentions_no_difference, has_hedging, cites_evidence_type

Step 2: M1 Detection
  → needs_calibration(ucs_score, needs_manual_review)
  → Returns (bool, reason_str)
  → UCS=0 or 1 → calibrate. UCS=2 or 3 → pass.

Step 3: M2 Diagnosis (only if M1=calibrate)
  → diagnose(ucs_score, 5 extraction features)
  → Returns DiagnosisResult {failure_type, confidence, evidence, raw_features}
  → Three types: TEMPLATE_DOMINANCE, CUE_LEAKAGE, CONTEXT_MISMATCH

Step 4: M3 Correction (only if M1=calibrate)
  → correct(failure_type, response_text)
  → Builds prompt from hardcoded template, calls GPT-4o-mini via OpenRouter
  → Falls back to prefix prepend if LLM fails

Step 5: M4 Validation (only if M1=calibrate)
  → validate(corrected_text, original_text)
  → 4 checks: length (0.5x-6x), assertion count ≤ original, non-empty,
    character overlap < 0.9
  → Returns ValidationResult {final_text, fallback_triggered}

Step 6: Score Delta
  → Second evaluate_ucs(corrected_text, question)
  → delta = after - before (approximate, has measurement noise)
```

## Current Output Schema (`CalibrateResult` from `schema.py`)

```python
{
    "success": bool,          # Pipeline completed normally
    "error": str | None,      # PIPELINE_ERROR: ... if failed
    "audit_id": str,          # cmc_20260709_120000_abcd1234
    "question": str,          # Original question
    "path": str,              # "calibrate" | "calibrate_full"
    "evidence": list[dict],   # Retrieved KC objects
    "response": str,          # Original response text
    "ucs_score": int,         # 0-3
    "extraction_features": dict | None,
    "needs_calibration": bool,
    "failure_type": str | None,  # TEMPLATE_DOMINANCE | CUE_LEAKAGE | CONTEXT_MISMATCH
    "m2_confidence": float | None,
    "corrected_response": str | None,
    "score_delta": float | None,
    "m4_passed": bool,
    "latency_ms": dict,
    "token_usage": dict | None,
    "pre_trust_score": float | None,    # placeholder
    "decision_change": bool | None,     # placeholder
    "user_profile": dict | None,        # placeholder
}
```

## What `calibrate()` Currently Produces vs Evaluation v1 Requires

| Eval v1 Field | Current Pipeline | Gap |
|---------------|-----------------|-----|
| `case_id` | None (audit_id exists `cmc_20260709_120000_...`) | Need structured case ID |
| `input_answer` | `response` in result ✅ | Same field |
| `failure_type` | `failure_type` (lowercase) ✅ | Mapping: `template_dominance`→`unsupported_factual_claim` etc. |
| `target_span` | Not tracked ❌ | Need detection span output |
| `retrieved_evidence` | `evidence` list ✅ | Same |
| `corrected_answer` | `corrected_response` ✅ | Same |
| `validation.target_failure_removed` | Not checked ❌ | M4 checks length/assertion/overlap only |
| `validation.supported_information_retained` | Not checked ❌ | No semantic preservation check |
| `validation.new_unsupported_claims` | Not checked ❌ | No new-claim injection check |
| `validation.boundary_preserved` | Not checked ❌ | Not applicable to all types |
| `trace.detection` | Not structured ❌ | M1 returns (bool, reason_str) |
| `trace.diagnosis` | `raw_features` + `evidence` ✅ | Structured but can be stored directly |
| `trace.retrieval` | Not logged ❌ | Query, match count, source IDs not stored |
| `trace.correction` | `latency_ms` only ❌ | Prompt, strategy, source needed |
| `trace.validation` | `checks` dict ✅ | Structured in ValidationResult.checks |
