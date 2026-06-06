# Model Calibration & Backtest Report (H3)

*Quantitative-modeling pass. Date: 2026-06-05.*

This closes the deferred **H3** item from `docs/improvements.md`: the model's
constants were **hand-set and never fitted**, and there was **no measurement** of
how good the model actually is. We now have a leakage-free walk-forward backtest,
fitted constants, and honest accuracy metrics.

---

## 1. What was built

| Artifact | Purpose |
|---|---|
| `model/backtest.py` | Walk-forward backtest over `internationals.csv`; computes log-loss, Brier, RPS, accuracy, reliability bins + ECE, and a naive base-rate baseline. |
| `model/calibrate.py` | Fits 5 constants by minimising **walk-forward train log-loss** (scipy Nelder-Mead, stdlib coordinate-descent fallback); reports train vs. validation; persists `calibration.json`. |
| `model/data/calibration.json` | The fitted constants + the full train/validation metric table. Loaded by `elo.py` at import. |
| `elo.override_constants()` | Context manager so the backtest/calibrator evaluate candidate constants through the **exact same** production math (no duplicated model). |
| `tests/test_backtest.py` | 14 new pytest cases (metrics correctness, no-leakage, constant loading, fitted ≥ hand-set, beats baseline). |

### Methodology (leakage-free)

The backtest processes matches in **chronological order**. For each match it
**predicts using ratings built only from prior matches, then updates** the
ratings with the realised result. The rating that prices a match therefore never
reflects that match's outcome. A dedicated test
(`test_walk_forward_no_leakage_first_scored_match_uses_only_prior`) reconstructs
the ratings independently and asserts the predicted match contributed nothing to
its own prediction.

**Data:** martj42-style `internationals.csv`, played matches since `2020-01-01`
(5,943 matches). **Warmup:** the first 800 matches build ratings but are not
scored. **Train/validation split:** walk-forward by date — train `< 2025-01-01`
(3,916 scored), validation `>= 2025-01-01` (1,227 scored). The fit optimises
**train log-loss only**; validation is reported but never optimised on.

**Metrics** (all *lower is better* except accuracy): multiclass **log-loss**,
multiclass **Brier**, ordered **RPS** (the football standard for 1X2),
**accuracy** (argmax hit-rate), and **ECE** (Expected Calibration Error, 10-bin
reliability). Over/Under 2.5 is scored as a binary log-loss/Brier.

---

## 2. Fitted vs. hand-set constants

| Constant | Hand-set (old) | Fitted (new) | Note |
|---|---|---|---|
| `K` | 32.0 | **100.9** | International football has high roster turnover; faster Elo adaptation genuinely helps. The log-loss curve is flat across K≈80–100 (validation 0.8637 at K=80 vs 0.8648 at K=101), so this is a real, if broad, optimum — not a boundary artifact. |
| `HOME_ADV` | 65.0 | **97.3** | Closer to eloratings.net's ~100 than ClubElo's ~53. On a wider-spread rating scale this is the natural value. |
| `ELO_TO_GOAL_DIFF` | 0.0040 | **0.0023** | Lower because the fitted ratings spread wider (higher K), so each Elo point maps to fewer goals — the *product* (rating gap × coef) stays sensible. |
| `GOALS_BASELINE` | 2.55 | **2.90** | Higher mean total; the realised over-2.5 base rate in the data supports a baseline above 2.55. |
| `DIXON_COLES_RHO` | −0.05 | **−0.153** | A *stronger* low-score correction than the conventional −0.05; the data wants more draw/0-0/1-1 mass than independent Poisson gives. |

Two **scale-dependent reference constants** in the totals model
(`GOALS_STRENGTH_REF`, `GOALS_MISMATCH_REF`) were re-measured on the fitted rating
scale (mean qualified Elo ≈1826, mean group-fixture |gap| ≈177) so the
total-goals terms stay ~zero-mean across the 2026 field. The totals **shape**
coefficients (`GOALS_STRENGTH_COEF`, `GOALS_MISMATCH_COEF`) remain hand-set and
documented — they don't enter the 1X2 log-loss objective (see limitations).

The hand-set values are retained in `elo.py` as **documented fallbacks** and in
`calibration.json` as `handset_fallback`; if `calibration.json` is deleted,
`elo.py` transparently reverts to them.

---

## 3. Headline metrics (honest numbers)

### Train / validation (the fit's own split)

| | log-loss | Brier | RPS | accuracy | ECE |
|---|---|---|---|---|---|
| **Hand-set — train** | 0.9504 | 0.5618 | 0.1927 | 0.5577 | 0.0134 |
| **Fitted — train** | **0.9366** | **0.5546** | **0.1895** | 0.5603 | **0.0066** |
| **Hand-set — validation** | 0.8767 | 0.5159 | 0.1728 | 0.5982 | 0.0247 |
| **Fitted — validation** | **0.8648** | **0.5078** | **0.1692** | **0.6039** | **0.0172** |
| **Naive base-rate — validation** | 1.0447 | — | — | 0.4857 | — |

The fit improves **every** proper scoring rule on **both** train and validation,
and lowers ECE — i.e. it is not overfitting (validation moves in the same
direction as train, and the gap between them is the expected "future is a bit
easier/different" effect, not a train-only mirage).

### Full backtest (5,143 scored matches, fitted constants, active in production)

| | log-loss | Brier | RPS | accuracy | ECE |
|---|---|---|---|---|---|
| **Model (fitted)** | **0.9221** | **0.5445** | **0.1848** | **0.5707** | **0.0066** |
| Model (hand-set, prior) | 0.9328 | 0.5509 | 0.1879 | 0.5674 | 0.0137 |
| Naive base-rate baseline | 1.0517 | 0.6344 | 0.2288 | 0.4750 | — |

**Over/Under 2.5** (binary): log-loss 0.6946, Brier 0.2507.

### Reliability (full backtest, 10 deciles, pooled over H/D/A)

| predicted | observed | n |
|---|---|---|
| 0.052 | 0.065 | 1454 |
| 0.154 | 0.155 | 2205 |
| 0.259 | 0.258 | 4539 |
| 0.333 | 0.317 | 2948 |
| 0.449 | 0.455 | 1319 |
| 0.547 | 0.549 | 1077 |
| 0.647 | 0.652 | 811 |
| 0.748 | 0.772 | 593 |
| 0.845 | 0.845 | 328 |
| 0.933 | 0.948 | 155 |

Predicted and observed frequencies track tightly across the whole range; **ECE
0.0066** is excellent calibration for a model this simple.

---

## 4. Honest assessment

- **Does it beat the naive baseline?** Yes, clearly. Log-loss 0.922 vs 1.052
  (−0.13), RPS 0.185 vs 0.229, accuracy 57% vs 48%. The model adds real
  information over "always predict the average home/draw/away rates."
- **How does it compare to the literature?** RPS **0.185** is in the same
  ballpark as a good single-league Dixon-Coles (~0.19, per the research doc), and
  it's measured over a much harder, more heterogeneous set (all internationals,
  many weak/debutant sides, neutral venues). Calibration (ECE 0.007) is strong.
- **How does it compare to the market?** Typical bookmaker 1X2 log-loss for
  football is ~0.95–1.0 (per `docs/competitive-research.md`). Our **0.92** is
  *not* directly comparable — bookmaker benchmarks are usually on top-league club
  matches, whereas this is internationals (often more lopsided, hence lower
  log-loss is partly "easier"). **We have not yet benchmarked against the de-vigged
  closing line on the same matches**, which is the only fair market comparison.
  So: the model is well-calibrated and beats the naive baseline, but the claim
  "beats the market" remains **unproven** — that requires CLV tracking (below).

---

## 5. Limitations & next steps

1. **No closing-line / CLV benchmark yet.** Beating base rates ≠ beating the
   market. The next highest-value step is to store closing odds per bet and track
   **average CLV** — the honest test of edge (`bets/`, a `settle.py`).
2. **Totals-model shape is documented, not fitted.** Only `GOALS_BASELINE` is in
   the optimiser; `GOALS_STRENGTH_COEF`/`GOALS_MISMATCH_COEF` shape the O/U
   distribution and were left hand-set (they don't affect 1X2 log-loss). A
   dedicated O/U-log-loss fit would tighten the Over/Under predictions.
3. **High K (≈101) trades stability for adaptivity.** It minimises backtest
   log-loss but makes the one-shot `train_ratings.py` ratings noisier. The
   validation curve is flat from K≈80–100; if in-tournament rating stability
   matters (H6), K≈80 is a defensible, marginally-more-conservative choice.
4. **Single rating, raw goals, no time-decay (ξ), no xG.** All flagged in the
   research doc (offense/defense split, Dixon-Coles time weighting, xG signal).
   These are the Tier-2 modeling upgrades beyond this calibration pass.
5. **Internationals are heterogeneous.** A friendly and a World Cup qualifier are
   weighted equally (beyond Elo's sequential update). Match-importance weighting
   would likely help and is cheap.

---

## 6. Reproducing

```
python model/backtest.py                 # metrics with the active (fitted) constants
python model/calibrate.py                # re-fit + re-write calibration.json
python model/train_ratings.py            # retrain ratings.json on the fitted K
python model/predict.py                  # regenerate site predictions
python -m pytest tests/ -q               # 37 tests, all green
```

`elo.py` loads `model/data/calibration.json` at import; deleting that file
reverts the model to the documented hand-set fallbacks with no code change.
