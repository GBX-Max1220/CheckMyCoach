# Baseline Fairness Audit — CheckMyCoach Evaluation v1

**Auditor:** Hermes Agent 4 (independent red-team)
**Date:** 2026-07-27

---

## Summary: GENERIC CONDITION IS ARTIFICIALLY WEAK

The generic correction baseline as implemented does **not** match what the
protocol specifies. This is the single most consequential finding of this audit.

---

## Defect D1: Generic correction uses a different prompt than the protocol

### Protocol specifies (`GENERIC_BASELINE_PROMPT.txt`):

```
Revise the answer to be accurate, appropriately cautious, evidence-based
and concise. Preserve useful supported information and avoid adding
unsupported claims.
```

### Implementation uses (`generic_correction.py`):

```
System:     "You are a professional writing assistant. Improve the following
             text to be more clear, accurate, and useful. Do not fabricate
             data or citations."
User:       "Please improve the following text:\n\n{original_text}\n\nImproved text:"
```

### Impact:

The protocol prompt explicitly asks to:
- Be evidence-based
- Preserve useful supported information
- Avoid adding unsupported claims

The implementation prompt:
- Asks to be "more clear, accurate, and useful" — broader and weaker
- Does **not** mention preserving supported content
- Does **not** mention avoiding new unsupported claims
- Does **not** reference evidence

The protocol prompt would produce better corrections; the implementation
prompt systematically disadvantages the generic baseline.

---

## Defect D2: Generic correction receives no question or evidence

### Protocol specifies:

> "Generic correction: provide only the question, original answer, eligible
> evidence payload, and the exact frozen prompt in GENERIC_BASELINE_PROMPT.txt."

### Implementation (`generic_correction.py:correct(original_text)`):

- **Receives only:** the original text
- **Does not receive:** the question, the evidence payload, the frozen prompt

### Impact:

Without the question, the generic correction cannot know what was being asked.
Without the evidence payload, it cannot distinguish supported claims from
unsupported ones. The CheckMyCoach condition receives both the detection
output and the evidence context. The generic condition is asked to improve
text in a vacuum.

This violates the experimental design: the comparison is supposed to isolate
*type-aware correction* from *generic improvement*, not from *blinded
regeneration*.

---

## Defect D3: Generic correction is LLM-based, not rule-based

### Protocol intent (and MINIMUM_PATCH_PLAN.md):

The MINIMUM_PATCH_PLAN proposed a **deterministic rule-based** baseline:
- Remove numerical patterns, prepend disclaimers according to failure family

### Implementation:

Calls `OpenRouter GPT-4o-mini` with a generic prompt.

### Impact:

The generic condition is itself an LLM-based system with its own failure modes
and capabilities. Any observed difference between generic and CheckMyCoach
conditions conflates:
1. **Prompt specialization** (generic vs type-aware)
2. **Model used** (GPT-4o-mini vs whatever the CMC pipeline uses for M3)
3. **Context provided** (text only vs evidence+dignosis)

A rule-based baseline would provide a clean lower bound: "Can a deterministic,
zero-cost rule remove the identified failure?" An LLM-based baseline answers
"Can *any* LLM fix this?" — a fundamentally different question.

---

## Defect D4: All three conditions share the same pipeline

### Implementation:

All three conditions call `calibrate_full()` which runs: retrieve evidence →
LLM generate → UCS score. The only difference is the correction step.

### Problem:

If retrieval fails (returns 0 results) and the LLM generates an unsupported
answer, **both** the original and generic conditions have this failure built in.
When CheckMyCoach fixes it, the improvement conflates:
- **Pipeline contribution:** Evidence retrieval + LLM generation quality
- **Retrieval contribution:** Whether evidence was available at all
- **Correction contribution:** M3 detection + diagnosis + correction
- **Prompt specialization:** Type-aware vs generic prompt

### Recommendation:

Add a "raw LLM" condition: call the LLM directly without any pipeline
evidence retrieval or UCS scoring. This isolates the evidence-retrieval
contribution from the correction quality.

---

## Defect D5: The generic baseline prompt does not match the protocol's generic correction intent

The protocol says that the generic condition should isolate the effect of
**"any improvement attempt"** from the effect of **"failure-type-aware
correction."** The generic correction prompt should be broad enough to
potentially fix the failure, but not so weak that it's guaranteed to fail.

The current implementation's prompt produces corrections that are plausible
improvements but that the CheckMyCoach condition's prompt would also produce.
The protocol's frozen prompt is more specific and would produce better
baseline results. Using the weaker prompt systematically inflates the
apparent advantage of CheckMyCoach.

---

## Distinguishing Contributions

| Contribution | Original | Generic (current) | Generic (per protocol) | CheckMyCoach |
|---|---|---|---|---|
| Evidence retrieval | YES | YES | YES | YES |
| LLM generation | YES | YES | YES | YES |
| Generic LLM correction | — | YES (text only, weak prompt) | YES (text+evidence+question, strong prompt) | — |
| Detection (M1) | — | — | — | YES |
| Diagnosis (M2) | — | — | — | YES |
| Type-aware correction (M3) | — | — | — | YES |
| Validation (M4) | — | — | — | YES |

The current generic condition is not a meaningful baseline for isolating
any single contribution.

---

## Verdict

**BLOCKING.** The generic baseline must be fixed to match the protocol before
any meaningful comparison can be drawn. Without this fix, all three conditions
are on different evidential and contextual footing, and no claim about
"CheckMyCoach outperforms a generic baseline" is defensible.
