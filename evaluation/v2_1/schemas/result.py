"""
Result record TypedDict for v2.1 evaluation.

Matches the structure built by build_record() in run_single_case.py.
"""

from typing import TypedDict, NotRequired


class CorrectionTrace(TypedDict, total=False):
    prompt_source: str
    model: str
    temperature: float
    llm_source: str
    """oracle_diagnosis for generic_with_diagnosis condition"""
    oracle_diagnosis: dict | None


class ValidationTrace(TypedDict, total=False):
    m4_passed: bool | None


class TokenUsage(TypedDict, total=False):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ResultRecord(TypedDict):
    """Complete provenance record for one case × one condition × one attempt."""
    run_id: str
    case_id: str
    condition: str  # original | generic | generic_with_diagnosis | checkmycoach
    model_id: str
    provider: str
    temperature: float | None
    max_tokens: int | None
    seed_policy: str
    request_id: str
    response_id: str
    fallback_status: str
    prompt_hash: str
    evidence_hash: str
    retry_count: int
    timestamp: str
    included: bool
    error: str | None
    raw_response: str
    corrected_response: str | None
    latency_ms: float

    # Condition-specific
    correction_trace: NotRequired[CorrectionTrace]
    validation_trace: NotRequired[ValidationTrace]
    evidence_ids: NotRequired[list[str]]
    token_usage: NotRequired[TokenUsage]
    m4_passed: NotRequired[bool | None]
    needs_calibration: NotRequired[bool | None]
    failure_type: NotRequired[str | None]
