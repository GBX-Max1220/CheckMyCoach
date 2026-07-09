# CheckMyCoach — Full Project Context

> Author: Max Guo (gbx1220max@gmail.com, WeChat: Max-GuoBX)
> Identity: Independent researcher (undergrad), Human-AI Trust Calibration
> Capabilities: ML engineering (Python/PyTorch) + HCI experiment design (LMM) + psychometrics
> Toolchain: Reasonix (coding/analysis) + Claude Code (review) + Hermes (statistics) + DeepSeek V4 Flash (default, can escalate to Pro)

---

## Three-Project Arc

```
MaxFitCalib-Bench (discover) → CheckMyCoach (intervene) → CalTrust (adapt)
```

Each project is a phase in a single research program: measure LLM calibration failures, build a system to correct them, and develop an adaptive policy that selects the best intervention per user.

---

## Phase 1: MaxFitCalib-Bench — Completed ✅

### What
126 expert-crafted fitness questions across 8 categories (factual, scenario, adversarial, boundary, safety, psychology, recency, recovery). Grounded in ACSM/NSCA/AHA position stands. Each question tagged with uncertainty type: CONSENSUS, NO_DIFFERENCE, MIXED_EVIDENCE, INSUFFICIENT_EVIDENCE, EVOLVING.

### UCS Engine (4-stage pipeline)
1. **Stage 1:** Regex pattern matching (resolves ~17% with high confidence)
2. **Stage 2:** LLM structured extraction — reduces 4-class output to 5 binary features
3. **Stage 3:** Deterministic decision tree mapping (0/1/2/3)
4. **Stage 4:** LLM judge fallback for contradictory signals

### Core Data (GPT-5.5-instant judge, 252 evaluations)
- **Calibrated (UCS=3):** 92.9%
- **Pseudo-precise (UCS=1):** 6.3% ← dominant failure mode
- **Hedged (UCS=2):** 0.8%
- **Overconfident (UCS=0):** 0.0%
- **No significant difference between models** (χ² p=0.32, Cramér's V=0.09)
- **Calibration gradient:** CONSENSUS ~2.96 vs INSUFFICIENT ~2.00 (gap 0.46-1.00/3.0)
- **Evolving anomaly:** Evolving questions scored near-perfect (2.90-3.00), likely due to training data exposure to well-publicized guideline changes

### Narrative: The Precision Illusion
**Not** "models are dangerously overconfident" (0% Overconfident contradicts this).
**Instead** "models appear calibrated on the surface, but 6.3% of outputs are Pseudo-precise — they cite precise numbers without evidence. This is harder to detect than overt overconfidence. At 10 statements/session, users face ~48% cumulative exposure. Pseudo-precise outputs cluster in safety-critical scenarios: 23.7% on mixed-evidence questions, 26.7% on insufficient-evidence questions."

**arXiv submitted, waiting for ID.**

---

## Phase 2: CheckMyCoach — Complete ✅

### M1 Detection (10 tests)
- UCS=0 or 1 → calibrate; UCS=2 or 3 → pass
- needs_manual_review caps confidence at 0.6, does NOT override feature-based diagnosis
- **Design decision (corrected after Claude Code review):** needs_manual_review is a confidence modifier, not a separate diagnosis path

### M2 Diagnosis (14 tests)
Three failure types, priority-ordered:
1. **Contradictory features** → Context Mismatch
2. **Superiority without evidence** → Template Dominance
3. **Pseudo-precise with direction** → Cue Leakage

Also handles: negation context filtering ("不/没有/无法/不能"), semantic exclusion for "一定" (distinguishes "有一定" from "一定要").

### M3 Correction (9 tests)
Hard-coded prompts (not dynamically generated), one per failure type. Full prompt example documented in paper.tex.
- Uses GPT-4o-mini via OpenRouter (~$0.001/correction)
- Fallback mode adds prefix when API unavailable

### M4 Validation (8 tests)
Four sanity checks: length (50%-400%), assertion reduction (absolute terms must not increase, with negation filtering), non-empty, non-copy (overlap < 0.9).
Failed corrections → fall back to original output (never amplifies miscalibration).

### Baseline Comparison (24 cases, DeepSeek V4 Pro judge)
| Category | N | Original UCS | Corrected UCS | Δ |
|----------|---|-------------|---------------|----|
| Overconfident | 4 | 1.75 | 2.50 | +0.75 |
| Pseudo-precise | 6 | 2.50 | 2.67 | +0.17 |
| Hedged | 4 | 2.25 | 2.25 | ±0.00 |
| Calibrated | 5 | 3.00 | 3.00 | ±0.00 |
| All | 19 | 2.42 | 2.63 | +0.21 |

**Total: 44 tests (41 unit + 3 e2e), all passing.**

---

## Phase 3: CalTrust — Built, needs polish 🔧

### Architecture
- **LinUCB contextual bandit** (4 arms: none / calibrate_only / comparison / reflection)
- 9-dim context: UCS + failure_type one-hot(3) + prior_acceptance + confidence + trial_norm + condition + cal_exposure + XGBoost predictions
- **XGBoost Trust Predictor**: predicts acceptance (binary) and confidence (1-7). Trained on 19,200 simulation trials. AUC 0.70, RMSE 1.04.
- **Rule-based fallback**: when model not trained, uses heuristics (UCS=3 → 0.8 accept, UCS=0 → 0.7)
- **StimulusManager**: loads 48 items from CSV, handles randomization
- **CalibrationOrchestrator**: wraps CheckMyCoach M1-M4 into `run_pipeline()` returning `CalibrationResult`
- **Frontend**: Streamlit (4 screens, 337 lines) + Gradio (backup)
- **DB**: SQLite sessions with checkpoint/resume
- **SHAP explainability**: top-3 features per prediction

### Simulation (fixed)
- 4 user profiles × 100 sessions × 24 trials × 2 conditions = 19,200 trials
- Calibration-aware reward function (penalizes accepting UCS=0/1)
- Trial-level data saved to `simulation_trials.csv`
- XGBoost trained on full dataset

### Known Issue
**Naive profile still -0.4% below random.** This is a ceiling effect (naive users already accept ~89%, bandit exploration costs outweigh potential gain). The bandit correctly learns to choose "no intervention" arm (46.7%) for these users, which is the desired behavior — but the comparison metric (reward/session) penalizes exploration during learning. Documented in paper as future work.

---

## Paper Status

**File:** `CheckMyCoach/paper.tex` (8 of 9 sections complete)
**Target venue:** CSCW 2027 (backup: CHI LBW)
**Title direction:** "From Precision Illusion to Calibration Intervention: Evaluating and Correcting LLM Uncertainty Expression in Safety-Critical Advice"

### Section Status
| Section | Words | Status |
|---------|-------|--------|
| 1. Introduction | ~600 | ✅ |
| 2. Related Work (3 subsections) | ~1500 | ✅ |
| 3. UCS Framework | ~900 | ✅ |
| 4. Benchmark (MaxFitCalib-Bench) | ~1300 | ✅ |
| 5. System (CheckMyCoach M1-M4) | ~1700 | ✅ |
| 6. Human Evaluation | — | ⚠️ Pending IRB |
| 7. Discussion | ~500 | ✅ |
| 8. Limitations (7 points) | ~900 | ✅ |
| 9. Conclusion | ~400 | ✅ |

### Notes
- Introduction narrative shifted from "overconfidence" to "precision illusion" after real data showed 0% Overconfident
- Limitations cover: LLM judge bias, ordinal scale issues, small per-cell N, 6.3% problem size, generalizability, UCS construct validity, user detection assumption
- Appendix includes: UCS examples table, test suite summary, Stage 1 profiling
- `references.bib` has 14 entries

---

## Blockers
- **Blind review data:** 1/5 returned (48 items, individual ratings). 4 pending. Once all in → run ANOVA → select top-6 per category → final 24 stimuli.
- **IRB:** Submitted, pending approval. Once approved → deploy PathB_问卷页面.html → recruit N=105.

**Neither blocker depends on engineering work.**

---

## Design Decisions & Corrections (History)

### M2 needs_manual_review (corrected after user review)
- **Before:** manual_review → forced CONTEXT_MISMATCH with 0.9 confidence
- **After:** manual_review → modulate confidence only (cap at 0.6), keep feature-based diagnosis

### M1 UCS=2 (Hedged) handling (corrected after user review)
- **Before:** UCS=2 + ECS=0 → needed calibration
- **After:** UCS=2 always passes (confidence direction opposite to rest of pipeline)

### README data error (corrected)
- README claimed 18.3% Overconfident / 53.2% Calibrated
- Real data: 0% Overconfident / 92.9% Calibrated
- README updated with correct values

### 4-model comparison (abandoned)
- Tried adding Claude Haiku + GPT-4o-mini via OpenRouter
- Three different judges (GPT-4o-mini, DeepSeek V4 Pro) gave inconsistent results
- Conclusion: 2-model paper is cleaner. Haiku/GPT-4o-mini responses saved in `data/baselines/` for future use.
- OpenRouter $10 credit, ~$1-2 used, ~$8 remaining.

### Paper editing policy (explicit user instruction)
All edits to `paper.tex` and `CheckMyCoach/` files should be done directly without asking permission.

---

## Environment

| Resource | Location / Key |
|----------|---------------|
| OpenRouter API | `OPENROUTER_API_KEY` in `.env` (~$8 remaining) |
| DeepSeek API | `DEEPSEEK_API_KEY` in `.env` (直连 key, direct API) |
| R 4.6.1 | `D:\R-Portable\R-4.6.1` with lme4 + lmerTest + ggplot2 + effectsize |
| Python | System Python 3.12 with pingouin 0.6.1, scipy 1.15.2, statsmodels 0.14.4 |
| Model | deepseek-v4-flash (can escalate with `<<<NEEDS_PRO>>>`) |
| Monthly budget | ~¥500 (~$70) |

## Key File Paths

```
C:\Users\gbx12\projects\FitCalib-Bench\
├── CheckMyCoach\
│   ├── paper.tex                    ← Main paper (8/9 sections)
│   ├── references.bib               ← 14 references
│   ├── calibration_agent\           ← M1-M4 code + tests (44 total)
│   ├── 刺激材料_48条_验证版.csv         ← 48 stimuli (12 bases × 4 UCS)
│   ├── 盲评数据_1人.json              ← Blind review data (1 person)
│   ├── PathB_问卷页面.html            ← Experiment questionnaire
│   ├── merge_data.py                ← Data merger (JSON → CSV)
│   ├── path_b_analysis.R            ← LMM analysis script (+ R 分析管线)
│   ├── baseline_comparison.json     ← 24-case evaluation results
│   ├── project_brief.md             ← This file
│   └── figures\                     ← TikZ figures for paper
├── CalTrust\
│   ├── app\ml\                      ← LinUCB + XGBoost + SBERT
│   ├── app\pipeline\                ← Orchestrator + StimulusManager
│   ├── app\frontend\                ← Streamlit (4 screens)
│   ├── data\simulation_trials.csv   ← 19,200 trials
│   ├── data\models\                 ← XGBoost trained model (1.2MB)
│   └── notebooks\                   ← Simulation + training scripts
├── evaluation\ucs_engine.py         ← UCS classifier (4 stages)
└── data\baselines\                  ← Raw scoring data
```
