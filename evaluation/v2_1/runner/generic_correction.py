"""
Generic Correction — Evidence-based revision baseline.

v2.1 changes:
- Temperature lowered to 0.3 (protocol §3.3)
- Supports custom_user_prompt for Generic+Diagnosis condition (protocol §4.3)
- max_tokens raised to 1024 (protocol §3.3)

Protocol reference: §4.2 (Generic), §4.3 (Generic+Diagnosis)
"""

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")


@dataclass
class GenericCorrectionResult:
    corrected_text: str
    prompt_used: str
    source: str  # "llm" — fallback is no longer allowed in evaluation
    model: str = ""
    temperature: float = 0.0
    token_usage: dict = field(default_factory=dict)
    error: str | None = None


def _compute_prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _load_prompt(protocol_dir: Path = None) -> str:
    """Load the frozen GENERIC_BASELINE_PROMPT.txt from the protocol directory."""
    if protocol_dir is None:
        protocol_dir = Path(__file__).resolve().parent.parent / "protocol"
    prompt_path = protocol_dir / "GENERIC_BASELINE_PROMPT.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Frozen generic prompt not found at {prompt_path}. "
            "This file is part of the frozen protocol."
        )
    return prompt_path.read_text(encoding="utf-8").strip()


def _build_user_prompt(
    question: str,
    original_answer: str,
    evidence_payload: list,
) -> str:
    """Build the standard Generic user prompt (protocol §4.2)."""
    evidence_text = ""
    if evidence_payload:
        lines = []
        for e in evidence_payload:
            src = e.get("source", "source")
            content = e.get("content", "")
            lines.append(f"[{src}] {content[:300]}")
        if lines:
            evidence_text = "\n".join(lines[:5])

    parts = []
    if question:
        parts.append(f"Question: {question}")
    if evidence_text:
        parts.append(f"Relevant evidence:\n{evidence_text}")
    parts.append(f"Original answer:\n{original_answer}")
    parts.append("Revised answer:")
    return "\n\n".join(parts)


def correct(
    question: str,
    original_answer: str,
    evidence_payload: list,
    protocol_dir: Path = None,
    custom_user_prompt: str | None = None,
) -> GenericCorrectionResult:
    """Apply evidence-based revision using the frozen generic prompt.

    Generic condition (§4.2): uses standard _build_user_prompt.
    Generic+Diagnosis condition (§4.3): passes a pre-built user_prompt with
    the diagnosis block inserted.

    Fail closed: if the LLM call fails, the exception propagates and the
    runner records included=False.

    Args:
        question: The original user question.
        original_answer: The pre-provided original answer to revise.
        evidence_payload: Retrieved evidence items (list of dicts).
        protocol_dir: Override for protocol directory (testing).
        custom_user_prompt: Optional pre-built user prompt (for Generic+Diagnosis).

    Returns:
        GenericCorrectionResult with revised text, prompt used, and source.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
        ConnectionError: If the API call fails.
    """
    system_prompt = _load_prompt(protocol_dir)
    if custom_user_prompt:
        user_prompt = custom_user_prompt
    else:
        user_prompt = _build_user_prompt(question, original_answer, evidence_payload)
    full_prompt = system_prompt + "\n\n" + user_prompt

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not set. "
            "Generic correction requires a valid API key. "
            "Fail closed: no fallback output."
        )

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    model = "openai/gpt-4o-mini"  # Hardcoded for v2.2 — no env var override
    temperature = 0.3  # Protocol §3.3

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=1024,  # Protocol §3.3
    )

    if not resp.choices or not resp.choices[0].message.content:
        raise ValueError("LLM returned empty response for generic correction")

    corrected = resp.choices[0].message.content.strip()
    usage = resp.usage
    token_info = {}
    if usage:
        token_info = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

    return GenericCorrectionResult(
        corrected_text=corrected,
        prompt_used=full_prompt,
        source="llm",
        model=model,
        temperature=temperature,
        token_usage=token_info,
        error=None,
    )
