"""
generic_plus.py — Generic+Diagnosis condition (ORACLE diagnosis).

Receives the same evidence_excerpt as Generic, PLUS oracle diagnosis fields
from the gold case: failure_family, target_failure_span, failure_statement,
content_required_to_change, and required_boundary (Group-C only).

This establishes the UPPER BOUND for diagnosis-informed generic correction.
If Generic+Diagnosis ≈ Generic, then even perfect diagnosis does not help
a generic correction prompt — the bottleneck is the correction mechanism.

Protocol reference: §4.3
RQ1: Does providing explicit failure-type diagnosis improve correction quality?
"""

from evaluation.v2_1.runner.generic_correction import correct as generic_correct


def _build_user_prompt_with_diagnosis(
    question: str,
    original_answer: str,
    evidence_excerpt: str,
    failure_family: str,
    target_failure_span: str,
    failure_statement: str,
    content_required_to_change: list[str],
    required_boundary: str | None = None,
) -> str:
    """Build the user prompt with evidence AND oracle diagnosis.

    Protocol reference: §4.3 — User prompt construction.

    The diagnosis block is inserted between the evidence section and
    the "Revised answer:" prompt. The system prompt is the SAME as
    Generic (GENERIC_BASELINE_PROMPT.txt).
    """
    parts = [f"Question: {question}"]

    if evidence_excerpt:
        parts.append(f"Relevant evidence:\n{evidence_excerpt}")

    parts.append(f"Original answer:\n{original_answer}")

    # Diagnosis block (protocol §4.3)
    diag_lines = ["Failure diagnosis:"]
    diag_lines.append(f"- Type: {failure_family}")
    diag_lines.append(f'- Problematic content: "{target_failure_span}"')
    diag_lines.append(f"- Issue: {failure_statement}")
    diag_lines.append(f"- Required changes: {'; '.join(content_required_to_change)}")
    if required_boundary:
        diag_lines.append(f"- Required boundary: {required_boundary}")
    parts.append("\n".join(diag_lines))

    parts.append("Revised answer:")
    return "\n\n".join(parts)


def run_generic_plus(
    original_answer: str,
    question: str,
    evidence_payload: list | None = None,
    # Oracle diagnosis fields from blinded case
    failure_family: str | None = None,
    target_failure_span: str | None = None,
    failure_statement: str | None = None,
    content_required_to_change: list[str] | None = None,
    required_boundary: str | None = None,
) -> dict:
    """Generic+Diagnosis: generic correction with oracle diagnosis.

    Receives evidence AND oracle diagnosis fields.
    These are gold labels — NEVER exposed to Generic or CMC conditions.

    If diagnosis fields are missing, falls back to plain generic correction
    (degraded mode — this should not occur in a properly constructed run).

    Protocol reference: §4.3, §4.1
    """
    evidence_excerpt = ""
    if evidence_payload:
        excerpts = [e.get("content", "") for e in evidence_payload if e.get("content")]
        evidence_excerpt = excerpts[0] if excerpts else ""

    # Build user prompt with diagnosis (if available)
    if all([failure_family, target_failure_span, failure_statement, content_required_to_change]):
        user_prompt = _build_user_prompt_with_diagnosis(
            question=question,
            original_answer=original_answer,
            evidence_excerpt=evidence_excerpt,
            failure_family=failure_family,
            target_failure_span=target_failure_span,
            failure_statement=failure_statement,
            content_required_to_change=content_required_to_change,
            required_boundary=required_boundary,
        )
    else:
        # Fallback: plain generic user prompt (should not happen in production)
        user_prompt = f"Question: {question}\n\nRelevant evidence:\n{evidence_excerpt}\n\nOriginal answer:\n{original_answer}\n\nRevised answer:"

    # Call generic_correct with the custom user prompt
    # We pass the diagnosis-enriched user prompt and let correct() handle the system prompt
    correction = generic_correct(
        question=question,
        original_answer=original_answer,
        evidence_payload=evidence_payload or [],
        custom_user_prompt=user_prompt,
    )

    return {
        "condition": "generic_with_diagnosis",
        "raw_response": original_answer,
        "corrected_response": correction.corrected_text,
        "correction_trace": {
            "prompt_source": "frozen GENERIC_BASELINE_PROMPT.txt (system) + oracle diagnosis (user)",
            "model": correction.model,
            "temperature": correction.temperature,
            "llm_source": correction.source,
            "oracle_diagnosis": {
                "failure_family": failure_family,
                "target_failure_span": target_failure_span,
                "failure_statement": failure_statement,
                "content_required_to_change": content_required_to_change,
                "required_boundary": required_boundary,
            },
        },
        "evidence_ids": [e.get("id", "") for e in (evidence_payload or [])],
        "token_usage": correction.token_usage or {},
        "latency_ms": 0,
        "included": correction.source != "fallback" if hasattr(correction, "source") else True,
        "error": correction.error if hasattr(correction, "error") and correction.error else None,
    }
