# Competitive Research & Model Assessment — soccer26

*Research analyst report. Date: 2026-06-05.*

This document situates the **soccer26** prediction engine against comparable public
football-prediction products and against the academic/industry state of the art, then
gives prioritized, evidence-based recommendations. It is intentionally critical rather
than promotional.

---

## 0. What our model actually does (baseline for comparison)

From `model/elo.py`, `model/predict.py`, `model/train_ratings.py`:

- **Ratings engine:** a single Elo number per national team (`DEFAULT_RATING = 1500`),
  updated with margin-of-victory scaling. The update uses
  `K = 32`, a log-of-goal-difference multiplier, and a "FIFA-style" autocorrelation
  damper `2.2 / (rating_gap*0.001 + 2.2)`. Home advantage is a flat `HOME_ADV = 65` Elo points.
- **Training window:** only matches since `2020-01-01` are used; updates are processed in
  date order with **no explicit time-decay weighting** (recency enters only through the
  sequential Elo update, not a decay parameter).
- **Goals model:** Elo difference is mapped linearly to expected goals via
  `ELO_TO_GOAL_DIFF = 0.0040` around a fixed league baseline `GOALS_BASELINE = 2.55`
  total goals, split into `lam_home`/`lam_away`. Match outcome, Over/Under 2.5, and BTTS
  probabilities come from the **outer product of two *independent* Poisson PMFs**
  (`np.outer(h, a)`, truncated at 10 goals).
- **World Cup handling:** home advantage applies only when the listed home team is the
  host nation *and* the venue is inside that nation (`is_true_home`); all other matches
  are treated as neutral. This is a sensible, if coarse, neutral-venue rule.
- **Betting layer:** model probability minus vig-inclusive implied probability
  (`1/odds_decimal`); a "value" edge is flagged when the gap exceeds **5 percentage points**
  (`edge > 0.05`). The bet log tracks P/L, ROI, and model-vs-manual accuracy.

In one line: **margin-aware Elo → linear Elo-to-λ map → independent bivariate Poisson →
1X2/OU/BTTS → flat-threshold value detection vs. raw (vig-included) book odds.** This is a
respectable, well-understood hobbyist architecture. The sections below show exactly where
it is mainstream and where it lags best practice.

---

## 1. Similar sites / products

| Product | Core model approach | What it exposes | Free / paid |
|---|---|---|---|
| **FiveThirtyEight SPI** *(defunct Mar 2025)* | Per-team **offensive & defensive ratings** (goals expected for/against vs. average team on neutral field), combined into SPI; match scores fed into **two Poisson distributions → score matrix → 1X2**. Blended market data + adjusted goals/"adjusted goals"/xG/non-shot xG. | Forecasts, win/draw/loss %, league sims, downloadable SPI CSVs | Was free; **shut down** with ABC/Disney cuts, archives later pulled |
| **Opta / Stats Perform "Supercomputer"** | **Opta Power Rankings** club-rating system blended with **betting-market odds**; Monte-Carlo simulation (tens of thousands of sims) for outcome/league-position probabilities. Separate world-class **xG** model (~20 contextual factors per shot). | League/title/relegation probabilities, match 1X2, xG | Headline predictions free via The Analyst; underlying data is **paid/enterprise** |
| **ClubElo** (clubelo.com) | Football-specific **Elo**; margin via `G = sqrt(goal diff)`; **HFA ≈ 53 Elo pts** (calibrated to Premier League home edge). | Daily club Elo ratings, history, fixtures probabilities, CSV API | Free |
| **eloratings.net** (World Football Elo) | National-team **Elo** with match-importance weighting, MoV, and a **fixed ~100-pt home advantage**; `G = 1` for draw/1-goal win. | National-team rankings & history | Free |
| **FBref** (Sports Reference) | Not a predictor — **stats aggregator**; xG/xA sourced from **Opta**. | Per-team/player xG, shooting, possession stats | Free |
| **StatsBomb Open Data** | Not a predictor — **event-level open data** (shots, freeze-frames) to *build* xG models. | JSON event data on GitHub for select comps | Free (subset); full feed paid |
| **football-data.co.uk** | Not a model — the canonical **free historical results + closing/opening bookmaker odds CSVs** for major leagues; standard backtesting dataset. | Match results + multi-book odds CSV | Free |
| **Infogol** (Opta-powered) | **xG-based** match model → 1X2 probabilities; flags **value** when book odds exceed model probability ("footballs" = size of discrepancy). | Match probabilities, xG, value tips | Free app/site; data via Opta |
| **Pinnacle** | Not a public model — a **sharp sportsbook**. Publishes betting-education articles; its **closing line is the industry's de-facto "true probability" benchmark** (r² ≈ 0.997 vs. outcomes on ~398k games). | Sharp, low-margin odds; educational content | Odds free to view |
| **penaltyblog** (GitHub, martineastwood) | Open-source Python: **Poisson, Bivariate Poisson, Dixon-Coles**, Massey/Colley/Elo ratings, implied-prob de-vig, backtesting. | Library | Free / open source |
| **Other OSS** (epl-prediction-lab, football-predictor, modelling-football-scores, etc.) | Mix of **Elo + xG + Dixon-Coles + XGBoost ensembles**; some publish SHA-committed pre-kickoff probabilities for auditability. | Code + sometimes live picks | Free / open source |

**Where soccer26 sits:** Architecturally it is closest to **538 SPI** (Elo-like strength →
Poisson → score matrix → markets) and to the **ClubElo / eloratings.net** family for the
rating layer — but using **one** combined rating per team and an **independent** (not
bivariate, not Dixon-Coles-corrected) Poisson, whereas 538 used **separate offense/defense
ratings** and the serious public/OSS models use a **Dixon-Coles correction** and/or
**market blending**. The bet-log + ROI/auditability angle is genuinely good and is the same
discipline OSS projects like *epl-prediction-lab* emphasize (pre-commit your probabilities).

**Sources (Section 1):**
[538 club projections methodology](https://fivethirtyeight.com/features/how-our-club-soccer-projections-work/) ·
[538 2022 World Cup methodology](https://fivethirtyeight.com/features/how-our-2022-world-cup-predictions-work/) ·
[538 shutdown — Nieman Lab](https://www.niemanlab.org/2025/03/fivethirtyeight-is-shutting-down-as-part-of-broader-cuts-at-abc-and-disney/) ·
[538 shutdown — Poynter](https://www.poynter.org/commentary/2025/538-disney-abc-layoffs-shut-down-nate-silver/) ·
[Opta Supercomputer explained](https://tribuna.com/en/blogs/how-the-supercomputer-predicts-football-match-outcomes-expla/) ·
[Opta Analyst predictions](https://theanalyst.com/articles/opta-football-predictions) ·
[Opta/Stats Perform xG](https://www.statsperform.com/resource/expected-goals-xg-the-football-metric-changing-analysis-betting-and-fan-engagement/) ·
[ClubElo (ENG)](http://clubelo.com/ENG) ·
[World Football Elo Ratings — Wikipedia](https://en.wikipedia.org/wiki/World_Football_Elo_Ratings) ·
[FBref](https://fbref.com/en/) ·
[StatsBomb open-data](https://github.com/statsbomb/open-data) ·
[football-data.co.uk](https://www.football-data.co.uk/data.php) ·
[Infogol (Timeform)](https://www.timeform.com/football) ·
[Pinnacle CLV](https://www.pinnacle.com/betting-resources/en/educational/what-is-closing-line-value-clv-in-sports-betting) ·
[penaltyblog GitHub](https://github.com/martineastwood/penaltyblog) ·
[epl-prediction-lab](https://github.com/tuantqse90/epl-prediction-lab)

---

## 2. Model comparison vs. the state of the art

### 2.1 The standard methods, ranked roughly by sophistication

1. **Independent double Poisson** (what we use). Two independent Poissons → score matrix.
   The classic, transparent baseline. Known to **systematically misprice low scores**
   (under-predicts 0-0, 1-1 draws) because real home/away goals are weakly negatively
   correlated, violating the independence assumption.
2. **Bivariate Poisson** — explicitly models a covariance term between home and away goals.
3. **Dixon-Coles (1997)** — independent Poisson + a **low-score correction** (a ρ parameter
   reshaping the (0,0),(1,0),(0,1),(1,1) cells) **plus exponential time-decay weighting**
   (ξ) so recent matches count more. This is the de-facto public baseline. On Eredivisie
   2023/24, Dixon-Coles scored **RPS 0.191**, and adding time-weighting improved it to
   **RPS 0.189**.
4. **xG-based models** (Infogol, Opta, FBref-derived) — replace actual goals with
   **expected goals** as the signal, which is more stable and predictive than raw goals
   over small samples. This is the single biggest data-quality gap vs. our raw-goals Elo.
5. **Bradley-Terry / Elo variants** (ClubElo, eloratings.net, our engine) — strength-only
   ratings; cheap, robust, good for ranking, but a *rating* is not natively a *score
   distribution* — you still bolt a goals model on top (as we do).
6. **SPI-style dual offense/defense ratings** — separates a team's attack from its defense
   so a high-scoring leaky team and a low-scoring stingy team are modeled differently.
   A single Elo number **cannot** express this; it is a real expressiveness gap.
7. **Market-implied (odds-derived) probabilities** — the **benchmark to beat**, not a model
   to copy. Pinnacle's closing line correlates with outcomes at **r² ≈ 0.997**; any model
   claiming an edge must be evaluated *against the de-vigged closing line*, because the
   market already embeds injuries, lineups, and sharp money.
8. **ML ensembles / Bayesian hierarchical / state-space** — XGBoost on engineered features,
   or Bayesian dynamic models (e.g., RSS-published EPL state-space models). Higher ceiling,
   much higher complexity and overfitting risk; often only marginally beat Dixon-Coles on
   RPS.

### 2.2 Where soccer26 is *reasonable*

- **Elo as the strength backbone** is squarely mainstream for international football — it is
  literally what eloratings.net and ClubElo do, and what 538 built on.
- **Margin-of-victory scaling + a rating-gap damper** mirrors the FIFA/eloratings refinements
  (preventing blowouts and lopsided matchups from over-inflating ratings).
- **Poisson score matrix → 1X2/OU/BTTS in one pass** is exactly 538's and the OSS standard
  pipeline. Truncating at 10 goals is fine (mass beyond is negligible).
- **Neutral-venue logic for the World Cup** (`is_true_home`) is a genuinely thoughtful touch
  most naive models miss — only the three host nations get a home edge, on home soil.
- **De-vig-aware mindset**: the code computes implied probability from odds; the value gate
  is explicit and logged.

### 2.3 Where soccer26 is *weak* (specific, fixable)

1. **Independent Poisson, no Dixon-Coles correction.** We will under-price draws,
   particularly 0-0 and 1-1, and mis-price tight matches — the exact failure Dixon-Coles
   was invented to fix. This is the highest-value modeling gap.
2. **Single rating, not offense/defense.** Cannot distinguish "scores a lot / concedes a
   lot" from "low-event grinder." 538's whole edge over plain Elo was the offense/defense
   split. Our `expected_goals()` forces both λ to move symmetrically around a fixed 2.55
   baseline, so **team-specific scoring/defensive tendencies are lost** and total-goals
   (OU/BTTS) predictions are weakly grounded.
3. **No time-decay weighting (ξ).** We hard-cutoff at 2020 and otherwise weight a Jan-2020
   friendly the same as a March-2026 qualifier (beyond Elo's implicit sequential update).
   Dixon-Coles-style exponential decay is the standard fix and measurably improves RPS.
4. **Raw goals, not xG.** Every serious public model (Opta, Infogol, FBref-based) has moved
   to xG because it's more stable and predictive than scoreline luck. We use actual goals
   only. For international football, shot-level xG data is scarcer, but team-level xG for
   confederation/qualifier matches increasingly exists.
5. **Flat home advantage (65 Elo), not per-venue / per-context.** ClubElo calibrates HFA
   (~53), eloratings uses ~100; the *right* number depends on competition and altitude
   (Mexico City!) and crowd. A constant is a simplification — and for 2026 specifically,
   host-nation home edge should arguably differ across USA/Canada/Mexico and altitude venues.
6. **No squad / lineup / injury / rest information.** The market prices these; we ignore them
   entirely. This is the main reason a static rating model will struggle to beat the
   *closing* line (which moves on team news).
7. **Edge computed against vig-inclusive odds.** `implied_prob = 1/odds` does **not** remove
   the bookmaker margin, so a flat 5% "edge" is partly just the vig. Properly, de-vig the
   book (normalize across the full market) before computing edge, and ideally compare to
   **Pinnacle/closing** rather than any book.
8. **Static threshold, no staking model.** A fixed 5% edge gate with no Kelly/fractional-Kelly
   staking and no accounting for model uncertainty will mis-size bets and over-bet thin edges.
9. **Calibration constants are un-fitted.** `K`, `HOME_ADV`, `GOALS_BASELINE`,
   `ELO_TO_GOAL_DIFF` are hand-set (the code comments even say "tune … once we have the
   dataset wired up"). Until they're fit by minimizing a proper scoring rule on held-out
   data, the probabilities are not calibrated and the edges are not trustworthy.

**Sources (Section 2):**
[538 club projections (offense/defense + Poisson)](https://fivethirtyeight.com/features/how-our-club-soccer-projections-work/) ·
[Dixon-Coles explained](https://football-bet-prediction.com/articles/dixoncoles-model-explained-improving-poisson/) ·
[Dixon-Coles + time-weighting (dashee87)](https://dashee87.github.io/football/python/predicting-football-results-with-statistical-modelling-dixon-coles-and-time-weighting/) ·
[Dixon-Coles RPS 0.191/0.189 — predictionengine](https://predictionengine.app/learn/dixon-coles-soccer-model) ·
[penaltyblog (bivariate/Dixon-Coles impls)](https://github.com/martineastwood/penaltyblog) ·
[Opta/Infogol xG](https://www.statsperform.com/resource/expected-goals-xg-the-football-metric-changing-analysis-betting-and-fan-engagement/) ·
[ClubElo HFA ~53](http://clubelo.com/ENG) ·
[eloratings.net HFA ~100 — Wikipedia](https://en.wikipedia.org/wiki/World_Football_Elo_Ratings) ·
[Pinnacle closing line r²≈0.997 / CLV](https://www.pinnacle.com/betting-resources/en/educational/what-is-closing-line-value-clv-in-sports-betting) ·
[Goddard — efficiency of fixed-odds betting](https://www.stat.berkeley.edu/~aldous/157/Papers/goddard.pdf)

---

## 3. Benchmarking — how these models are actually judged

### 3.1 Probabilistic accuracy (the model itself)

- **Ranked Probability Score (RPS)** — the football-standard ordinal scoring rule (used in
  the 2017 Soccer Prediction Challenge); rewards probability mass placed *near* the true
  ordered outcome (home/draw/away). Lower is better; good Dixon-Coles models land around
  **RPS ≈ 0.19** on a single league-season.
- **Log-loss (ignorance score)** and **multiclass Brier score** — increasingly recommended
  *over* RPS because they emphasize **calibration and sharpness**; both are strictly proper.
  Brier decomposes into **uncertainty + reliability (calibration) + resolution
  (discrimination)**, which is exactly the diagnostic breakdown you want.
- **Calibration / reliability plots** — bin predicted probabilities and check that, e.g.,
  events you call "30%" happen ~30% of the time. This is the single most honest one-picture
  check and is cheap to add.

### 3.2 Betting performance (the value layer)

- **Closing Line Value (CLV)** — "did you beat the closing odds?" is *the* signal of genuine
  edge. Beating the **de-vigged Pinnacle closing line** is widely regarded as the strongest
  evidence of skill and is empirically tied to long-run profit. ROI on a small bet log is
  far noisier than CLV.
- **ROI / yield + bankroll P/L with proper sizing**, reported with confidence intervals.
- **Backtesting against historical closing odds** (football-data.co.uk gives the de-facto
  free dataset) — the standard way OSS projects validate before risking money.

### 3.3 What it would take for soccer26 to credibly claim "beats the market"

1. **Calibrate first.** Fit `K/HOME_ADV/GOALS_BASELINE/ELO_TO_GOAL_DIFF` (and any
   Dixon-Coles ρ/ξ) by minimizing **log-loss or RPS** on a held-out set of internationals;
   publish a **reliability plot**. An un-calibrated model cannot claim edge.
2. **De-vig the market** and benchmark against **Pinnacle/closing**, not against the soft
   book you happen to be betting. Edge measured vs. vig-included odds is illusory.
3. **Track CLV per bet**, not just ROI. A positive average CLV across a few hundred bets is
   far more convincing than a lucky tournament-length ROI.
4. **Pre-commit predictions** (e.g., timestamp/hash `predictions.json` before kickoff — some
   OSS projects SHA-256 commit theirs) so the audit can't be second-guessed.
5. **Out-of-sample, multi-tournament** validation. 104 World Cup matches is too small to
   establish edge on its own; backtest the same engine across historical qualifiers and
   prior tournaments.

**Sources (Section 3):**
[Better metrics beyond RPS — penaltyblog](https://pena.lt/y/2025/05/01/better-metrics-for-football-forecasts-moving-beyond-the-ranked-probability-score/) ·
[Evaluating probabilistic football forecasts (arXiv 1908.08980)](https://arxiv.org/pdf/1908.08980) ·
[Verification of probability forecasts (arXiv 2106.14345)](https://arxiv.org/pdf/2106.14345) ·
[Brier decomposition / scoring rules](https://thexgfootballclub.substack.com/p/which-machine-learning-models-perform) ·
[Pinnacle — CLV is the key skill metric](https://www.pinnacle.com/betting-resources/en/educational/what-is-closing-line-value-clv-in-sports-betting) ·
[Closing line as #1 metric (Trademate)](https://tradematesports.medium.com/closing-line-the-most-important-metric-in-sports-trading-58e56cdb4458) ·
[football-data.co.uk odds CSVs](https://www.football-data.co.uk/data.php)

---

## 4. Actionable takeaways (ranked by impact ÷ effort)

### Tier 1 — high impact, low/medium effort (do these first)

1. **De-vig odds before computing edge, and benchmark vs. closing/Pinnacle.**
   Replace `implied_prob = 1/odds` with a normalized (margin-removed) book probability, and
   where possible compute edge against the **de-vigged closing line**. This single change
   stops the model from flagging the bookmaker's vig as "value." *(Low effort, high impact.)*
2. **Calibrate the four constants by minimizing log-loss/RPS on held-out internationals, and
   add a reliability plot to the dashboard.** Turns hand-set guesses into fitted, defensible
   numbers. *(Medium effort, high impact — and required before any "beats the market" claim.)*
3. **Add the Dixon-Coles low-score (ρ) correction to `match_probabilities`.** It is a small,
   well-documented adjustment to four score-matrix cells; `penaltyblog` has a reference
   implementation. Directly fixes our known draw under-pricing. *(Low/medium effort, high impact.)*
4. **Track CLV per bet in `bets.json` / the dashboard.** Store closing odds and report
   average CLV alongside ROI. The most honest measure of whether the model has real edge.
   *(Low effort, high impact.)*

### Tier 2 — high impact, higher effort

5. **Split the rating into offense + defense (SPI-style)** so λ_home/λ_away reflect each
   team's attack and the opponent's defense, instead of a symmetric spread around a fixed
   2.55. Materially improves OU/BTTS realism. *(Higher effort, high impact.)*
6. **Add exponential time-decay weighting (ξ).** Weight recent internationals more than the
   2020 cutoff edge; empirically improves RPS. *(Medium effort, medium/high impact.)*
7. **Introduce xG (or team-level xG) as the scoring signal** where data exists for
   internationals, instead of raw goals — the direction every serious public model has taken.
   *(Higher effort, high impact, gated on data availability.)*

### Tier 3 — refinements

8. **Context-aware home advantage:** differentiate host nations and high-altitude venues
   (Mexico City/Guadalajara) rather than one flat 65-Elo constant. *(Medium effort.)*
9. **Proper staking (fractional Kelly) instead of a flat 5% gate**, sized by edge and model
   uncertainty. *(Medium effort.)*
10. **Pre-commit predictions (timestamp/hash before kickoff)** to make the audit
    tamper-evident — cheap credibility win. *(Low effort.)*
11. **Backtest the engine across prior tournaments/qualifiers** to get an out-of-sample
    RPS/log-loss and CLV baseline before the Cup. *(Medium effort.)*

### Honest bottom line

soccer26's architecture is a **sound, transparent member of the Elo→Poisson family** and is
in good company (538, ClubElo, eloratings, many OSS projects). Its gaps versus best practice
are **specific and well-trodden**: independent (un-corrected) Poisson, a single combined
rating instead of offense/defense, no time-decay, raw goals instead of xG, and a value layer
that compares against vig-included rather than de-vigged/closing odds with un-fitted
constants. None of these require ML heavy machinery — Tier 1 alone (de-vig, calibrate,
Dixon-Coles ρ, CLV tracking) would move the project from "plausible hobby model" to
"defensibly benchmarked." Beating the **closing** line, however, is a genuinely high bar that
even sophisticated public models rarely clear, precisely because that line already embeds the
lineup/injury information our static ratings omit.
