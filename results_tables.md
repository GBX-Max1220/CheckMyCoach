# Results Tables — CSCW/CHI Format (Updated with Real Data)

**Source**: UCS Engine (GPT-5.5 Instant judge) on 126 questions × 2 models

> ⚠️ Historical draft. All tables and findings come from one early LLM-judge run (GPT-5.5 Instant) that was never human validated; no accuracy measure exists and the run is not reproducible. Retained as audit history; not publication-ready results.

---

## Table 1: UCS Distribution Across Models

```
\begin{table}[ht]
\centering
\caption{UCS Distribution Across LLM Models (126 Questions, N=252 Evaluations)}
\label{tab:ucs_distribution}
\begin{tabular}{lcccc}
\toprule
UCS Category & DeepSeek & Qwen & Pooled & 95\% CI (Pooled) \\
\midrule
Overconfident (0)    & 0.0\%  & 0.0\%  & 0.0\%  & [0.0\%, 3.0\%] \\
Pseudo-precise (1)   & 5.6\%  & 7.1\%  & 6.3\%  & [4.0\%, 9.9\%] \\
Hedged (2)           & 1.6\%  & 0.0\%  & 0.8\%  & [0.2\%, 3.1\%] \\
Calibrated (3)       & 92.9\% & 92.9\% & 92.9\% & [89.1\%, 95.5\%] \\
\bottomrule
\end{tabular}
\end{table}
```

_Note: Wilson 95\% confidence intervals for pooled proportions.
Chi-square test comparing model distributions: $\chi^2(2) = 2.25$, $p = 0.32$,
Cram\'{e}r's $V = 0.09$ (negligible effect size). UCS scores are treated as
interval-level for analysis, consistent with common practice for Likert-type
scales in HCI research [cite]. Median scores and IQR are reported in supplementary
materials as a robustness check._

---

## Table 2: Mean UCS Score by Uncertainty Type (Calibration Gradient)

```
\begin{table}[ht]
\centering
\caption{Mean UCS Score by Question Uncertainty Type}
\label{tab:calibration_gradient}
\begin{tabular}{lccc}
\toprule
Uncertainty Type & N & DeepSeek & Qwen \\
\midrule
CONSENSUS              & 38  & 2.96 & 3.00 \\
NO\_DIFFERENCE          & 20  & 2.60 & 2.60 \\
MIXED\_EVIDENCE         & 38  & 2.76 & 2.52 \\
INSUFFICIENT\_EVIDENCE  & 15  & 2.50 & 2.00 \\
EVOLVING               & 15  & 2.90 & 3.00 \\
\midrule
Gap (Consensus - Insufficient) & — & 0.46 & 1.00 \\
\bottomrule
\end{tabular}
\end{table}
```

_Note: UCS scores range from 0 (Overconfident) to 3 (Calibrated). Maximum possible
gap is 3.0 points. Per-cell N shows the number of questions per uncertainty type
(pooled across models)._

---

## Results Section — Historical Draft (superseded)

The archived GPT-5.5 Instant judge labels are summarized below as historical label counts. They do not establish model behavior.

**Finding 1 (historical label distribution): Pseudo-precise was the largest non-Calibrated label class.**
Across the archived 252 evaluations, 92.9% were labeled Calibrated and 6.3% (pooled)
Pseudo-precise by the GPT-5.5 Instant judge; no Overconfident labels were produced.
Because the judge was never human-validated and no accuracy measure exists, this is a
label distribution, not an established finding about model behavior.

Historical note: 1 − (0.937)^10 ≈ 48% is the arithmetic consequence of the 6.3%
label share; it is not a validated exposure or safety estimate (no user study exists).

**Finding 2 (historical): the archived labels show a calibration gradient.**
In the archived labels, both models received higher scores on CONSENSUS than on
INSUFFICIENT_EVIDENCE questions (Table 2).
Responses to CONSENSUS questions received the highest scores (DeepSeek: 2.96, Qwen: 3.00),
while INSUFFICIENT EVIDENCE questions received the lowest (DeepSeek: 2.50, Qwen: 2.00).
However, the gradient magnitude differed substantially: Qwen showed a gap of 1.00 UCS points
(33% of the maximum 3.0-point scale) compared to DeepSeek's 0.46 UCS points (15%).
This asymmetry suggests that while both models demonstrate evidence-aware calibration,
the sensitivity to evidence strength varies by model — a dimension not captured by
accuracy-only evaluations.

**Finding 3 (historical): the two models received similar label distributions.**
The Qwen baseline summary reported higher self-reported confidence (93.72 vs 91.16), yet the
Pseudo-precise label shares were similar (7.1% vs 5.6%). A chi-square test on the archived
labels found no significant difference between the models ($\chi^2 = 2.25$, $p = 0.32$).
This is a historical label comparison; it does not establish a decoupling of accuracy from
calibration, because no accuracy measure was validated.

## Paper Narrative Positioning (historical; construct retired)

**Historical core narrative**: Not "models are dangerously overconfident" (the archived labels
do not support this), but "models create a precision illusion — their primary calibration
failure is generating seemingly precise but unsupported numerical claims, which is harder
for users to detect than overt overconfidence."

**Why this is a stronger HCI story**: It connects to the precision heuristic in judgment
and decision-making — people trust more precise-sounding information even when they know
the precision is unwarranted. This makes the problem inherently about human perception,
not just model behavior.

## Limitations to Address in Paper

1. **LLM judge bias without human validation**.
   The entire UCS classification pipeline depends on a single LLM judge (GPT-5.5 Instant).
   This creates a circularity risk: the judge may preferentially classify outputs matching
   its own stylistic patterns as Calibrated. The 0% Overconfident rate in particular should
   be interpreted cautiously—it may reflect the judge's calibration pattern more than the
   evaluated models' actual output behavior. Human validation (target κ ≥ 0.7) is required
   to confirm these results.

2. **Ordinal scale**. UCS scores are ordinal (0-3). Mean reporting follows standard practice
   for Likert-type scales in HCI but should be interpreted with the scale's bounded nature
   in mind. Median + IQR reported in supplementary materials.

3. **Small per-cell N for subgroup analyses**. Per-uncertainty-type N ranges from 15-38.
   Subgroup comparisons (e.g., gradient by model) are descriptive, not inferential.

4. **Limited generalizability**. Single domain (fitness), single judge (GPT-5.5 Instant),
   two models from similar capability tiers. Generalization to medical/legal domains,
   other judge models, or frontier models is untested.

5. **UCS taxonomy construct validity not formally tested**. The 4-level taxonomy was derived
   inductively from 252 LLM responses. Exhaustiveness and boundary clarity require further
   validation through inter-rater reliability and factor analysis.
