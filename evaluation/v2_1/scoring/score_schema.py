"""
score_schema.py — TypedDict for v2.2 external evaluation scorer.

The scorer is INDEPENDENT of the pipeline:
- No M1/M2/M3/M4 imports
- No pipeline imports
- No LLM calls
- Deterministic (same inputs → same outputs)

Only inputs: final response text + case_id + frozen primary_checks from gold data.
"""

from typing import TypedDict, NotRequired


class CheckResult(TypedDict):
    """Result of one primary check."""
    check_id: str
    check_type: str
    passed: bool
    detail: NotRequired[str]
    """Human-readable reason for failure."""


class ScoreRecord(TypedDict):
    """Score for one condition × case."""
    case_id: str
    condition: str  # original | generic | generic_with_diagnosis | checkmycoach
    response_text: str | None
    """The text that was scored (raw_response for original, corrected_response for others)."""
    checks: dict[str, bool]
    """Map of check_id → passed (True/False)."""
    check_details: list[CheckResult]
    """Per-check details with type and optional failure reason."""
    primary_score: bool
    """True iff ALL primary checks pass."""
    passed: bool
    """True iff primary_score is True AND response_text is not None."""


class ConditionSummary(TypedDict):
    """Aggregate scores for one condition across all cases."""
    condition: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    errors: int
    """Count of None/empty responses (pipeline failures)."""
    per_check_pass_rate: dict[str, float]
    """check_id → fraction of cases where this check passed."""


# ── Check type constants ──

CHECK_TYPES = {
    "substring_absent": "Target substring must NOT appear in response.",
    "regex_present": "Regex pattern must match response.",
    "any_phrase_present": "At least one of the given phrases must appear.",
    "all_phrase_present": "ALL of the given phrases must appear.",
    "phrase_present": "Single phrase must appear.",
    "any_regex_present": "At least one regex pattern must match.",
    "all_regex_present": "ALL regex patterns must match.",
    "all_phrase_groups_present": "Each group must have at least one matching phrase.",
}
