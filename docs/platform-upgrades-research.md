# Platform-upgrades research — synthesis (2026-06-06)

Five read-only research agents (forecasting/model, data-enrichment, product/UX, architecture/tech,
engagement/retention) ran in parallel. This is the cross-cutting synthesis, sequenced for a solo
dev ~5 days before kickoff. Full agent reports are summarised in the session handoff.

## The cross-cutting #1 (4 of 5 reports converge here)

**The closing-odds / CLV capture is the moat — and it's currently a single-Windows-machine, manual
process that will silently fail if the PC is off at the June 11 openers (and that data is
permanently lost).** The architecture report shows the fix is *also* the platform unlock:

> **git → Cloudflare Pages (free `.pages.dev`) → a scheduled GitHub Action that runs the pipeline +
> `capture_closing.py` and commits the JSON, which auto-triggers a deploy.**

Half a day of work. It simultaneously fixes: no version control, the manual-rebuild bottleneck,
matchday automation, the `SITE_URL` placeholder (SEO/OG/RSS), AND makes the moat **self-capturing,
machine-independent**. Critical sub-fix flagged: **un-ignore `site/public/data/predictions.json`** —
the SHA-256 ledger hashes it, so committing it to a *public* repo makes the tamper-evidence
externally verifiable (which `/methodology` currently lists as roadmap — TASK-050 follow-on).
The forecasting report adds: the same CLV data is what lets you *fit* the blend weight and *prove*
the model beats the market — so this is a modelling unlock too, not just ops.

Also convergent across reports: **shareable "we said X → result Y" receipt cards** (UX #7 + engagement
#4 — the only real growth mechanic, pipeline already built) and **prediction-market prices** (data
#1-2 + forecasting #6).

---

## Ship BEFORE kickoff (low risk, high leverage)

**Infra (do first — unblocks the rest):**
- git init + public GitHub + un-ignore `predictions.json`; Cloudflare Pages + real `SITE_URL`.
- Scheduled GitHub Action: data-gen + `capture_closing.py` → commit JSON → auto-deploy (quota-safe;
  public-repo Actions minutes are free/unlimited). Keep the local Task Scheduler as a June-11 backup.
- Pin Python deps + commit `package-lock.json`; a `push`-triggered CI mirroring `check.ps1`.

**Data (free, on-brand, novel):**
- **Polymarket + Kalshi public read APIs** → add their prices to `/divergence` + the Model-vs-market
  panel. "Model vs sportsbooks vs real-money markets" — no key, no licence, no affiliate.

**Model (all through the existing `calibrate.py`/`backtest.py` harness — keeps ECE 0.007):**
- Match-importance K-weighting; exponential time-decay ξ; extend the market blend to **O/U + BTTS**
  on the **logit scale**; a Glicko-style rating-uncertainty **confidence flag** (+ Kelly caution).
- Optional low-risk: a *blendable* attack/defence prior (fit offline, averaged into the λ's) — the
  safe pre-kickoff cousin of the full split.

**UX (the "legibility batch"):**
- First-run onboarding overlay + inline "what this means" interpreters on every probability surface.
- Uncertainty bands on the reliability + equity charts (reuse the Wilson CI just shipped).
- Tap-openable tooltips on mobile + colour-blind cue on the prob bar (open a11y gaps).
- Score-matrix heatmap + model-vs-market diverging bar on match pages (the bar is S, no model change).

**Engagement:**
- Activate the newsletter stub + web push via OneSignal (works on a static site, no backend).
- One-tap "share this receipt" buttons on the post-match cards.
- **Pre-commit the post-tournament audit** (a page + the hash ledger) — must publish *before* 11 Jun.

## Tournament-critical (by specific dates)

- **In-tournament dynamic rating updates + knockout re-prediction — ready by the June 18 knockouts**
  (frozen ratings ignore the group stage that just happened; results pipeline already exists).
- Matchday **live command-centre** dashboard (reuses the `live.json` poller + countdowns + `clvStats`).
- **Public "Beat the Model" leaderboard** by kickoff (needs a tiny serverless store — Cloudflare D1 /
  Supabase free; self-chosen handle, no PII, picks stay in localStorage).
- OG-render caching + `_headers` edge-cache for `live.json` → fast matchday rebuilds.

## Post-tournament (high impact, don't rush — validated branch)

- **Attack/defence (λ) split (TASK-031)** — the real model upgrade for totals/BTTS *shape*; a full
  re-fit + re-validation, too risky to land days before kickoff (confirmed by the forecasting agent).
- Bayesian state-space bivariate Poisson (unifies dynamic abilities + uncertainty); xG priors
  (data-gated — international xG coverage is patchy for minnows); gradient-boosting *meta-blender*
  (only worth it with squad-value/player features — ML ≈ Poisson otherwise).
- Per-team "drama curves"; a forecasting-only Discord; PWA push; print/colour-blind modes.

## Guardrails (from the engagement report — the bright lines)

No "bet now" / sportsbook deep-links / affiliate buttons anywhere (incl. alerts + OG cards). No
picks/handicapper Discord ("tail my play" / VIP tips). No "lock of the day" framing. No PII/accounts
for the leaderboard. Note: X's 2026 policy now *prohibits* paid promo partnerships with betting
accounts — which only reinforces the organic, receipts-driven path.

## The meta-point

soccer26's biggest remaining edge is **not** a fancier algorithm (ML ≈ Poisson). It's (a) a richer
rating layer + a better-fitted market blend, and (b) finally **capturing the CLV record** — which is
simultaneously the ops blocker, the credibility moat, the modelling-validation input, and the
engagement asset. The infra unlock at the top makes that capture happen automatically. Do it first.
