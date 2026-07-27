"""
original.py — Original condition.

Returns the pre-provided original_answer directly. No API call.
"""


def run_original(original_answer: str) -> dict:
    """Original condition: return the pre-provided answer directly.

    Protocol reference: §4.1

    Args:
        original_answer: Pre-provided answer from the blinded case.

    Returns:
        Dict with condition, raw_response, corrected_response=None, included=True, error=None.
    """
    return {
        "condition": "original",
        "raw_response": original_answer,
        "corrected_response": None,
        "included": True,
        "error": None,
    }
