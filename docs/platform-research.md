# Platform improvement research — expert panel

Synthesis of a four-expert research panel (2026-06-06) on how soccer26 — the
transparent, World-Cup-2026 betting-analysis forecaster — should evolve. Lenses:
**(Q)** quantitative sports-modeling, **(U)** UX / trust / conversion, **(G)**
product growth & monetization, **(C)** competitive / market positioning. Each
expert returned ~12 recommendations grounded in web research; this doc
de-duplicates them, surfaces where they **converge**, and ends with a prioritized
cross-cutting plan. A companion **front-end** critique lives in
`docs/frontend-improvement-plan.md`.

> Framing held by all four: the moat is **honest, auditable credibility**, and the
> CLV track record is the asset everything monetizable is downstream of. Don't drift
> toward "tips."

---

## 0. The unblockers everyone circled

Two foundational items gate a surprising amount of the rest:

1. **Deploy a domain + set `site` in `astro.config.mjs`** (G, also implied by U/C).
   Today there's no domain, so OG cards, the RSS feed, and the (un-built) XML
   sitemap all carry relative/broken URLs and the 173 pages earn zero organic
   traffic. ~30 min of work unblocks social sharing, sitemap indexing, and absolute
   feed URLs. **Highest enabling leverage.**
2. **Closing-odds capture from a sharp book (Pinnacle/Betfair)** (C#11, Q, matches
   the standing HANDOFF blocker). The CLV grading, de-vig benchmark, and any
   market-divergence feature all depend on it. Operational, not code — but it's the
   single highest-leverage data investment before kickoff.

---

## 1. Model & data (lens Q — highest-leverage first)

Net-new or deeper than the backlog's existing model TASK-ids:

- **xG-seeded goal rates instead of actual goals (Q#2, M).** xG regresses out
  finishing luck and gives a denser signal for data-sparse international sides;
  club-football literature shows ~3–6% log-loss gains from the same Poisson
  architecture fed xG. Largest expected accuracy lever.
- **Attack/defence rating split, SPI-style (Q#1, M).** Replace the single Elo scalar
  with λ_att/λ_def so the Poisson inputs are structurally correct (separates the
  4–3 thriller from the 1–0 grind). Backlog TASK-031 names it; Q frames it as *the
  mechanism* that seeds everything else.
- **Market-blend as a Bayesian prior (Q#11, S).** Treat the Pinnacle opening line as
  a prior and the model as the likelihood; a weighted blend beats pure-model or
  pure-market in CLV studies. Cheap, high-impact, and philosophically compatible
  with "honest."
- **Shin (or power) de-vig instead of multiplicative (Q#5, S).** Multiplicative
  mis-prices the favourite–longshot axis; Shin models insider proportion explicitly.
  Run in parallel and keep whichever tracks the sharp no-vig line. Affects which
  edges you surface.
- **CRPS + cross-tournament out-of-sample backtest (Q#6, C#4, M).** Evaluate on
  WC2018/22, Euro 2016/20, Copa 2021/24 (~250 held-out matches) with CRPS
  (calibration vs sharpness decomposition) and CLV vs the close. Turns the honest
  "not yet proven" caveat into a *quantified* claim. **Convergent with C.**
- **Altitude / climate / rest-day & travel covariates (Q#3, Q#12).** 2026-specific:
  Estadio Azteca at 2,240 m, cross-continental USA/CAN/MEX travel, heat. Markets
  under-price physiology → potential CLV alpha and a proprietary data angle.
- **In-tournament Bayesian rating updates (Q#9, M).** Update λ posteriors as group
  games land so knockout predictions reflect form (backlog TASK-033 names it).
- **Uncertainty-adjusted Kelly (Q#10, S).** Bootstrap the fit to get a CI on the
  edge; stake off the *lower* bound and pass when the CI crosses zero. Directly
  encodes the "not proven" honesty into sizing.
- ✅ **Asian-handicap + totals ladder (Q#7) — partially shipped 2026-06-06:** AH and
  Asian-total *probabilities* now derive from the score matrix and render per match
  (no AH odds sourced yet → no AH edges). Q wants the rest of the ladder (O/U 1.5/3.5,
  exact-score, eventually props) as softer, less-efficient markets.
- **GBDT meta-learner ensemble (Q#8, M).** Use Dixon-Coles probs + context features
  in a gradient-boosted tree as a residual learner; competitive at small N. Higher
  overfitting risk — gate behind the cross-tournament validation above.

## 2. Trust, comprehension & UX (lens U + C)

- **Living, post-match calibration scorecard (C#1, U convergent, S).** After each
  matchday: "of calls we gave 65–75%, 71% happened." No public WC2026 site does this
  ongoing. Strongest cheap differentiator. (Backlog TASK-010 is the model side.)
- **"We said X → result Y" post-match card (U#10, S/M).** Close the loop on each
  finished match page from data that already exists (`bets.json` + the prediction
  ledger). Most satisfying repeat-trust moment.
- **Sample-size warnings on thin stats (U#2, S).** The dashboard P/L·ROI·win-rate
  cards look authoritative at N=0–4; annotate "N=X — interpret with caution" until
  N≥30. Matches the honest frame.
- **Model-freshness indicator in the header (U#3, S).** A small "updated HH:MM" chip
  that turns amber >24 h / red >72 h, so users never bet on stale numbers (also
  backlog TASK-029).
- **Beginner ⇄ Sharp view toggle on /edges (U#8, M).** Progressive disclosure:
  "simple" (favourite, edge %, best odds, bet/pass) vs the current full table.
- **First-visit "how to read an edge" walkthrough (U#4, M).** A one-time annotated
  example so "+8% DRAW" reads as a model disagreement, not a tip.
- **Match-specific uncertainty signals (U#6, S).** Thin-data confidence pill for
  low-N nations; elevate injury flags above the news panel into a verify-before-bet
  callout (the schema field already exists).
- **Shareable / "copy hash" + tweet on the ledger (U#7, S).** Make the tamper-evident
  hash a shareable verification act — it's the most novel credibility artifact and
  no competitor has it.
- **Public manifesto / conflicts-of-interest pledge (C#7, C#12, S).** A one-page "no
  affiliates, no tips, predictions timestamped before kickoff" statement — a durable
  signal no commercial product can authentically copy. Guard RSS/headlines against
  drift into tips language.
- **PWA manifest + `theme-color`, touch-openable tooltips (U#12, front-end plan, S).**
  Mobile polish + "add to home screen" retention during the tournament window.

## 3. Distribution, growth & monetization (lens G + C)

Sequenced for a solo creator with ~5 tournament weeks; **no gambling licence, no
affiliates** — every item below respects that.

- **Activate the newsletter now (G#1, S).** Wire `NEWSLETTER_ACTION` to Buttondown/
  Beehiiv free tier; one matchday digest of top edges. Every day unwired is audience
  lost. (The stub + RSS already ship.)
- **Public "Beat the Model" prediction leaderboard (G#2, G#6, C — convergent, M).**
  Free-to-play bracket where visitors' picks are scored against the model's, updated
  each matchday. Strongest no-licence retention loop; manufactures the "vs the model"
  social narrative. localStorage picks + build-time scoring for v1. **No stakes/
  prizes** → not regulated.
- **Per-team probability-over-time "drama curve" (C#5, U, M).** 538's most-shared UX:
  a team's title/advance odds drifting after each match. The Monte-Carlo + per-team
  pages already exist; add the time series. Return-visit driver for all 48 fan bases.
- **Markets-vs-model divergence tracker (C#9, M).** Surface where Pinnacle/Polymarket/
  Kalshi diverge from the model (e.g. Spain 16% market vs 19% model). Attracts the
  prediction-market-adjacent quant audience; nobody does it publicly.
- **Daily X/Twitter edge thread (G#4, S recurring).** Highest-ROI distribution; attach
  the existing OG cards. Post ~30–60 min pre-kickoff. "Analysis, not advice" in bio.
- **Reddit / football-analytics community seeding (G#10, S recurring).** r/soccer,
  r/footballanalysis, r/soccerbetting reward honest-methodology posts; the ledger is a
  genuinely novel talking point. Genuine contributions only.
- **One-time "Model Pack" download (Ko-fi/Gumroad) + "support the model" tip
  (G#3, G#8, S).** Sell the *analysis artifact* (CSV of all 104 matches: probs, edges,
  Kelly, sim odds), not advice. Self-funds The Odds API + hosting. Honest framing.
- **Long-tail SEO prose on match pages (G#7, C, S).** Add a 2–3 sentence plain-language
  preview to each match page ("[A] vs [B] — Model Prediction & Value Edge | WC2026");
  long-tail terms are ~92% of search volume and the templates already exist.
- **Email-gated edge alerts (G#11, S).** "Notify me when an edge >8% appears" — a
  utility-specific, higher-converting capture than a generic newsletter CTA.
- **Pre-committed post-tournament audit report (G#5, C#10, M — convergent).** Plan now,
  publish in July: full CLV record, calibration-vs-outcome, P/L curve, honest misses.
  The "538 vacancy" cornerstone asset and the next tournament's credibility proof.
- **Premium tier — *later* (G#9).** Do NOT launch paid during the tournament; the CLV
  record isn't proven yet and a too-early paywall damages the credibility asset. Build
  the free list now, paywall future-tournament depth after the audit.

## 4. Differentiating features (lens C)

- **Interactive group-stage "what-if" scenario explorer (C#8, M/L).** "If Brazil wins
  Group C, who do they meet?" — built on the same Poisson model so it's internally
  consistent with the published forecast. Viral during group stage.
- **Machine-readable JSON/CSV prediction feed (C#6, S).** 538's CSVs made competitors
  into distribution partners. Expose the edge data as JSON; turns rivals into
  syndicators. (RSS already ships; this is the structured-data sibling.)
- **De-vigged value-edge dashboard as the headline (C#3) — ✅ largely shipped** (`/edges`).
  C confirms it's a genuine differentiator vs OddsPortal (raw odds, no de-vig) and
  Opta (narrative, no market comparison). Keep leaning on it.

---

## 5. Cross-cutting priority synthesis

Ordered by leverage ÷ effort, weighting items where **multiple experts converged**:

| # | Action | Lenses | Effort | Why now |
|---|--------|--------|--------|---------|
| 1 | Deploy domain + `site` + sitemap | G (U,C) | XS | Unblocks OG/RSS/SEO for all 173 pages |
| 2 | Closing-odds capture cadence | C,Q | M(ops) | Foundation for CLV/divergence/honesty |
| 3 | Activate newsletter (Buttondown/Beehiiv) | G | S | Audience clock is ticking (~5 wks) |
| 4 | Living post-match calibration scorecard + "we said X→Y" card | U,C | S/M | Cheapest unmatched credibility differentiator |
| 5 | "Beat the Model" free prediction leaderboard | G,C | M | Strongest no-licence retention loop |
| 6 | Per-team probability "drama curve" | C,U | M | 538's most-shared UX; inputs exist |
| 7 | Market-blend prior + Shin de-vig | Q | S | Cheap accuracy/CLV gain |
| 8 | xG-seeded + attack/defence split | Q | M | Biggest model-accuracy lever |
| 9 | Sample-size + freshness + uncertainty signals | U,Q | S | Honest framing, low effort |
| 10 | Public manifesto + anti-tips guardrails | C | S | Durable, uncopyable positioning |
| 11 | Markets-vs-model divergence tracker | C | M | Unique, quant-audience magnet |
| 12 | Pre-committed post-tournament audit | G,C | M | The "538 vacancy" cornerstone |

**Sequencing note (from G):** 1 → 3 → daily-thread → leaderboard before R16 → plan
the audit now. Don't rush a paid tier — proving the CLV record first is the one
mistake that's hardest to reverse.

---

*Raw per-expert findings were returned to the orchestrator on 2026-06-06; this
synthesis preserves the substance and the convergence signal. The front-end-specific
critique is in `docs/frontend-improvement-plan.md`.*
