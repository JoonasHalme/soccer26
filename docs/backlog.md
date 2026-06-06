# soccer26 — Backlog

A single, durable, prioritized backlog for the World Cup 2026 betting-analysis
site. It folds together the expert-panel **viability roadmap**, the
engineering/model **improvements** audit, and the **competitive / calibration /
news-feed** research into discrete, implementable tasks.

Each task has a stable ID (cite it in commits/PRs), a one-line rationale, a
concrete scope, the real files it will touch, dependencies, an effort estimate
(**S** <0.5 day · **M** 0.5–2 days · **L** >2 days), and acceptance criteria.
Pick any task up cold and ship it.

The honest strategic frame (from the viability roadmap): this is **not** viable as
a "sharp tips that beat the market" product. It is viable as the **transparent,
honestly-graded, World-Cup-focused forecaster** that wins trust on credibility and
monetizes via content + newsletter, earning a premium tier only after a public CLV
record proves real edge. The backlog is ordered to build that trust infrastructure
first.

---

## Recently shipped (✅)

The model and site foundation are in good shape. Treat all of the following as
**done** — do not re-task them:

- ✅ **De-vigged edges** — `predict.py` normalises each market (1X2 trio, O/U
  pair) to fair probabilities summing to 1 before computing `edge = model − fair`;
  unpriced markets are skipped. (`model/predict.py`)
- ✅ **Matchup-specific Over/Under** — `expected_goals()` scales total goals by
  pair strength + mismatch instead of partitioning a fixed 2.55; ~70 distinct
  Over-2.5 values across the field. (`model/elo.py`)
- ✅ **Dixon-Coles low-score correction** — `rho` adjustment on the
  0-0/1-0/0-1/1-1 cells in `match_probabilities`. (`model/elo.py`)
- ✅ **Betting-discipline validator** — `validate_bets.py` enforces schema + the
  >5%-edge-or-rationale gate (non-zero exit), checks `match_id` resolves, reports
  model-vs-manual hit-rate/ROI. (`model/validate_bets.py`, `bets/schema.json`)
- ✅ **Calibration + walk-forward backtest** — `backtest.py` (log-loss, Brier,
  RPS, ECE, reliability bins, base-rate baseline) and `calibrate.py` (fits 5
  constants, persists `data/calibration.json`, loaded by `elo.py` at import).
  Model ECE 0.0066, RPS 0.185, beats naive baseline. (`docs/calibration.md`)
- ✅ **RSS news feed** — key-less `fetch_news.py` (BBC/Guardian/ESPN), team-tagged
  + injury-flagged, writes `site/public/data/news.json`; rendered on dashboard and
  match pages via `NewsItem.astro`. (`model/fetch_news.py`)
- ✅ **Group standings + flags** — `computeStandings()` + `GroupCard.astro` /
  `TeamFlag.astro` / `flagCode()` on `groups.astro`.
- ✅ **Per-bookmaker European odds / line-shopping data** — `fetch_odds.py` stores
  a `books[]` array per fixture; `bestBookPrices()` in `data.ts` and
  `BookmakerOdds.astro` surface them. (NB: the data + best-price helper exist; the
  *aggregated edges page that consumes best price* is still TASK-002.)
- ✅ **CLV + results-settlement pipeline** — shipped end-to-end (runs clean on the
  current empty state, activates with real data):
  - `fetch_results.py` pulls completed scores from The Odds API into
    `fixtures.json` (`match.score`/`status`); safe on the "0 games played" case.
  - `settle.py` grades each bet → `result`/`pnl`/`settled_at` (1X2, totals, BTTS,
    **Asian handicap** incl. quarter-line half-win/loss/push); idempotent, `--dry-run`.
  - `clv.py` de-vigs the **closing** line via `predict.devig_market()` and writes
    `closing_odds_decimal`/`closing_fair_prob`/`clv_pct`, plus portfolio beat-rate
    and average CLV. (Aggregate **confidence interval** still TASK-011.)
  - Closing capture: `fetch_odds.py --closing` snapshots the last pre-kickoff
    line (consensus + best-of-book) to `match.closing_odds`.
  - Tamper-evident predictions: `predict.py` writes a SHA-256 + timestamp sidecar
    `predictions.hash.json`. (Append-only ledger + on-site display still TASK-021.)
  - Site: CLV scoreboard on `bets.astro` (avg CLV, beat-rate, settled P/L, ROI) +
    P/L split **by source** and **by market** via `clvStats()`/`splitPnl()` in
    `data.ts`; new `bets/schema.json` fields; CLV column on `matches/[id].astro`.
    (P/L equity curve + edge/CLV-bucket splits still TASK-001 / TASK-022.)
  - **63 pytest tests** green (settlement grading per market, idempotency, CLV sign,
    empty inputs).
- ✅ **Pipeline + visual redesign** — `fetch_fixtures.py` → `parse_fixtures.py`
  wired end-to-end (groups + knockouts); 23+37 pytest tests green; redesigned
  Astro site (`Base.astro`, `MatchCard.astro`, `ProbBar.astro`, `StageChip.astro`).

## Shipped in the latest pass (✅) — the whole P0 sequence + finishes

Worked top-to-bottom through the suggested sequencing. Done, built (110 pages),
**75 pytest tests green**:

- ✅ **TASK-003** — best-book price + realisable EV on every edge (`predict.py`
  `best_price()`/`find_edges`), measured RAW (de-vigging the best line would cancel
  the shopping value). Tested.
- ✅ **TASK-002** — `/edges` page: every value edge across all fixtures, best book
  price + book, EV, ¼-Kelly stake; client-side market filter + sort by edge/EV/kickoff.
- ✅ **TASK-004** — fractional-Kelly staking (`model/staking.py` + `kellyStake()` in
  `data.ts`), capped, surfaced on `/edges`; bets.json carries `kelly_fraction`/`kelly_cap_pct`. Tested.
- ✅ **TASK-005** — `model/add_bet.py --edge <id> --odds <p>`: pre-fills + validates +
  appends a bet (¼-Kelly default stake); non-zero exit on bad edge id.
- ✅ **TASK-006** — site-wide RG / 18+ / not-advice / affiliate-disclosure footer.
- ✅ **TASK-007** — date-aware "Today / next matchday" dashboard hero with live
  kickoff countdowns (`nextMatchday()` + `KickoffCountdown.astro`).
- ✅ **TASK-001** — finished the CLV scoreboard: bankroll **equity curve** (SVG,
  `pnlSeries()`) + the settled-call hit/miss list. Empty-state safe.
- ✅ **TASK-011** — CLV **confidence interval** (t-based, `mean_ci` in `clv.py`,
  `meanCI` in `data.ts`), shown as "95% CI …" on the scoreboard. Tested.
- ✅ **TASK-009** — `/calibration` page: reliability curve + headline metrics +
  fitted-vs-hand-set table, fed by `model/export_calibration.py`.
- ✅ **TASK-008** — repositioned homepage hero + README around transparency /
  calibration / honest "not yet proven to beat the market".

Nothing else in active development. Remaining tasks below are untouched.

---

## P0 — Now (the trust infrastructure all three experts converged on)

### TASK-001 — Public CLV + ROI scoreboard ("model report card") — ⚠️ mostly shipped
- **Why:** A continuously-graded, tamper-evident CLV track record is the one thing
  all three advisors agreed is the entire business problem; everything monetizable
  is downstream of it.
- **Status:** The scoreboard core landed on `bets.astro` (avg CLV, beat-rate,
  settled P/L, ROI cards; CLV column; `clvStats()` in `data.ts`; schema fields).
  **Remaining scope only:** (1) a P/L **equity curve** / cumulative-bankroll chart
  (hand-rolled SVG or a light dep), (2) a **settled-call hit/miss list** with each
  call's CLV, (3) optional public framing/polish (a clearer "track record" headline,
  link from nav) so it reads as the report card, not just the bet log.
- **Files likely touched:** `site/src/pages/bets.astro`, `site/src/lib/data.ts`
  (a `pnlSeries()` cumulative helper), optional small SVG chart component.
- **Dependencies:** none (pipeline shipped).
- **Effort:** S
- **Acceptance criteria:**
  - [ ] An equity/P-L curve renders from settled bets (empty-state safe).
  - [ ] A hit/miss list of settled calls shows each call's result and CLV.

### TASK-002 — Aggregated "all current value edges" page (best-price)
- **Why:** The actionable centerpiece of the whole workflow and the newsletter
  teaser; today only the single top edge shows on the dashboard.
- **Scope/what to build:** A sortable/filterable route listing every model edge
  above threshold across all matches, priced against the **best available book**
  (use `bestBookPrices()`), not consensus. Columns: match, market, selection,
  model prob, best price + book, edge %, kickoff. Sort by edge/kickoff; filter by
  market/threshold.
- **Files likely touched:** new `site/src/pages/edges.astro`,
  `site/src/lib/data.ts` (an `allEdges()` aggregator joining predictions +
  `bestBookPrices`).
- **Dependencies:** none (best-price data already shipped).
- **Effort:** S/M
- **Acceptance criteria:**
  - [ ] `/edges` lists every above-threshold edge across all fixtures.
  - [ ] Each row shows the best book price/name and edge computed against it.
  - [ ] At least sortable by edge and kickoff time.

### TASK-003 — Edge against best book price in the model layer
- **Why:** Pricing edges vs the best available book (not consensus median) is worth
  several % EV/bet; the research flags consensus pricing as leaving money on the
  table.
- **Scope/what to build:** In `predict.py`, in addition to the consensus-based
  edge, compute a `best_price_edge` per selection from each fixture's `books[]`
  (de-vig the best-book market the same way `devig_market()` does, or at minimum
  surface best decimal odds + which book). Emit it into `predictions.json`.
- **Files likely touched:** `model/predict.py`, `site/src/lib/data.ts` (types for
  the new field).
- **Dependencies:** none.
- **Effort:** M
- **Acceptance criteria:**
  - [ ] `predictions.json` edges carry best-book price, book name, and best-price
        edge alongside the consensus edge.
  - [ ] A test asserts best-price edge ≥ consensus edge when a sharper book exists.

### TASK-004 — Fractional-Kelly + flat staking engine
- **Why:** Turns the binary 5% gate into bankroll-aware position sizing; a flat
  threshold with no staking model over-bets thin edges.
- **Scope/what to build:** A staking helper that, given model prob, best price, and
  bankroll/unit config (`starting_bankroll`, `unit_size` already in `bets.json`),
  returns a fractional-Kelly stake (configurable fraction, capped) and a flat-stake
  alternative. Surface the suggested stake on the edges page / bet-slip.
- **Files likely touched:** new `model/staking.py` (or a function in `predict.py`),
  `site/src/lib/data.ts`, `site/src/pages/edges.astro`, `bets/bets.json` (config).
- **Dependencies:** TASK-003 (best price feeds Kelly).
- **Effort:** S/M
- **Acceptance criteria:**
  - [ ] Given prob+odds+bankroll, the engine returns a capped fractional-Kelly
        stake and a flat stake.
  - [ ] Suggested stake renders next to each surfaced edge.
  - [ ] Unit test: Kelly = 0 when edge ≤ 0; scales with edge.

### TASK-005 — Quick bet-logging helper
- **Why:** Removes friction from capturing the track record now (qualifiers/
  friendlies); a copy-paste-free path from edge → logged bet.
- **Scope/what to build:** `add_bet.py --edge <id> --odds <price> [--stake X]`
  that reads the edge from `predictions.json`, pre-fills `match_id`, `market`,
  `selection`, `model_edge_pct`, `model_prob`, appends a schema-valid entry to
  `bets/bets.json`, and runs `validate_bets.py`. Optionally emit a pre-filled
  bet-slip snippet on the edges page.
- **Files likely touched:** new `model/add_bet.py`, `bets/bets.json`,
  `model/validate_bets.py` (reuse), optionally `site/src/pages/edges.astro`.
- **Dependencies:** TASK-002 (edge ids), TASK-004 (stake default).
- **Effort:** S
- **Acceptance criteria:**
  - [ ] `add_bet.py --edge <id> --odds <price>` appends a valid bet and passes the
        validator.
  - [ ] Refuses (non-zero exit) if the edge id doesn't resolve.

### TASK-006 — Compliance / responsible-gambling disclaimer (site-wide)
- **Why:** Currently entirely absent; an RG / 18+ / "not advice" line is table
  stakes for any public gambling-adjacent site and a near-zero-effort credibility
  win.
- **Scope/what to build:** A persistent footer disclaimer in the shared layout:
  18+/21+ jurisdiction note, "for entertainment / not betting advice", an RG
  helpline link, and an affiliate-disclosure stub. Independent of TASK-018.
- **Files likely touched:** `site/src/layouts/Base.astro` (footer), optional
  `site/src/components/Disclaimer.astro`.
- **Dependencies:** none.
- **Effort:** S
- **Acceptance criteria:**
  - [ ] Every page renders the RG/age/not-advice disclaimer in the footer.
  - [ ] An affiliate-disclosure stub is present (even if affiliate links aren't).

### TASK-007 — "Today / this matchday" dashboard hero + kickoff countdowns
- **Why:** Reframes the dashboard around "what do I look at now"; the product lead's
  top retention lever.
- **Scope/what to build:** A hero section at the top of `index.astro` showing
  today's / the next matchday's fixtures with live kickoff countdowns, each fixture's
  top edge, and a LIVE/UPCOMING/FT pill. Falls back to "next matches" when none today.
- **Files likely touched:** `site/src/pages/index.astro`, `site/src/lib/data.ts`
  (a `todaysFixtures()` / `nextMatchday()` selector), optional
  `site/src/components/KickoffCountdown.astro`.
- **Dependencies:** none (TASK-019 enriches with live scores once available).
- **Effort:** S
- **Acceptance criteria:**
  - [ ] The dashboard leads with today's/next matchday fixtures + countdowns.
  - [ ] Each hero fixture shows its top edge and a status pill.

---

## P1 — Next (high value, builds on the trust layer)

### TASK-008 — Reposition copy: "the transparent, auditable WC2026 model"
- **Why:** Claims the credibility niche 538's SPI shutdown vacated; aligns the
  pitch with what's actually defensible (honest grading, not "sharp tips").
- **Scope/what to build:** Rewrite the homepage hero/intro and README tagline to
  lead with transparency, calibration, and the public track record. Link the
  calibration report. Remove any "beats the market" implication that isn't proven.
- **Files likely touched:** `site/src/pages/index.astro`, `README.md`, optional
  `site/src/pages/about.astro` or `methodology.astro`.
- **Dependencies:** TASK-009 (so "see the calibration" links somewhere).
- **Effort:** S
- **Acceptance criteria:**
  - [ ] Homepage copy leads with transparency/calibration, not tips.
  - [ ] No unqualified "beats the market" claim remains.

### TASK-009 — Publish the calibration report on the site
- **Why:** The reliability curve + RPS/log-loss/ECE are the proof of honest
  forecasting and the core of the new positioning.
- **Scope/what to build:** A page that renders `data/calibration.json` (or the
  backtest output): the reliability table/curve, headline metrics, and the
  base-rate comparison from `docs/calibration.md`. Static, build-time.
- **Files likely touched:** new `site/src/pages/calibration.astro`,
  `site/src/lib/data.ts` (load calibration JSON), possibly copy
  `model/data/calibration.json` into `site/public/data/`.
- **Dependencies:** none.
- **Effort:** S/M
- **Acceptance criteria:**
  - [ ] A public page shows the reliability curve and headline metrics.
  - [ ] Numbers are read from the calibration artifact, not hardcoded.

### TASK-010 — Live calibration tracking (tournament predictions vs outcomes) — ✅ mostly shipped via TASK-043
- **Why:** Shows model vs de-vigged-closing reliability side by side as the Cup
  unfolds — the live proof the model stays calibrated on 2026 matches.
- **Status:** The **model-side** live reliability shipped as **TASK-043** (the
  "Tournament 2026 — live" section on `/calibration`, fed by the prediction archive).
  **Remaining scope only:** the *de-vigged-closing* reliability series shown beside the
  model's — which needs the **closing-odds capture cadence** (the #1 ops blocker) to
  have data. Add it once closing snapshots exist.
- **Acceptance criteria:**
  - [x] Tournament-to-date reliability bins render once results settle.
  - [ ] Model and de-vigged-closing reliability shown side by side (needs closing odds).

### TASK-011 — CLV-vs-de-vigged-closing benchmark (the only fair market test) — ⚠️ mostly shipped
- **Why:** The calibration doc explicitly flags this as the missing honest test:
  beating base rates ≠ beating the market; only CLV vs the closing line proves edge.
- **Status:** Per-bet CLV vs the de-vigged closing line, plus portfolio beat-rate
  and average CLV, are computed in `clv.py` and tested (sign correctness covered).
  **Remaining scope only:** add an aggregate **confidence interval** (the sample is
  tiny, so the CI is the honest part of the claim) and surface "avg CLV ± CI" on the
  scoreboard, with a test for the CI.
- **Files likely touched:** `model/clv.py` (CI computation), `site/src/lib/data.ts`
  + `site/src/pages/bets.astro` (render the CI), `tests/test_clv.py`.
- **Dependencies:** none (pipeline shipped).
- **Effort:** S
- **Acceptance criteria:**
  - [ ] Aggregate CLV is reported with a confidence interval.
  - [ ] The scoreboard shows avg CLV ± CI; a test covers the CI.

### TASK-012 — Client-side search / filter / sort across matches & edges — ✅ shipped 2026-06-06
- **Why:** Findability across 104 matches and the edge set; cheap, builds on
  existing JSON.
- **Status:** Done for the matches index: a client-side search box (by team), stage
  filter chips, a "Top edge / Kickoff" sort, and a "★ Following" watchlist filter —
  no reload, hides empty stage sections, live aria-live count. (`/edges` already had
  market filter + sort + the longshot/exposure work, so it was left as-is.)
- **Files touched:** `site/src/pages/matches/index.astro`.
- **Acceptance criteria:**
  - [x] Users can filter/sort matches client-side with no page reload.

### TASK-013 — Asian Handicap / Asian totals markets — ✅ shipped (probabilities) 2026-06-06
- **Why:** Lowest vig in football; the score matrix already prices them.
- **Status:** AH + Asian-total **probabilities** now derive from the Dixon-Coles
  score matrix (`elo.asian_probabilities`, fed by a new shared `elo.score_matrix`),
  emit into `predictions.json` (`asian` block), and render on each match page
  (handicap table from the home team's side with pushes on whole lines + a totals
  ladder). Cross-checked: AH -0.5 home == 1X2 home win, AH 0 push == draw, AT 2.5
  over == O/U 2.5. **7 new pytest.** No AH odds are sourced, so no AH edges surface
  (the deliberate "suppress when no odds" branch).
- **Files touched:** `model/elo.py`, `model/predict.py`, `site/src/lib/data.ts`,
  `site/src/pages/matches/[id].astro`, `tests/test_asian.py`.
- **Acceptance criteria:**
  - [x] AH and Asian-total probabilities appear per match.
  - [x] AH edges surface only when AH odds are present (none sourced ⇒ none shown).
- **Follow-up:** source AH/Asian-total **odds** in `fetch_odds.py` to unlock AH edges
  (uses Odds-API quota — be frugal); extend the totals ladder (1.5/3.5/exact score).

### TASK-014 — Newsletter + RSS digest of new edges & news — ✅ shipped 2026-06-06
- **Why:** The realistic monetization on-ramp (no gambling licence needed); the
  strategist's recommended first revenue layer.
- **Status:** Done. `site/src/pages/feed.xml.ts` builds a **hand-rolled RSS 2.0**
  feed (40 items — top 20 value edges + 20 tagged news), well-formed + XML-escaped,
  working with no configured domain (links auto-upgrade to absolute via `Astro.site`).
  New `Newsletter.astro` signup component on the dashboard — a **stub** (set
  `NEWSLETTER_ACTION` to a Buttondown/Substack embed to go live) that honestly points
  to the working RSS feed meanwhile. RSS autodiscovery `<link>` in `Base.astro` head +
  a footer feed link.
- **Files touched:** new `site/src/pages/feed.xml.ts`, new
  `site/src/components/Newsletter.astro`, `site/src/pages/index.astro`,
  `site/src/layouts/Base.astro`.
- **Acceptance criteria:**
  - [x] A valid RSS feed of new edges + news is generated at build.
  - [x] A newsletter signup entry point is present on the site.
- **Note:** email signup is a stub until `NEWSLETTER_ACTION` is wired to a provider;
  RSS is fully functional now. A standalone human-readable `/digest` page was skipped
  (the dashboard already surfaces edges + news; the feed covers syndication).

### TASK-015 — Shareable OG / edge share cards — ✅ mostly shipped 2026-06-06
- **Why:** The only real growth/distribution mechanic; makes edges and the report
  card shareable.
- **Status:** Done. Build-time 1200×630 PNGs via **satori → @resvg/resvg-js**
  (`site/src/lib/og.ts`), fonts vendored as static TTFs in
  `site/src/assets/og-fonts/` (Inter + Sora — keeps the build fully offline).
  Cards: per-match (104, with the **model probability bar** Home/Draw/Away %),
  per-team (48), per-group (12), a tailored **track-record** card, and a default
  site card — 166 images total. `Base.astro` emits `og:image`/`twitter:image`
  (+ width/height) as `summary_large_image`; pages set `ogImage` (match/team/group/
  bets override, the rest use the default). `og:image` is a path now and
  auto-upgrades to absolute via `new URL(ogImage, Astro.site)` once `site` is set.
- **Files touched:** new `site/src/lib/og.ts`, `site/src/pages/og/*` endpoints,
  `site/src/assets/og-fonts/*.ttf`, `site/src/layouts/Base.astro`, match/team/group/
  bets pages. Deps added: `satori`, `@resvg/resvg-js`, `satori-html`.
- **Acceptance criteria:**
  - [x] Match/edge/track-record pages emit OG + Twitter image meta.
  - [x] Cards render with the model number (prob bar). *(Team flags deferred — they're
        remote flagcdn images; embedding them would need a build-time fetch and break
        offline builds. Card uses brand + matchup + prob bar instead.)*
- **Notes:** OG rendering adds ~30s to `npm run build` (166 satori renders); `npm run
  dev` is unaffected (endpoints render on demand). Two follow-ups: real flags (fetch +
  cache flagcdn PNGs, or vendor a flag sprite); absolute `og:image` URLs need the
  deploy domain (same blocker as the sitemap) before cards render on social.

### TASK-016 — Onboarding "How to read this" + jargon tooltips — ✅ shipped 2026-06-06
- **Why:** Trust + shareability; newcomers don't know edge/de-vig/xG/Elo/CLV.
- **Status:** Done. The explainer landed as `/methodology` (how the model works,
  finding value, honest grading, the tamper-evident ledger, a plain-language
  **glossary** of Elo/Poisson/Dixon-Coles/de-vig/edge/EV/Kelly/CLV/ECE, and honest
  limitations; nav + footer linked). A reusable, keyboard- + SR-accessible
  `Tooltip.astro` (dotted-underline term, hover/focus bubble, `aria-label`) is wired
  on the highest-jargon surfaces for the terms each page *uses but doesn't define* —
  "de-vigged" + "Kelly" on `/edges`, "de-vigged" on `/bets`; `/calibration` already
  carries `<abbr>` glosses on its metrics.
- **Files touched:** new `site/src/components/Tooltip.astro`, `site/src/pages/edges.astro`,
  `site/src/pages/bets.astro`, `/methodology`.
- **Acceptance criteria:**
  - [x] An explainer page exists and is linked from the nav.
  - [x] Key jargon terms have hoverable definitions inline (component reusable for more).

### TASK-017 — Mobile navigation + bottom tab bar
- **Why:** Mobile is the betting segment; nav is the first responsive gap.
- **Scope/what to build:** A responsive nav with a mobile bottom tab bar (Today,
  Edges, Matches, Track record, News) in the shared layout.
- **Files likely touched:** `site/src/layouts/Base.astro`, new
  `site/src/components/MobileNav.astro`.
- **Dependencies:** none (links to TASK-002/007 routes once they exist).
- **Effort:** S/M
- **Acceptance criteria:**
  - [ ] A usable bottom tab bar appears on mobile widths.

### TASK-018 — Affiliate-disclosure + jurisdiction policy page — ✅ SHIPPED 2026-06-06
- **Done:** new `/policy` page (`site/src/pages/policy.astro`) with full sections — **no
  affiliate/sportsbook relationship**, not advice, eligibility/jurisdiction (18+/local law),
  responsible gambling (BeGambleAware/GamCare/NCPG/GA), **data sources & attribution** (Odds
  API, martj42 results, RSS, FIFA), and a **privacy** note (no accounts/tracking; watchlist &
  picks are localStorage-only). Linked from the footer disclosure line.
- **Acceptance criteria:**
  - [x] A policy page covers affiliate disclosure, jurisdiction, age, "not advice".

---

## P2 — Later (depth, polish, model upgrades)

### TASK-019 — Live / results mode (poll results.json on matchdays) — ✅ SHIPPED 2026-06-06
- **Done:** `model/publish_live.py` emits a compact `site/public/data/live.json`
  (match_id → status + score for LIVE/FINISHED matches) from fixtures.json; a defensive
  client poller on the dashboard (`.md-row[data-match-id]`) fetches it every 60s and patches in
  **LIVE/FT scores without a rebuild** — full no-op when the file is empty (the pre-tournament
  state). Matchday loop (`fetch_results → publish_live → settle`) documented in the runbook.
  +2 tests (`build_live`).
- **Acceptance criteria:**
  - [x] On a matchday, scores/LIVE pill update client-side without a redeploy.

### TASK-020 — Price-cross alerting (scheduled poller) — ✅ SHIPPED 2026-06-06
- **Done:** `model/check_edges.py` — a pure local diff (no API) of the current edges vs the last
  snapshot (`edges_snapshot.json`), reporting edges that **APPEARED / GONE / MOVED ≥ Npp**.
  Run it after `predict.py` (`--dry-run` to preview, `--move` to set the move threshold). The
  dashboard also shows a **freshness badge** (TASK-029) when odds move after the model ran.
  +4 tests. Documented in the runbook.
- **Acceptance criteria:**
  - [x] Surfaces newly-appeared / disappeared / materially-moved edges since last run.
  - [x] Zero API calls (diffs the already-generated predictions).

### TASK-021 — Pre-commit SHA + timestamp of predictions (tamper-evident) — ✅ shipped 2026-06-06
- **Why:** Makes the audit un-cherry-pickable; OSS sharp models SHA-commit their
  pre-kickoff probabilities.
- **Status:** Done. `predict.py` now appends each run to an append-only ledger at
  `site/public/data/predictions_ledger.json` ({generated_at, sha256 of the file,
  content_sha256, n_predictions}). It **de-dups on a timestamp-free content hash**,
  so re-runs with identical picks don't bloat the ledger (the full-file sha256
  embeds the timestamp and would otherwise differ every run). The new
  `/methodology` page surfaces the latest hash + time, a recent-entries table (once
  >1 distinct set exists), and a "how to verify" (re-hash the live file); the footer
  links to it. `loadLedger()` + `LedgerEntry` added to `data.ts`.
- **Files touched:** `model/predict.py`, `site/public/data/predictions_ledger.json`
  (generated), `site/src/lib/data.ts`, `site/src/pages/methodology.astro`,
  `site/src/layouts/Base.astro`.
- **Acceptance criteria:**
  - [x] Each prediction run appends a hash + timestamp to an append-only ledger.
  - [x] The latest prediction hash + time is shown on the site.

### TASK-022 — Bet-log analytics split (source/market/edge-bucket/CLV) — ⚠️ partially shipped
- **Why:** Turns the log into a diagnostic: where does the edge actually come from?
- **Status:** P/L split **by source** (model vs manual) and **by market** already
  render on `bets.astro` (`splitPnl()` in `data.ts`). **Remaining scope only:** add
  breakdowns by **edge bucket** (e.g. 5-8% / 8-12% / 12%+) and **CLV bucket**, with
  ROI + avg CLV per bucket — the cut that tells you whether to raise the edge gate.
- **Files likely touched:** `site/src/lib/data.ts` (bucketing helper),
  `site/src/pages/bets.astro`.
- **Dependencies:** TASK-011 (CLV buckets need the CLV field — already present).
- **Effort:** S
- **Acceptance criteria:**
  - [ ] ROI + avg CLV breakdowns by edge bucket and CLV bucket render.

### TASK-023 — Mobile table-collapse for dense tables
- **Why:** The fixed `cols-3/cols-4` grids and odds/standings tables overflow on
  mobile; distinct from nav (TASK-017).
- **Scope/what to build:** Responsive card-collapse for the bookmaker-odds,
  standings, and edges tables at small widths.
- **Files likely touched:** `site/src/components/BookmakerOdds.astro`,
  `GroupCard.astro`, `site/src/pages/edges.astro`, shared CSS.
- **Dependencies:** none.
- **Effort:** M
- **Acceptance criteria:**
  - [ ] Dense tables collapse to readable cards on mobile widths.

### TASK-024 — Alt totals / DNB / double-chance / correct-score from the matrix — ✅ shipped 2026-06-06
- **Why:** Cheap extra markets the score matrix already supports; more engagement.
- **Status:** Done. `elo.derived_markets()` sums the existing Dixon-Coles score
  matrix into **double chance** (1X/12/X2), **Draw-No-Bet** (1X2 renormalised over
  decisive outcomes), and the **top-6 likeliest exact scores**. `predict.py` emits a
  `derived` block per prediction; a **"More markets"** section on the match page renders
  them (two `.table--cards` tables, mono scorelines). Display-only (no odds sourced, so
  no edges). Alt-*totals* skipped — the Asian-totals block (1.5/2.5/3.5) covers it.
- **Files touched:** `model/elo.py`, `model/predict.py`, `site/src/lib/data.ts`
  (`DerivedMarkets`), `site/src/pages/matches/[id].astro`, `tests/test_derived.py` (+5).
- **Acceptance criteria:**
  - [x] At least DNB + double-chance + top correct-scores render per match.

### TASK-025 — Per-team / per-group SEO landing pages — ✅ shipped 2026-06-06
- **Why:** Organic discovery via `/team/brazil`, `/group/a`; the content/SEO leg of
  the monetization stack.
- **Status:** Done. `team/[slug].astro` (48 pages) + `group/[id].astro` (12 pages)
  statically generated — hero, fixtures (`MatchCard`), value-edges table, group
  standings (current team highlighted), and team-filtered news. New `teamSlug()` +
  `teamGroups()` in `data.ts` (accents stripped, `&`→`and`); `Base.astro` gained a
  `description` prop + canonical/OG/Twitter meta. Internal linking: `GroupCard` team
  names → team pages, "Group X" → group pages (on /groups + dashboard + the new
  pages), breadcrumbs, team↔group cross-links. Build clean (**171 pages**, +60);
  verified in-browser incl. accented `curacao` / `bosnia-and-herzegovina` slugs.
- **Files touched:** `site/src/pages/team/[slug].astro`, `site/src/pages/group/[id].astro`,
  `site/src/lib/data.ts`, `site/src/layouts/Base.astro`, `site/src/components/GroupCard.astro`,
  `site/src/pages/groups.astro`, `site/src/pages/index.astro`.
- **Acceptance criteria:**
  - [x] Each team and group has a static, indexable landing page.
- **Follow-ups:** ✅ match pages now link team names → team pages (group-stage names
  only; knockout placeholders stay plain — `matches/[id].astro`, 2026-06-06).
  Still deferred: no XML sitemap yet (needs `site` in `astro.config` — set the deploy
  domain, then add `@astrojs/sitemap`); OG **images** still TASK-015.

### TASK-026 — Watchlist / favourite teams (localStorage v1) — ✅ shipped 2026-06-06
- **Why:** Retention without a backend.
- **Status:** Done. New `FollowButton.astro` (★ toggle, one-time init guard, shared
  `soccer26:following` localStorage key, emits a `watchlist:change` event) on each
  team page; the matches index "★ Following" filter reads the same key and reacts
  live. Verified cross-page: follow Brazil on its team page → matches filter shows
  Brazil's fixtures; persists across reloads.
- **Files touched:** new `site/src/components/FollowButton.astro`,
  `site/src/pages/team/[slug].astro`, `site/src/pages/matches/index.astro`.
- **Follow-up:** add the same "following" filter to `/edges` and the dashboard.
- **Acceptance criteria:**
  - [x] Favouriting a team persists across reloads and filters views.

### TASK-027 — Accessibility pass (prob-bar SR labels, colorblind redundancy) — ✅ already satisfied
- **Why:** Trust + reach; the prob bars convey meaning by colour alone.
- **Status:** On review, `ProbBar.astro` already meets the bar: it carries
  `role="img"` + a full `aria-label` ("Model: Home win X%, draw Y%, Away win Z%")
  AND a labeled legend (Home/Draw/Away with swatches + percentages) — so it is NOT
  colour-only, and segment text uses adequate-contrast light/dark fills. The
  `MatchCard` mini-bar is decorative (`aria-hidden`) with the probabilities shown as
  adjacent text. No change made.
- **Remaining (deferred, low priority):** the card mini-bar omits the *draw* % as
  text (only home/away shown); the front-end plan also notes touch-openable tooltips
  + a `?colorblind=1` pattern mode as nice-to-haves. See `docs/frontend-improvement-plan.md`.

### TASK-028 — Outright / group-winner Monte-Carlo simulation — ✅ shipped 2026-06-06
- **Why:** High engagement (tournament sims), even though it's high-vig and not an
  edge source.
- **Status:** Done. `model/simulate.py` Monte-Carlos the whole tournament —
  group round-robins (real fixtures, host advantage, sampled scorelines), the
  **8-best-thirds** qualification, the **official R32 third-place allocation** (a
  bipartite matching against the slot rules in `fixtures.json`, precomputed for all
  495 qualifying-group subsets), and the full knockout bracket. Fully **vectorised
  with NumPy** — 20k sims in ~1.1s. Goal sampling uses `lambdas()`, a vectorised
  mirror of `elo.expected_goals` (a test asserts they agree to 1e-9). Output:
  `site/public/data/simulation.json` (per team: win_group / qualify / r16 / qf / sf /
  final / champion). New `/outrights` page (champion leaderboard + full 48-team
  table, honest "model's opinion, not a tip" framing) + nav link; `loadSimulation()`
  in `data.ts`. **6 new pytest** (probability totals are exact: champion→1, qualify→32,
  win_group→12; stage monotonicity; seed determinism; lambdas-match-model).
- **Files touched:** new `model/simulate.py`, new `site/src/pages/outrights.astro`,
  `site/src/lib/data.ts`, `site/src/layouts/Base.astro` (nav), `tests/test_simulate.py`.
- **Acceptance criteria:**
  - [x] Advance / win-group / win-tournament probabilities are simulated and shown.
- **Notes:** tiebreaks approximate head-to-head with a random draw (negligible on
  aggregate outrights); paths respect the official third-place slot rules but the
  exact FIFA allocation table isn't transcribed (the matching is equivalent in
  intent). Re-run `python model/simulate.py` whenever ratings/fixtures change.

### TASK-029 — Staleness / freshness signals (odds & predictions vs kickoff) — ✅ SHIPPED 2026-06-06
- **Done:** uses the per-book `last_update` already in the odds data (no fetch_odds change
  needed). `data.ts` adds `latestBookUpdate(match)`, `oddsAsOf(matches)`, and
  `oddsMovedSincePredictions(generated_at, matches)`. The match page's Bookmaker-odds header
  shows **"as of <localised time>"**; the dashboard shows a freshness badge — **"✓ in sync with
  latest odds"** or **"⚠ odds moved since — refresh"** when a book quotes a price newer than the
  current prediction set (a build-time, kickoff-independent signal that the model should re-run).
- **Acceptance criteria:**
  - [x] Odds-capture time is shown; a stale prediction set (older than the odds) is flagged.

### TASK-030 — Consolidate team-name normalization to one alias table
- **Why:** Three separate name maps drift and silently drop unmatched odds events
  (improvements M2); a single new spelling loses a fixture's odds with no warning.
- **Scope/what to build:** One canonical alias table consumed by `elo.py`,
  `fetch_odds.py`, `parse_fixtures.py`, and `fetch_news.py`; make `fetch_odds.py`
  log every unmatched event instead of silently skipping. Fold in `check_names.py`.
- **Files likely touched:** new `model/team_aliases.py`, `model/elo.py`,
  `model/fetch_odds.py`, `model/parse_fixtures.py`, `model/check_names.py`.
- **Dependencies:** none.
- **Effort:** M
- **Acceptance criteria:**
  - [ ] All name mapping reads one table; unmatched odds events are logged loudly.

### TASK-031 — Offense/defense rating split (SPI-style λ)
- **Why:** The single biggest expressiveness gap vs 538/best practice; a single Elo
  can't separate a high-scoring leaky team from a low-event grinder, so OU/BTTS are
  weakly grounded.
- **Scope/what to build:** Add separate attack/defence ratings so `λ_home`/`λ_away`
  reflect each side's attack and the opponent's defence, instead of symmetric spread
  around a fixed baseline. Re-fit via `calibrate.py`/`backtest.py`.
- **Files likely touched:** `model/elo.py`, `model/train_ratings.py`,
  `model/backtest.py`, `model/calibrate.py`.
- **Dependencies:** none (uses existing calibration harness).
- **Effort:** L
- **Acceptance criteria:**
  - [ ] λ derive from attack/defence ratings; OU log-loss improves vs current.

### TASK-032 — Exponential time-decay weighting (ξ) — ❌ TESTED & REJECTED 2026-06-06
- **Why (original hypothesis):** A Jan-2020 friendly weighs the same as a 2026
  qualifier; Dixon-Coles-style decay should improve RPS.
- **Outcome:** Tested empirically (recency-weighted train objective, refit the
  1X2 constants, eval on held-out 2025 competitive matches). ξ **monotonically
  worsens** every metric: competitive log-loss 0.8421 → 0.8439 (ξ=0.4) → 0.8450
  (ξ=0.8); RPS and accuracy likewise degrade. **ξ=0 is optimal.**
- **Why it fails here:** Dixon-Coles ξ is for *static* models that weight all
  matches equally in one likelihood. soccer26's Elo is already **sequential /
  recency-aware** — old results are continuously overwritten by newer ones — so
  re-weighting the calibration objective on top just discards useful older signal
  and overfits recent dynamics, generalising worse. Not applicable to a sequential
  Elo. Left rejected; do not re-open without a fundamentally different mechanism.

### TASK-063 — Match-importance K-weighting — ✅ SHIPPED 2026-06-06
- **Why:** ~1,500 friendlies in the training set moved ratings as much as
  competitive results. Weight the rating update by match importance (eloratings.net
  style) so exhibitions stop polluting the ratings.
- **What shipped:** `match_importance(tournament)` in `model/elo.py` (friendly 0.5,
  minor cup 0.85, qualifier/Nations-League 1.0, continental final 1.4, World Cup
  1.75); `EloTable.update(..., importance=)` scales the per-match delta; threaded
  through `backtest.py` + `train_ratings.py`; base **K re-fit to 117.98** with
  weighting active (K bound widened to 200 in `calibrate.py`); ratings + anchors +
  predictions + sims regenerated.
- **Empirical result:** marginal **net-positive on competitive matches** (the WC's
  job): held-out accuracy 0.6244 → 0.6313, RPS 0.1657 → 0.1653, log-loss ~tied;
  cost falls only on *friendly* prediction (never forecast by the site). Train ECE
  improved 0.0089 → 0.0080.
- **Known side effect (accepted):** the **un-blended outright sims** become more
  market-contrarian (Spain ~20%→23.6%, Germany ~6%→1.9%, Brazil ~12%→5.9%, Norway
  ~2.5%→5%) because importance emphasises competitive results (Spain/England up for
  winning real matches; Brazil/Belgium down for poor qualifying) and outrights have
  no per-match odds to blend against. Per-match *published* edges barely move — the
  market blend absorbs the rating change (median model-vs-market |gap| 0.036). Owner
  chose to ship the competitive-weighted view. Revisit by blending outrights to a
  futures market post-tournament.

### TASK-064 — Extend market blend to O/U & BTTS — ➖ ALREADY SHIPPED / MOOT 2026-06-06
- **Finding:** O/U 2.5 is **already** in the blend (`_BLENDABLE` in `predict.py`,
  linear probability scale). BTTS **cannot** be blended — the Odds API World Cup
  endpoint rejects the `btts` market (see `fetch_odds.py`), so there is no market to
  anchor against; model BTTS stays display-only (honest). Logit-scale blending for
  the binary O/U market ≈ linear because WC totals cluster near 50%, so the change is
  negligible. Nothing to build.

### TASK-033 — In-tournament rating updates + knockout re-prediction (H6)
- **Why:** Over a month-long event, frozen ratings make later-round predictions
  ignore everything that just happened.
- **Scope/what to build:** Mark finished 2026 matches, update ratings as group
  games finish, and re-predict downstream knockout edges. Requires placeholder→team
  resolution as the bracket fills.
- **Files likely touched:** `model/elo.py`, `model/train_ratings.py`,
  `model/predict.py`, `model/parse_fixtures.py`.
- **Dependencies:** ✅ results pipeline (`fetch_results.py`/`settle.py` shipped).
- **Effort:** M/L
- **Acceptance criteria:**
  - [ ] Finishing group games update ratings and refresh knockout predictions.

### TASK-034 — Fit the totals-model shape coefficients — ✅ DONE 2026-06-06 (via TASK-048)
- **Done as part of TASK-048:** `calibrate.py` now fits `GOALS_BASELINE` +
  `GOALS_STRENGTH_COEF` + `GOALS_MISMATCH_COEF` to an **O/U-2.5 log-loss objective**
  (`fit_totals` / `--totals-only`, `TOTALS_NAMES`), loaded from `calibration.json`.
  Walk-forward O/U log-loss improved 0.6946→0.6873 (and 1X2 ll too). The strength coef
  fitted to ~0 (the over-bias fix). See TASK-048 for the full write-up.

### TASK-035 — Context-aware home advantage (host + altitude)
- **Why:** A flat 65/97 Elo HFA ignores that USA/Canada/Mexico and altitude venues
  (Mexico City, Guadalajara) differ materially.
- **Scope/what to build:** Replace the single HFA with a small per-host /
  altitude-adjusted table; derive host status from fixtures/groups data rather than
  the hardcoded `VENUE_COUNTRY` string-match (also fixes improvements L4).
- **Files likely touched:** `model/predict.py`, `model/elo.py`.
- **Dependencies:** none.
- **Effort:** M
- **Acceptance criteria:**
  - [ ] HFA varies by host/altitude; host status no longer string-matched on venue.

### TASK-036 — Backtest across prior tournaments/qualifiers (out-of-sample edge)
- **Why:** 104 WC matches are too few to establish edge; need an OOS RPS/log-loss +
  (where odds exist) CLV baseline before the Cup.
- **Scope/what to build:** Extend `backtest.py` to evaluate prior tournaments/
  qualifier windows and, against historical closing odds (football-data.co.uk-style),
  a CLV baseline.
- **Files likely touched:** `model/backtest.py`, `model/data/`.
- **Dependencies:** none.
- **Effort:** M
- **Acceptance criteria:**
  - [ ] OOS metrics across prior windows are reported; CLV baseline where odds exist.

### TASK-037 — Structured injuries enrichment (API-Football v2)
- **Why:** A higher-confidence, separate injuries/suspensions block beyond the RSS
  headlines (news-feed research Phase v2).
- **Scope/what to build:** Add `APIFOOTBALL_KEY` support and pull
  `/injuries?league=1&season=2026` (coverage-checked), map team→country via the
  alias table, write an `injuries[]` block; render distinctly from headlines.
- **Files likely touched:** `model/fetch_news.py` (or new `fetch_injuries.py`),
  `site/src/components/NewsItem.astro`, `site/src/pages/matches/[id].astro`,
  `.env.example`.
- **Dependencies:** TASK-030 (alias table).
- **Effort:** M
- **Acceptance criteria:**
  - [ ] A distinct, coverage-gated injuries block renders per team/match.
- **Note (2026-06-06):** keep this as **display/context only** — see TASK-065.

### TASK-065 — Player form ("hotness") + injuries as a MODEL input — ❌ RESEARCHED & DECLINED 2026-06-06
- **Question (owner):** Can recent individual player form + injuries feed the
  forecast (e.g. a hot Germany player nudges Germany up; injuries nudge down)?
- **Verdict:** **Do not feed it into the model. Keep injuries/squads as on-page
  context (already shipped: injury-tagged news, matchday injury pill, squad rosters).**
- **Why (research summary):**
  1. **Redundant with the blend.** The published forecast is already pulled toward
     the de-vigged market, which prices lineups/injuries/form within minutes — faster
     and more completely than we could. A player layer would mostly help us *match* a
     market we're already anchored to, not *beat* it. The blend (TASK-046/047) is the
     project's answer to "the market sees squad quality we can't"; this re-solves it.
  2. **Coverage is backwards.** Free form/injury data is abundant for big nations
     (which the market already nails) and **blank for CAF/AFC/OFC/CONCACAF minnows**
     (where a team model is our only edge). ESPN's WC injury tracker is explicitly
     star/big-nation only; no free source covers all 48 teams' players.
  3. **Biggest risk:** a wrong/stale flag on a thin-data minnow (one player = a huge
     share of a fragile rating) swings the prediction hard the wrong way — *adding
     variance where we have least information* — and if it ever touched the blended
     forecast it would manufacture phantom edges on the sharpest games and pollute CLV.
- **Only defensible modeled version (post-tournament, optional):** a small, capped
  "key-player **confirmed ruled out**" penalty applied to the **raw `probabilities`
  / knockout+outright sims only** (never the blended `forecast`/edges) — and only
  after the CLV ledger exists to measure whether it does anything. Not worth it now.

### TASK-066 — "Road to the World Cup": warm-up form + pre-match model calls — ✅ SHIPPED 2026-06-06
- **Why:** Show each team's recent international form AND — the on-brand part — what
  the model *predicted* for each game, walk-forward (no hindsight), as an honest
  pre-kickoff track record. The "show form/results as context, don't model it" path
  that TASK-065 endorsed, plus a free, public model-vs-reality demonstration.
- **What shipped:**
  - `model/build_form.py` → `site/public/data/form.json`: per-team last-6 internationals
    (W/D/L + scores, competition, ×½ friendly weight) **and** a walk-forward 1X2
    prediction per game (`_model_view`: pick + correct + prob of the actual result),
    a per-team `record`, and a deduped run-in **feed** (`recent_feed`, since 2026-05-01)
    with home-perspective calls + an aggregate record.
  - Team pages: a "Road to the World Cup" form strip (`TeamForm.astro`) with per-game
    `model ✓/✗ N%` chips + a `model called X/6` badge.
  - **New page `/road-to-the-world-cup`** (nav: "Road to WC"): headline record
    (26/38 = 68% on the run-in), the full run-in feed (model call vs reality, hits AND
    misses), and a "how every team is arriving" form table. Owner chose **full
    transparency** (show the misses).
  - `/methodology#ratings` documents the match-importance half-weight rule (now that the
    ×½ badges expose it). +6 `test_form.py` tests.
- **Freshness:** `form.json` is current through the committed `internationals.csv`
  (June 4). A June-10 refresh is scheduled (one-shot reminder caacaa32, **session-only
  — unreliable across 4 days**; a GitHub Action is the robust alternative if wanted).
  `build_form.py` reads the historical CSV, which the matchday-poll does NOT refresh.

### TASK-038 — Model uncertainty / confidence indicator
- **Why:** Point probabilities hide that minor-nation ratings rest on tiny samples
  (improvements L5).
- **Scope/what to build:** Surface a coarse confidence signal (rating sample size /
  recent caps) flagging low-confidence predictions; optionally widen Kelly caution.
- **Files likely touched:** `model/predict.py`, `site/src/pages/matches/[id].astro`.
- **Dependencies:** none.
- **Effort:** M
- **Acceptance criteria:**
  - [ ] Low-sample teams' predictions show a confidence flag.

### TASK-044 — Power-method de-vig (favourite-longshot correction) — ✅ shipped 2026-06-06
- **Why:** Quant-panel item. The old proportional ("multiplicative") de-vig splits the
  bookmaker margin evenly across outcomes, which — given the favourite-longshot bias
  (books load relatively more margin on longshots) — **overstates the market's fair
  probability for longshots and understates it for favourites**. That skews the
  fair baseline every edge is measured against.
- **Status:** Done. `devig_market()` now takes a `method` arg and defaults to
  `DEVIG_METHOD = "power"`: fit one exponent k (bisection) so `sum((1/odds)^k) == 1`.
  Because each implied prob < 1, k>1 shrinks longshot probs more than favourites' —
  the standard favourite-longshot correction, the parameter-free cousin of Shin.
  `"multiplicative"` is kept for comparison/tests. Each surfaced edge records
  `devig_method`. Methodology page + glossary updated to describe it.
- **Effect on our book (modest WC margins):** edges 123→126, the shift concentrated in
  **draws** (21→23, the 1X2 longshot) — multiplicative had been masking genuine
  model-vs-market draw disagreements by inflating the market's fair draw prob. Favourite
  (home) edges ~flat. This is a more accurate baseline, not an edge cull.
- **Files touched:** `model/predict.py`, `tests/test_model.py` (+4 tests),
  `site/src/pages/methodology.astro`. Regenerated predictions; hash chain re-verified.
- **Acceptance criteria:**
  - [x] Fair baseline uses power de-vig by default; multiplicative still available.
  - [x] Tests prove sum-to-1 + longshot-shrink direction; full suite green (103).
- **Follow-on (not done):** Shin's z-model proper (insider-trade proportion) — power is
  the agreed good-enough default; revisit only if calibration says otherwise.

### TASK-045 — Markets-vs-model divergence tracker (`/divergence`) — ✅ shipped 2026-06-06
- **Why:** The "unique feature" from the competitive panel — a single page answering
  "where does the model most disagree with the market?", in BOTH directions (not just
  the value side the edges page shows). A transparency/insight surface, distinct from the
  actionable edges list.
- **Status:** Done. `predict.find_divergences()` emits every priced outcome's **signed**
  model−fair gap (no threshold, both signs; same power-de-vigged baseline as edges) into a
  `divergences` block. `data.ts.topDivergences()` collapses each match-market to its
  largest-|Δ| outcome (the 1X2 legs are complementary — one disagreement, not three) and
  sorts by |Δ|. New `/divergence` page (PageHero violet) with a summary strip
  (priced markets · model>market · market>model · biggest gap), direction + market filter
  chips, and a ranked table linking to match pages. Added to the top nav after Edges.
- **Honesty framing:** copy states large gaps can be edges OR model blind spots — and the
  current top gaps are big NEGATIVE ones (model rating favourites well below the market,
  e.g. Belgium–Iran model 34% vs market 70%), which reads as a model-conservatism signal
  worth watching, not 144 value bets. Same odds data as the edges page, so consistent.
- **Files touched:** `model/predict.py`, `tests/test_model.py` (+4 tests),
  `site/src/lib/data.ts` (`Divergence`/`DivergenceRow`/`topDivergences`),
  `site/src/pages/divergence.astro` (new), `site/src/layouts/Base.astro` (nav).
- **Acceptance criteria:**
  - [x] One page ranks all priced matches by model-vs-market gap, both directions.
  - [x] Collapses redundant complementary legs; filterable by direction + market.
- **Follow-on:** once the model-side issue (big favourite under-rating) is understood,
  this page is also the natural QA surface for it; could later flag |Δ|>threshold rows
  as "review the model" vs "potential value".

### TASK-047 — Tune the blend → confidence-weighted (disagreement-aware) + found the O/U bias — ✅ shipped 2026-06-06
- **Why:** Tune the TASK-046 blend weight. Measuring first was decisive: the model disagrees
  with the 29-book market by a **median 15 pts**, and the BIGGEST disagreements ARE the broken
  confederation-skew games. So a **flat weight can't work** — any weight high enough to keep
  the model meaningful re-surfaces exactly the broken cases (at flat 0.5, Belgium–Iran still
  leaked Iran/away +13%).
- **Fix:** made the blend **disagreement-aware** — per market group,
  `w = BASE / (1 + (D/HALF)^2)` where `D = max|model − market|` in that group;
  `MARKET_BLEND_BASE_WEIGHT = 0.6`, `BLEND_DISAGREEMENT_HALF = 0.17` (chosen by sweeping the
  real 72-match data). The model is trusted ~0.6 when it agrees and collapses toward 0 as it
  strays — so structural-error gaps defer to the market while moderate disagreements survive.
  The per-match effective 1X2 weight is stored on `forecast.weight` and shown in the
  "Model vs market" panel caption ("11% model + 89% market here" for Belgium–Iran).
- **Effect:** edges **75 → 12**; zero fake DRAW/AWAY longshots; all 12 biggest-disagreement
  matches now produce no edge; Belgium–Iran trusts the model **11%** (forecast 66%, no edge).
  Per-match 1X2 weights range 0.11–0.60 (median 0.34).
- **Files touched:** `model/predict.py` (`_group_weight`, rewrote `blend_forecast` → returns
  `w_1x2`; consts renamed), `tests/test_model.py` (rewrote blend tests, +confidence tests),
  `methodology.astro` + `matches/[id].astro` (copy: "confidence-weighted", per-match share).
- **Acceptance criteria:**
  - [x] Blend weight shrinks with disagreement; egregious cross-confed cases surface no edge.
  - [x] Per-match trust is published + shown; suite green (118).

### TASK-048 — Totals model ran systematically HOT vs market — ✅ FIXED 2026-06-06 (source recalibration)
- **Found via TASK-047:** with the 1X2 skew fixed, surviving edges were almost all OVER even
  on matches where 1X2 agreed with the market. `model P(over2.5) − market` was +0.057 mean /
  +0.074 median, positive in 78% — a **systematic offset** a blend can't remove.
- **Root cause (diagnosed, not guessed):** the totals **shape coefficients were hand-set and
  fit BLIND** — `GOALS_BASELINE` rode the 1X2 log-loss objective (which barely constrains
  totals) and `GOALS_STRENGTH_COEF`/`GOALS_MISMATCH_COEF` were never fitted at all. Measured:
  on full mixed-strength history, `GOALS_BASELINE=2.898` calibrates (model over-rate 0.479 vs
  realised 0.490); but the **positive** strength coef (+0.0011) inflated totals on the strong
  WC field, so the WC over-rate ran 0.553 while the market (0.496) matched realised history.
- **Fix:** made the totals params fittable to an **O/U-2.5 log-loss objective** (separate from
  the 1X2 fit) in `calibrate.py` (`fit_totals`, `--totals-only`, `TOTALS_NAMES`), loadable from
  `calibration.json` via `elo.py`. Refit (1X2 constants held): `GOALS_BASELINE 2.898→2.591`,
  `GOALS_STRENGTH_COEF +0.0011→~0` (strong pairs do NOT score more total goals — strength
  predicts the WINNER, not the goal count), `GOALS_MISMATCH_COEF 0.0008→0.0015`. Improves
  walk-forward O/U log-loss (0.6946→0.6873) **and** 1X2 log-loss.
- **Effect:** WC model over-rate **0.553 → 0.478** (market 0.496, realised 0.490 — within 2pts).
  O/U edges flipped from a one-sided 6-OVER/1-UNDER artifact to a balanced 1-OVER/5-UNDER;
  total edges 12 → 10. The systematic bias is gone — O/U edges now reflect genuine
  match-specific disagreement.
- **Files touched:** `model/elo.py` (load coefs from calibration, TUNABLE), `model/calibrate.py`
  (split objectives, `fit_totals`, `--totals-only`), `model/data/calibration.json` (refit),
  `tests/test_model.py` (corrected the now-wrong "strong pairs score more" test → independence;
  + totals-level characterisation guard). 119 tests green; hash chain re-verified.
- **Acceptance criteria:**
  - [x] Totals fit to an O/U objective; WC over-rate ≈ realised/market; O/U edges no longer one-sided.

---

## Expert-panel findings (2026-06-06) — fleet review, triaged into tasks below

A 5-agent read-only review (market/growth, quant, code, security, test-automation) ran on the
post-blend codebase. The highest-value items became TASK-049…056 below. Full agent reports are
summarised in the session handoff. **The recurring #1 across market + quant: the audited CLV
record is the entire moat and is still EMPTY — closing-odds capture must start on the June 11
openers or the first-week data is permanently lost.**

### TASK-049 — Stored-XSS hardening: allowlist news URL schemes — ✅ FIXED 2026-06-06
- Security audit HIGH. **Fixed** in depth: `fetch_news._norm_url` now rejects any non-http(s)
  scheme (returns "" → the item is dropped at ingestion), AND the render layer guards
  defensively — `NewsItem.astro` and `feed.xml.ts` only emit an href when `^https?:` matches
  (else `#` / site root). Closes the `javascript:`/`data:` one-click XSS path both at source
  and at the sink.

### TASK-050 — Tamper-evidence claim overstates the guarantee — ✅ FIXED 2026-06-06
- Security audit (the moat): `/methodology` overstated the guarantee. **Fixed both ways:**
  (a) `predict.py` now writes a real **prev-hash chain** — every ledger entry carries `prev` =
  SHA-256 of the previous entry (`ledger_entry_hash`, `GENESIS_HASH`), so altering any historical
  entry breaks every entry after it. Backfilled the existing 8 entries; live file ↔ ledger ↔
  sidecar still consistent; idempotency intact. (b) Methodology copy rewritten to be **honest**:
  describes the chain, drops "can't be changed," and adds a "what this does/doesn't prove" note —
  it's self-published, so a fully independent guarantee needs an external anchor (flagged as
  roadmap). Verify-steps now include checking the chain. +3 tests (chain links / detects tamper /
  order-independent hash). **Follow-on (open):** external anchoring (public git remote /
  OpenTimestamps) for a third-party-notarised guarantee.

### TASK-051 — Rotate the exposed ODDS_API_KEY — ✅ ROTATED (owner) + REPO VERIFIED CLEAN 2026-06-06
- Owner rotated the key in the the-odds-api.com dashboard (the original value is now dead).
- **Repo audited and confirmed clean (2026-06-06):** the key value appears in **no tracked file**
  and in **no commit across the full git history (all refs)**; `.env` was **never committed**; the
  fetch scripts keep the key in the request `params` (never in the printed URL/logs); the
  `.claude` memory files are clean. So the public repo is **not** a leak source — rotation holds.
- If GitHub secret-scanning still shows an alert, it is the **pre-rotation** alert and can be
  **dismissed** (Security → Secret scanning) — GitHub never received the key via a commit, so there
  is nothing in the repo to purge. `.env.example` documents the expected env with no secret.

### TASK-052 — Dashboard cards showed RAW model probs (blend inconsistency) — ✅ FIXED 2026-06-06
- Code review (C1, Critical): `MatchCard.astro` + the match OG card used `pred.probabilities`
  (raw skewed Elo) while match pages used the blend — so "Next up" cards showed Belgium 34%, and
  the lean indicator could point at the wrong team. **Fixed:** both now use `publishedProbs()`.

### TASK-053 — settle.py can grade a LIVE match as final — ✅ FIXED 2026-06-06
- Code review H4. **Fixed:** `match_is_final` now requires a complete score AND
  `status not in ("LIVE","SCHEDULED")` — a half-played LIVE score can no longer settle bets
  into the source-of-truth log. Regression test added (`test_live_match_with_score_is_not_graded`).

### TASK-057 — Closing-odds capture cadence (the #1 ops blocker) — ✅ TOOLING SHIPPED 2026-06-06
- **The standing #1 blocker:** the audited CLV record (the moat) is empty until closing odds
  are captured on real matchdays — and it can't be backfilled. `fetch_odds.py --closing` existed
  but had no schedulable, quota-safe cadence (free tier ≈ 500 req/month).
- **Shipped:** `model/capture_closing.py` — a quota-aware wrapper that spends an API request
  ONLY when a SCHEDULED match is within `--within-hours` of kickoff and not captured within
  `--min-refresh-mins` (else exits without calling). Pure decision logic (`capture_plan`) with
  `--plan`/`--dry-run` modes; `scripts/capture-closing.ps1` + a Windows Task Scheduler `schtasks`
  one-liner for hourly set-and-forget; `docs/closing-odds-runbook.md` runbook. +8 tests.
- **Remaining (owner action):** actually register the hourly task (or run manually) so capture
  starts on the **June 11 openers**. Verified safe: `--dry-run` today returns "no API call".

### TASK-058 — Set `site` + sitemap + absolute OG/canonical (SEO/social unblock) — ✅ SHIPPED 2026-06-06
- Market panel's cheap #1 unblock: `astro.config.mjs` had no `site`, so every OG card, RSS link,
  canonical, and (absent) sitemap had broken/relative URLs → zero indexability.
- **Shipped:** `astro.config.mjs` sets `site` from `SITE_URL` env (placeholder default +
  build-time warning so it can't ship unnoticed); added `@astrojs/sitemap` (emits
  `sitemap-index.xml`); `Base.astro` canonical + `og:url` now absolute; dynamic `robots.txt.ts`
  advertises the sitemap. **Owner action:** set `SITE_URL=https://<domain>` once a domain exists
  (one env var / one line) — everything upgrades automatically.

### TASK-054 — CLV de-vig docstring/copy says "multiplicative", code uses power — ✅ FIXED 2026-06-06
- Code + quant review (A4/H2): `clv.py` docstring + line-150 comment said proportional/multiplicative
  but `compute_clv` uses the power default. **Fixed:** both now say "power method (same default as
  predict.py)". Confirmed the site copy (`/methodology`) had no stale "multiplicative" CLV claim.

### TASK-055 — Typed/validated data loaders + first JS/TS tests — ✅ SHIPPED 2026-06-06 (folds in TASK-039)
- **Done:** added **Vitest** (`npm --prefix site run test`) and the project's first JS/TS suite —
  `site/src/lib/data.test.ts`, **19 tests** over the logic-heavy spine: Kelly (`fullKellyFraction`/
  `kellyStake` + cap), `meanCI`, formatting (`signed`/`money`/`pct1`, real − glyph), `teamSlug`
  (accents/&), `matchOutcome`, `computeStandings`, `topDivergences`, `liveCalibration`, the loader
  validators, and a smoke test that the real artifacts load. **Hardened `readJson`:** missing file
  → fallback, **corrupt JSON → throws**, optional shape **validator** → throws with the filename.
  Added exported `validateFixtures`/`validateBets`/`validatePredictions` (id/probabilities/numeric
  stake checks) wired into the three core loaders, so a malformed artifact fails the build loudly
  instead of rendering wrong numbers. This is the old TASK-039.

### TASK-056 — Test the hash-chain/idempotency + Python↔TS golden cross-check + CI gate — ✅ SHIPPED 2026-06-06
- **Done, all three parts:** (a) `tests/test_predict_main.py` runs the real `predict.main()` against
  a temp fixture/ratings set (paths monkeypatched) and asserts **file-bytes-hash == sidecar ==
  ledger[-1]**, the ledger is a **valid prev-hash chain**, **no CRLF** in the written bytes, and a
  no-op re-run **rewrites nothing / doesn't grow the ledger** (4 tests). (b) A **golden cross-check**:
  `tests/golden/staking_clv_golden.json` is a shared contract asserted by BOTH `tests/test_golden.py`
  (Python `staking.kelly_stake` / `clv.mean_ci`) and `site/src/lib/data.golden.test.ts` (TS
  `kellyStake` / `meanCI`) — so the duplicated Kelly/t-table math can't silently drift. (c)
  `scripts/check.ps1` — one-command gate running **pytest → vitest → astro build**, non-zero on first
  failure. Verified green: **pytest 148, vitest 26, build 176 pages.**

### TASK-059 — Confederation anchoring at the ratings source — ✅ SHIPPED 2026-06-06
- **The durable fix** for the cross-confederation Elo skew (the market blend only patched priced
  group games; the knockout/outright sims still ran on the raw skewed ratings — quant A7).
- **Done:** `model/anchor.py` fits ONE Elo offset per confederation against the de-vigged market on
  the 63 neutral priced games (regress `market_gap − model_gap` on the home−away confederation
  indicators, UEFA reference), then **re-centres to mean-zero** across the 48-team field so the
  totals strength term is undisturbed. Fitted: **UEFA +95, CONMEBOL +79, OFC +78 (noisy, 1 team);
  CAF −58, AFC −91, CONCACAF −113**. Stored in `model/data/confederation_offsets.json` (+ the 48-team
  `confederations.json`). `apply_offsets()` (canonical-name-aware, so USA/Bosnia are adjusted) is
  called in **both** `predict.py` and `simulate.py`, so the correction reaches per-match AND the sims.
- **Effect:** model-vs-market disagreement **halved** (median 0.153 → 0.076); ratings now sane
  (Germany 1882→1977 **above** Iran 1936→1845; Brazil **above** Morocco; Mexico below Croatia);
  edges 10→7; **outrights now sane** — Spain 17% / France 11% / Argentina–Brazil 10%, Morocco out
  of the top. The blend now does far less work (Belgium–Iran raw model 34%→54%). +6 tests.
- **Files:** `model/anchor.py` (new), `confederations.json`/`confederation_offsets.json` (new),
  `predict.py` + `simulate.py` (apply), `tests/test_anchor.py`; methodology/divergence/outrights copy.
- **Follow-on:** OFC (New Zealand only) is poorly constrained; refit when more data exists. A longer
  term option is anchoring to an external rating (SPI/eloratings) instead of the market.

### TASK-060 — Quant transparency: raw gap + staked edge, and CLV reporting — ✅ SHIPPED 2026-06-06
- **A1 (raw gap vs staked edge):** `find_edges` now records `model_raw_prob` + `raw_edge_pct` (the
  pre-blend anchored-model gap) on every edge, so the green **staked** edge no longer hides that
  `edge = trust × raw gap`. The edges page shows a "raw +W%" annotation (with the trust factor in
  the tooltip), the match-page edges table shows the raw model prob + raw gap, and the callout
  states the relationship. Visible payoff: staked edges cluster ~5% while raw gaps are 15–19%. +1 test.
- **A3 (CLV reporting):** added `wilsonInterval()` (binomial 95% CI for a proportion) and a
  **stake-weighted** avg CLV to `clvStats`. The bets page now **leads with the beat-rate + its
  Wilson CI** (the cleaner small-sample skill signal) and shows avg CLV stake-weighted, with the
  fragile per-bet mean t-interval demoted and a note explaining why. +3 tests. Full gate green
  (pytest 155, vitest 29).

### TASK-031 — Attack/defence (SPI-style) rating split — ⏳ DEFERRED (HIGH impact / L effort)
- The real fix for totals/BTTS expressiveness (a single Elo can't separate a high-event leaky side
  from a low-event grinder). **Deferred deliberately:** it's a full rating-model rewrite
  (`train_ratings.py`, `elo.py expected_goals`, re-fit ALL calibration constants, re-validate) — too
  large and destabilising to land safely ~5 days before kickoff, when the confederation anchoring +
  totals recalibration + blend already produce sane outputs. Best done after the tournament (or in a
  carefully-validated branch). Until then the totals model is recentred + O/U-fitted, which covers
  the level; the split would improve the per-match *shape*.

### TASK-046 — Market-blend prior (fixes the ratings mis-scaling the divergence tracker exposed) — ✅ shipped 2026-06-06
- **NOTE:** the flat `MARKET_BLEND_MODEL_WEIGHT = 0.5` described below was **superseded the
  same day by TASK-047's confidence-weighted blend** (`MARKET_BLEND_BASE_WEIGHT = 0.6` +
  disagreement shrink). The architecture (pure `probabilities` vs published `forecast`/`market`,
  edges + archive off the blend) is unchanged; only the weight became adaptive.
- **Root cause found (via TASK-045):** the divergence tracker surfaced the model rating
  favourites 30+ pts below a 29-book market on cross-confederation games (Belgium 34% vs
  market 70% to beat Iran). Investigation ruled out every mechanical cause — data is clean
  (6,015 matches since 2020, all teams covered 67–91 each), future WC rows have NaN scores
  and are dropped, names all join, and the skew is **K-invariant** (retrained at K=32→101,
  the ordering Iran/Morocco/Ivory Coast > Germany/Belgium/Netherlands never flips; K only
  scales the spread). It's the **structural Elo limitation**: inter-confederation isolation
  (CAF/AFC rarely play UEFA, so the pools aren't anchored to each other) + genuine recent
  Euro underperformance, and Elo can't see squad value. The market can. **Not a bug.**
- **Fix (user-chosen):** a **market-blend prior**. `predict.blend_forecast()` shrinks the
  pure-model 1X2 + O/U toward the de-vigged (power) market: `forecast = w·model + (1−w)·fair`,
  `MARKET_BLEND_MODEL_WEIGHT = 0.5`. Pure `probabilities` stays the raw instrument reading
  (drives score-shape markets + knockout/outright sims, which have no odds to blend); a new
  `forecast` + `market` snapshot are emitted per prediction. **Edges** are now measured off
  the blend (`find_edges(forecast, …)`) and the **calibration archive** stores the blend, so
  structural model errors no longer masquerade as value.
- **Effect:** edges **126 → 75** (inflated longshot draws 23→10; max edge ~15%). Belgium
  home 34% → published **52%**. **Honest caveat:** at w=0.5 the most extreme mismatches still
  leak a residual edge (Belgium–Iran still shows Iran/away +13%, since half of a 26-pt gap
  clears the 5% threshold) — lowering `MARKET_BLEND_MODEL_WEIGHT` toward ~0.35 would shrink
  those further. Knockout rounds (no odds) remain pure model — a known limitation.
- **Files touched:** `model/predict.py` (`blend_forecast`/`market_snapshot` + wiring +
  archive), `tests/test_model.py` (+5), `site/src/lib/data.ts` (`market`/`forecast` types +
  `publishedProbs`), `site/src/pages/matches/[id].astro` ("Model vs market" panel + blended
  headline), `edges.astro` (callout + "Our call" column), `divergence.astro` (raw-gap note),
  `methodology.astro` (blend section + glossary). Regenerated; hash chain re-verified.
- **Acceptance criteria:**
  - [x] Published forecast + edges + calibration use the market-blended probability.
  - [x] Raw model still visible (Model-vs-market panel + divergence page); sims unaffected.
- **Follow-on (open):** (1) tune `MARKET_BLEND_MODEL_WEIGHT` (0.35–0.5) once there's CLV
  data to optimise against; (2) the deeper fix — confederation/external-rating anchoring at
  the source — would also help the knockout sims the blend can't reach (see TASK-045 option B).

### TASK-039 — Typed, schema-validated site data loaders — ✅ DONE 2026-06-06 (folded into TASK-055)
- Done via TASK-055: `readJson` now throws on corrupt JSON, and `loadFixtures/loadBets/
  loadPredictions` run exported shape validators that fail the build loudly (with the filename)
  on malformed data. Hand-written guards rather than zod (dependency-light); covered by Vitest.
- **Acceptance criteria:**
  - [x] Build fails on malformed bet/prediction JSON with a clear error.

### TASK-040 — Reproducibility pinning + data provenance
- **Why:** `requirements.txt` uses `>=` ranges and the training CSV is gitignored
  with only a prose pointer, so `ratings.json` isn't reproducible (improvements L6).
- **Scope/what to build:** Pin exact versions, add a lock file, and record the
  dataset snapshot/date used to train.
- **Files likely touched:** `model/requirements.txt`, `model/data/`, `README.md`.
- **Dependencies:** none.
- **Effort:** S
- **Acceptance criteria:**
  - [ ] Pinned deps + a recorded dataset snapshot make ratings reproducible.

### TASK-041 — "Beat the Model" prediction game — ✅ shipped 2026-06-06
- **Why:** The strongest no-licence **retention loop** (expert panel §5 / growth #2):
  a free-to-play forecasting game that manufactures the "you vs the model" narrative.
- **Status:** Done. `/predict` lets a visitor pick the 12 group winners + a champion
  (saved to `soccer26:picks` localStorage); the model's picks are shown (group winner =
  max `win_group` from `simulation.json`; champion = top title prob) and both are
  scored as results land — 3 pts per correct group winner, 10 for the champion. Model
  score is server-rendered (deterministic), the user score is computed client-side;
  empty-state-safe (0–0 until the tournament starts 11 Jun). Nav link "Predict".
- **Files touched:** new `site/src/pages/predict.astro`, `site/src/layouts/Base.astro`.
- **Follow-ups (panel):** extend to a full knockout bracket pick; per-matchday email of
  standings (needs the newsletter wired); true cross-user leaderboard would need a backend.
- **Acceptance criteria:**
  - [x] Visitors pick group winners + champion; picks persist; scored vs the model.

### TASK-042 — Post-match "we said X → result Y" card (prediction vs outcome) — ✅ shipped 2026-06-06
- **Why:** Closes the feedback loop (expert panel UX#10 / competitive #10): the single
  strongest repeat-trust moment.
- **Status:** Done. On a FINISHED match, `matches/[id].astro` shows a card with a
  **correct/missed** verdict, the score + outcome, the model's pre-kickoff top pick and
  the probability it gave the actual result, the full 1X2 breakdown (actual highlighted),
  and any settled bets (WIN/LOSS + P/L). Uses the **pre-kickoff prediction archive** (see
  the note in TASK-043 — `predictions.json` drops finished matches, so the archive
  preserves the locked prediction). Verified by injecting a 2–0 result (rendered "Top
  pick ✓ correct · Mexico win 78.3%") then reverting. Empty-state-safe (no card until a
  match finishes).
- **Files touched:** `site/src/pages/matches/[id].astro`, `site/src/lib/data.ts`
  (`matchOutcome`, `loadPredictionArchive`), `model/predict.py` (archive write).
- **Acceptance criteria:**
  - [x] Finished matches show predicted-vs-actual with a correct/incorrect verdict.

### TASK-043 — Living post-match calibration scorecard (matchday-updated) — ✅ shipped 2026-06-06 (folds in TASK-010)
- **Why:** Panel-convergent (UX + competitive #1): the cheapest unmatched credibility
  differentiator.
- **Status:** Done. A **"Tournament 2026 — live"** section on `/calibration` scores the
  model's **frozen pre-kickoff** 1X2 predictions vs actual 2026 results: matches graded,
  top-pick hit rate, live Brier, and a one-vs-rest reliability table (predicted band vs
  observed frequency). Computed build-time by `liveCalibration()` in `data.ts` from the
  prediction archive + fixtures scores — no new pipeline step. Verified populated (1
  match → correct bins/Brier) then reverted; empty-state-safe.
- **Key infra — prediction archive:** `predict.py` now also writes an append-only
  `site/public/data/predictions_archive.json` (match_id → frozen pre-kickoff 1X2 +
  `locked_at`). It refreshes each *scheduled* match's entry every run and never touches
  finished matches, so a match's last pre-kickoff prediction is preserved after kickoff
  (predictions.json only ever holds scheduled matches). This unblocks both TASK-042/043.
- **Files touched:** `model/predict.py`, `site/src/lib/data.ts`, `site/src/pages/calibration.astro`.
- **Dependencies:** ✅ settlement pipeline; the CLV side still wants the **closing-odds
  capture cadence** (the standing #1 ops blocker).
- **Acceptance criteria:**
  - [x] Tournament-to-date reliability bins render once results settle.

> **Ops prerequisite (not a code task, but the keystone all four research agents +
> the market scan converged on):** run `python model/fetch_odds.py --closing` before
> kickoffs to capture closing snapshots. It fills the CLV record the whole "do we beat
> the market" story — and the project's one defensible moat — depends on. See the
> HANDOFF "#1 next step".

---

## Suggested sequencing (top ~10, in order)

The CLV/settlement pipeline (formerly the #1 item) has shipped, so the trust
centerpiece is now mostly in place — the order shifts to *using* it (edges,
staking, logging) and *finishing* its public face.

1. **TASK-003** — Best-book-price edges in the model — feeds the edges page and
   Kelly; the per-book data already exists, this consumes it.
2. **TASK-002** — Edges page (best-price) — the actionable centerpiece; unblocks
   filtering, digest, bet-logging.
3. **TASK-005** — Quick bet-logging helper — start capturing the track record NOW
   (qualifiers/friendlies); the settlement/CLV machinery is ready for the data.
4. **TASK-004** — Fractional-Kelly staking — turns the gate into real sizing.
5. **TASK-006** — Compliance/RG footer disclaimer — near-zero effort, removes a
   glaring gap before more public surface ships.
6. **TASK-007** — "Today" dashboard hero + countdowns — biggest retention lever.
7. **TASK-001** — Finish the CLV/ROI scoreboard (P/L curve + hit/miss list) — small
   remaining slice now the data layer exists.
8. **TASK-011** — CLV-vs-closing confidence interval — the honest "beats the market"
   caveat; small remaining slice.
9. **TASK-009** — Publish the calibration report — proof of honest forecasting.
10. **TASK-008** — Reposition copy — align the pitch with TASK-001/009.
