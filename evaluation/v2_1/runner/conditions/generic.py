"""
generic.py — Generic correction condition.

Single-pass LLM revision with question context and evidence payload.
Receives NO failure diagnosis, NO gold labels.

Protocol reference: §4.2
"""

from evaluation.v2_1.runner.generic_correction import correct as generic_correct


def run_generic(
    original_answer: str,
    question: str,
    evidence_payload: list | None = None,
) -> dict:
    """Generic correction: evidence-based revision using frozen prompt.

    Does NOT receive failure_type, target_span, or any gold label.
    On API failure: included=False (fail closed).

    Protocol reference: §4.2 — Forbidden inputs list.

    Args:
        original_answer: Pre-provided original answer.
        question: The original user question.
        evidence_payload: Evidence items (from evidence_router).

    Returns:
        Dict with corrected_response, trace, and provenance fields.
    """
    correction = generic_correct(
        question=question,
        original_answer=original_answer,
        evidence_payload=evidence_payload or [],
    )

    return {
        "condition": "generic",
        "raw_response": original_answer,
        "corrected_response": correction.corrected_text,
        "correction_trace": {
            "prompt_source": "frozen GENERIC_BASELINE_PROMPT.txt",
            "model": correction.model,
            "temperature": correction.temperature,
            "llm_source": correction.source,
        },
        "evidence_ids": [e.get("id", "") for e in (evidence_payload or [])],
        "token_usage": correction.token_usage or {},
        "latency_ms": 0,
        "included": correction.source != "fallback" if hasattr(correction, "source") else True,
        "error": correction.error if hasattr(correction, "error") and correction.error else None,
    }
