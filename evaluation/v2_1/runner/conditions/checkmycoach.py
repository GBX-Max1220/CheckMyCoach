"""
checkmycoach.py — CheckMyCoach condition.

Full CMC pipeline: UCS → M1 → M2 → M3 → M4.
Receives the SAME evidence_excerpt as Generic and Generic+Diagnosis,
passed explicitly to calibrate() to skip KC runtime retrieval.

Protocol reference: §4.4, §5
"""

from pipeline.agent_pipeline import calibrate


def run_checkmycoach(
    original_answer: str,
    question: str,
    evidence_payload: list | None = None,
) -> dict:
    """CheckMyCoach condition: full pipeline with external evidence.

    Evidence from blinded case is passed pre-retrieved, so the pipeline
    skips KC runtime retrieval. Pipeline internally runs UCS→M1→M2→M3→M4.

    Protocol reference: §4.4 — calibrate(response, question, evidence=...)

    API failure handling (v2.2):
    - If M3 correction source is not "llm" (i.e., fallback was used),
      the evaluation treats this as a failure — not a successful correction.
      corrected_response is set to None and included=False.
      This ensures API failures do not enter scientific analysis.

    Args:
        original_answer: Pre-provided original answer.
        question: The original user question.
        evidence_payload: Evidence items (from evidence_router, same as Generic conditions).

    Returns:
        Dict with pipeline output, trace, and provenance fields.
        On pipeline failure or M3 fallback: included=False with error="M3_API_FALLBACK".
    """
    try:
        result = calibrate(
            response=original_answer,
            question=question,
            evidence=evidence_payload,
        )

        # v2.2: Detect M3 fallback — mark as excluded, not as successful correction
        m3_source = result.get("m3_source", "unknown")
        if m3_source != "llm":
            return {
                "condition": "checkmycoach",
                "raw_response": original_answer,
                "corrected_response": None,
                "m4_passed": result.get("m4_passed"),
                "needs_calibration": result.get("needs_calibration"),
                "failure_type": result.get("failure_type"),
                "m2_confidence": result.get("m2_confidence"),
                "correction_source": m3_source,
                "correction_trace": {
                    "failure_type": result.get("failure_type"),
                    "m2_confidence": result.get("m2_confidence"),
                    "corrected_response": None,
                },
                "validation_trace": {
                    "m4_passed": result.get("m4_passed"),
                },
                "evidence_ids": [e.get("id", "") for e in (result.get("evidence") or [])],
                "token_usage": result.get("token_usage", {}),
                "latency_ms": (result.get("latency_ms") or {}).get("total", 0),
                "included": False,
                "error": "M3_API_FALLBACK",
            }

        return {
            "condition": "checkmycoach",
            "raw_response": original_answer,
            "corrected_response": result.get("corrected_response"),
            "correction_source": m3_source,
            "m4_passed": result.get("m4_passed"),
            "needs_calibration": result.get("needs_calibration"),
            "failure_type": result.get("failure_type"),
            "m2_confidence": result.get("m2_confidence"),
            "correction_trace": {
                "failure_type": result.get("failure_type"),
                "m2_confidence": result.get("m2_confidence"),
                "corrected_response": result.get("corrected_response"),
            },
            "validation_trace": {
                "m4_passed": result.get("m4_passed"),
            },
            "evidence_ids": [e.get("id", "") for e in (result.get("evidence") or [])],
            "token_usage": result.get("token_usage", {}),
            "latency_ms": (result.get("latency_ms") or {}).get("total", 0),
            "included": True,
            "error": result.get("error"),
        }
    except Exception as exc:
        return {
            "condition": "checkmycoach",
            "raw_response": original_answer,
            "corrected_response": None,
            "correction_source": "pipeline_exception",
            "evidence_ids": [],
            "token_usage": {},
            "latency_ms": 0,
            "included": False,
            "error": f"CMC_PIPELINE_ERROR: {exc}",
        }
