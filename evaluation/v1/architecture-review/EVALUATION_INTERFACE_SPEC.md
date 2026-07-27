# Evaluation v1 — Interface Specification

## One-Case Input/Output Record

Based on the existing `CalibrateResult` TypedDict in `schema.py` and the Evaluation v1 requirements, the stable minimum interface for one evaluation case:

```python
{
    # ── Case Identity ──
    "case_id": "NUM-001",                    # Required. {FAMILY}-{NNN}
    "failure_family": "unsupported_numerical_specificity",
                                             # One of three:
                                             #   unsupported_numerical_specificity
                                             #   unsupported_factual_claim
                                             #   missing_safety_boundary

    # ── Input ──
    "input_answer": "Research shows that 38.7% of people benefit...",
    "question": "Does massage help muscle recovery?",
    "target_span": "38.7%",                  # Optional. The specific text span
                                             # that exhibits the failure.

    # ── Condition Assignments ──
    "original_answer": "Research shows that 38.7% of people benefit...",
    "generic_correction": "...",             # Generic correction baseline
    "cmc_correction": "...",                 # CheckMyCoach full pipeline output

    # ── Corrected Answers (populated by each condition) ──
    "retrieved_evidence": [
        {
            "id": "recommendation.acsm_flexibility_recommendations",
            "type": "recommendation",
            "canonical_name": "ACSM Flexibility Recommendations for Healthy Adults",
            "content": "Table 5.6 provides the ACSM flexibility recommendations...",
            "source": "ACSM12 (ACSM Flexibility Recommendations for Healthy Adults)"
        }
    ],

    # ── Validation (per condition) ──
    "original_validation": {
        "target_failure_removed": False,     # N/A for original
        "supported_information_retained": True,
        "new_unsupported_claims": [],
        "boundary_preserved": True
    },
    "generic_validation": {
        "target_failure_removed": True,
        "supported_information_retained": True,
        "new_unsupported_claims": ["generalizes training volume claim without evidence"],
        "boundary_preserved": False,
        "change_summary": "Removed 38.7% but inserted vague claim about training volume"
    },
    "cmc_validation": {
        "target_failure_removed": True,
        "supported_information_retained": True,
        "new_unsupported_claims": [],
        "boundary_preserved": True,
        "change_summary": "Replaced 38.7% with 'some research suggests benefits may vary'"
    },

    # ── Traces (one per condition, only CMC shown) ──
    "cmc_trace": {
        "detection": {
            "ucs_score": 1,
            "needs_calibration": True,
            "decision": "calibrate",
            "reason": "UCS=1: Pseudo-precise — uses seemingly precise number without source"
        },
        "diagnosis": {
            "failure_type": "cue_leakage",
            "confidence": 0.85,
            "evidence_used": [
                "UCS=1: Pseudo-precise — number or parameter appears precise but has no source"
            ],
            "raw_features": {
                "ucs_score": 1,
                "has_directional_claim": True,
                "has_hedging": True,
                "cites_evidence_type": False
            }
        },
        "retrieval": {
            "query": "massage muscle recovery",
            "results_count": 3,
            "source_ids": [
                "recommendation.acsm_flexibility_recommendations",
                "threshold.absolute_indications_for_terminating_exercise_testing"
            ]
        },
        "correction": {
            "strategy": "cue_leakage",
            "source": "llm",                 # "llm" | "fallback"
            "model": "openai/gpt-4o-mini",
            "prompt_tokens": 320,
            "latency_ms": 1450
        },
        "validation": {
            "passed": True,
            "fallback_triggered": False,
            "checks": {
                "length": {"passed": True, "ratio": 1.2},
                "assertion": {"passed": True, "original_count": 3, "corrected_count": 1},
                "non_empty": {"passed": True},
                "non_copy": {"passed": True, "overlap_ratio": 0.45}
            }
        }
    }
}
```

## Failure Family → M2 Failure Type Mapping

| Evaluation v1 Family | M2 `failure_type` | UCS Score | Primary Features |
|---------------------|-------------------|-----------|------------------|
| `unsupported_numerical_specificity` | `cue_leakage` | 1 | `has_directional_claim=True` |
| `unsupported_factual_claim` | `template_dominance` | 0 | `claims_superiority=True`, `cites_evidence_type=False` |
| `missing_safety_boundary` | `context_mismatch` | 2-3 (Hedged/Calibrated w/ manual_review) | `needs_manual_review=True` or contradiction |

## Case ID Convention

```
NUM-001  through  NUM-015   → unsupported_numerical_specificity  (15 cases)
FCT-001  through  FCT-015   → unsupported_factual_claim          (15 cases)
SAF-001  through  SAF-010   → missing_safety_boundary            (10 cases)
```

## Output Files

Per case (individual):

```
evaluation/v1/cases/NUM-001.json
evaluation/v1/cases/NUM-002.json
...
```

Aggregate:

```
evaluation/v1/results.json       # All 40 cases with all conditions
evaluation/v1/summary.json       # Aggregate statistics per family
evaluation/v1/annotation/        # Human annotation worksheets
```

## Three Conditions

| Condition | Implementation | Source |
|-----------|---------------|--------|
| **Original answer** | Raw LLM output (DeepSeek Chat, direct API, no evidence) | `benchmark.py` `_raw_llm()` already implemented |
| **Generic correction baseline** | Rule-based: prepend "The above values are for reference only; actual results vary." for NUM, "[Disclaimer]" prefix for all | New — minimal python function |
| **CheckMyCoach full pipeline** | `calibrate(response=raw_answer, question=question)` | Already implemented in `pipeline/agent_pipeline.py` |

## What This Interface Reuses from the Existing Schema

| Eval v1 Field | Existing Schema Field | Change Required |
|---------------|-----------------------|-----------------|
| `case_id` | None — `audit_id` exists but different format | **Add** `case_id` field |
| `failure_family` | None — M2's `failure_type` doesn't map 1:1 | **Add** family mapping layer |
| `input_answer` | `response` | Reuse |
| `retrieved_evidence` | `evidence` | Reuse |
| `cmc_correction` | `corrected_response` | Reuse |
| `cmc_trace.detection` | Partial — M1 returns (bool, str) | **Promote** to structured dict |
| `cmc_trace.retrieval` | Not logged | **Add** trace fields to retriever |
| `cmc_trace.diagnosis` | `raw_features` + `evidence` | Reuse directly |
| `cmc_trace.validation` | `checks` dict in ValidationResult | Reuse directly |
| Validation fields | Not checked by M4 | **Add** 4 new validation checks |
