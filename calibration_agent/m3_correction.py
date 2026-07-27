"""
M3 Correction Layer - Correct original advice text based on M2 diagnosis results.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


# ==================== 数据类 ====================

@dataclass
class CorrectionResult:
    corrected_text: str
    strategy_used: str
    prompt_used: str
    source: str  # "llm" / "fallback"


class CorrectionError(Exception):
    pass


# ==================== Prompt 模板（硬编码）====================

PROMPT_TEMPLATES = {}

PROMPT_TEMPLATES["template_dominance"] = {}
PROMPT_TEMPLATES["template_dominance"]["system"] = (
    "You are a professional academic writing assistant. Rewrite overly determined claims into scientifically cautious expressions."
)
PROMPT_TEMPLATES["template_dominance"]["user"] = (
    "Below is an AI-generated fitness advice. This advice uses overly determined language, sounding authoritative but lacking evidence.\n\n"
    "Please rewrite this advice with the following requirements:\n"
    "1. Acknowledge individual differences and scientific uncertainty in this area\n"
    "2. Specify conditions or limitations of the conclusion\n"
    "3. Keep the core advice but reduce assertion strength\n"
    "4. If applicable, note the evidence status\n"
    "5. Do not fabricate data or citations\n"
    "6. Output ONLY the rewritten text. No explanation, preamble, or commentary.\n"
    "7. Keep output length similar to the original (+/- 50% max)\n\n"
    "Original advice:\n{original_text}\n\n"
    "Rewritten advice:"
)

PROMPT_TEMPLATES["cue_leakage"] = {}
PROMPT_TEMPLATES["cue_leakage"]["system"] = (
    "You are a professional academic writing assistant. Rewrite advice containing unsourced precise numbers into scientifically sound expressions."
)
PROMPT_TEMPLATES["cue_leakage"]["user"] = (
    "Below is an AI-generated fitness advice. This advice contains seemingly precise numbers without clear sources (e.g., percentages to decimal places, specific durations, counts), which may mislead users.\n\n"
    "Please rewrite this advice with the following requirements:\n"
    "1. Replace specific numbers with reasonable ranges\n"
    "2. Note that values vary by individual\n"
    "3. If the value comes from general reference rather than personalized assessment, state this\n"
    "4. Keep the core message but remove false precision\n"
    "5. Do not fabricate data or citations\n"
    "6. Output ONLY the rewritten text. No explanation, preamble, or commentary.\n"
    "7. Keep output length similar to the original (+/- 50% max)\n\n"
    "Original advice:\n{original_text}\n\n"
    "Rewritten advice:"
)

PROMPT_TEMPLATES["context_mismatch"] = {}
PROMPT_TEMPLATES["context_mismatch"]["system"] = (
    "You are a professional academic writing assistant. Rewrite generic advice into responsible expressions that account for individual differences."
)
PROMPT_TEMPLATES["context_mismatch"]["user"] = (
    "Below is an AI-generated fitness advice. This advice may be correct in some contexts but does not account for individual differences and specific situations.\n\n"
    "Please rewrite this advice with the following requirements:\n"
    "1. Specify the target population or prerequisites for this advice\n"
    "2. Note that different individuals may need different approaches\n"
    "3. Recommend consulting a professional when necessary\n"
    "4. Keep the core advice but add necessary qualifiers\n"
    "5. Do not fabricate data or citations\n"
    "6. Output ONLY the rewritten text. No explanation, preamble, or commentary.\n"
    "7. Keep output length similar to the original (+/- 50% max)\n\n"
    "Original advice:\n{original_text}\n\n"
    "Rewritten advice:"
)


# ==================== Fallback ====================

FALLBACK_PREFIXES = {
    "template_dominance": "[Correction: reduce assertion] Note that ",
    "cue_leakage": "[Correction: remove false precision] The above values are for reference only; actual results vary. ",
    "context_mismatch": "[Correction: add context] This advice applies to general situations, but individual differences are significant. ",
}


# ==================== 核心函数 ====================

def _build_prompt(failure_type: str, original_text: str,
                  question: str | None = None,
                  evidence: str | None = None) -> str:
    tmpl = PROMPT_TEMPLATES.get(failure_type)
    if not tmpl:
        raise ValueError(f"Unknown failure type: {failure_type}")
    base_prompt = tmpl["user"].format(original_text=original_text)
    # Prepend question and evidence context to the existing prompt
    context_parts = []
    if question:
        context_parts.append(f"Question: {question}")
    if evidence:
        context_parts.append(f"Evidence:\n{evidence}")
    if context_parts:
        return "\n\n".join(context_parts) + "\n\n" + base_prompt
    return base_prompt


def _call_llm(prompt: str, system_prompt: str) -> Optional[str]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        resp = client.chat.completions.create(
            model="openai/gpt-4o-mini",  # Hardcoded for v2.2 — no env var override
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # Protocol v2.2 §3.3 — equalized across all correction conditions
            max_tokens=1024,  # Protocol v2.2 §3.3 — equalized across all correction conditions
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise CorrectionError(f"LLM call failed: {e}")


def correct(failure_type: str, original_text: str,
            question: str | None = None,
            evidence: str | None = None) -> CorrectionResult:
    """Apply type-aware LLM correction.

    v2.2: Accepts question and evidence for evidence-aware correction.
    The prompt includes question, evidence, failure type, and original text.

    Args:
        failure_type: M2 diagnosis (e.g. "cue_leakage").
        original_text: The original answer to correct.
        question: The original user question (evidence awareness).
        evidence: Evidence excerpt text (evidence awareness).
    """
    if failure_type not in PROMPT_TEMPLATES:
        raise ValueError(f"Unknown failure type: {failure_type}")

    prompt = _build_prompt(failure_type, original_text, question, evidence)
    sys_prompt = PROMPT_TEMPLATES[failure_type]["system"]

    try:
        llm_result = _call_llm(prompt, sys_prompt)
    except CorrectionError:
        llm_result = None

    if llm_result:
        return CorrectionResult(
            corrected_text=llm_result,
            strategy_used=failure_type,
            prompt_used=prompt,
            source="llm",
        )

    prefix = FALLBACK_PREFIXES.get(failure_type, "[Correction] ")
    return CorrectionResult(
        corrected_text=prefix + original_text,
        strategy_used=failure_type,
        prompt_used=prompt,
        source="fallback",
    )
