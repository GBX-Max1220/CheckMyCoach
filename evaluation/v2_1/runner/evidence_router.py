"""
evidence_router.py — Uniform evidence distribution for Evaluation v2.1.

All three correction conditions receive the identical evidence_excerpt
from the same blinded case. This removes v1's evidence asymmetry.

Protocol reference: §5.1 Evidence Equalization
"""

import hashlib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvidencePayload:
    """Structured evidence payload, identical for Generic, Generic+, and CMC."""
    evidence_excerpt: str
    evidence_hash: str  # SHA-256 prefix (16 hex chars)
    structured: list[dict] = field(default_factory=list)
    """Formatted for pipeline consumption — passed to calibrate(evidence=...) or inserted into user prompt."""


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def route_evidence(case: dict) -> EvidencePayload:
    """Extract evidence_excerpt from a blinded case and build the uniform payload.

    Args:
        case: Blinded case dict (must have 'evidence_excerpt' key).

    Returns:
        EvidencePayload with excerpt text, hash, and structured list.

    Raises:
        ValueError: If evidence_excerpt is missing or empty.
    """
    excerpt = case.get("evidence_excerpt") or ""
    if not excerpt:
        raise ValueError(
            f"Case {case.get('case_id', '?')} has empty evidence_excerpt. "
            "All v2.1 correction conditions require frozen evidence."
        )

    structured = [{
        "id": "case_evidence",
        "type": "inline",
        "content": excerpt[:500],
        "source": "blinded case file",
    }]

    return EvidencePayload(
        evidence_excerpt=excerpt,
        evidence_hash=_hash_text(excerpt),
        structured=structured,
    )
