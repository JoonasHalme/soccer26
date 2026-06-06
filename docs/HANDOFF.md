# HANDOFF — read this first

Continuation notes for soccer26, a personal **World Cup 2026 betting-analysis**
site. Last worked: **2026-06-06**. Tournament kicks off **2026-06-11**.

If you're picking this up cold: read this file, then `docs/backlog.md` (the task
list) and `docs/site-improvements.md` (review findings). For the strategic roadmap
see `docs/platform-research.md` (expert-panel synthesis — start at §0 unblockers + §5
priority table), `docs/market-research.md` (competition/market-viability scan),
`docs/frontend-improvement-plan.md` (visual/UX critique), **`docs/design-direction.md`
(the interface-rework master plan — a 4-designer panel's consolidated direction + phased
roadmap; the active front-end workstream, with a progress log)**, and
`docs/sharp-direction.md` (the "sharper/less-rounded" aesthetic spec the owner asked for).
The rest of `docs/` is background.

---

## What this project is

An Elo + Poisson model that produces World Cup 2026 match probabilities, finds
**value edges** where it disagrees with the *de-vigged* market, and an **auditable
bet log** graded against the closing line (CLV). Positioning is deliberately
honest: well-calibrated and beats a naive baseline, but **"beats the market" is
not yet proven** — that's what the CLV track record is for. It's "analysis, not
tips."

```
site/        Astro static site (dashboard, edges, matches, groups, bets, calibration, bracket)
model/       Python: Elo+Poisson model + the data/settlement/CLV pipeline
bets/        bets.json (source of truth for P/L) + schema.json
fixtures/    fixtures.json — 104 WC2026 matches (incl. full knockout bracket slots)
docs/        backlog + research + this handoff
```

## Current state (verified 2026-06-06)

- **99 pytest tests pass** (`python -m pytest tests/ -q`).
- **Site builds clean — 174 pages + 166 OG PNGs** (`cd site && npm run build`).
  Build now takes **~35s** (was ~3s) because OG-card rendering (satori→resvg) runs at
  build; `npm run dev` is unaffected. (111 pages before the SEO pages + /methodology.)
- `bets/bets.json` is **empty** (no bets logged yet — correct, tournament hasn't started).
- **0 fixtures have closing-odds snapshots** — see the #1 next step below.
- Pages live: `/` `/edges` `/matches` `/matches/[id]` `/groups` `/group/[id]`
  `/team/[slug]` `/bets` `/calibration` `/bracket` `/outrights` `/predict`
  `/methodology` (+ `/feed.xml`, `/og/*` images). Nav is in
  `site/src/layouts/Base.astro` (the /team + /group pages are SEO landing pages,
  reached via internal links, not the top nav).

## ⚠️ Environment gotchas (important)

- **NOT a git repo.** There is no version control / no commits / no undo. Be
  careful with destructive edits; there's no safety net.
- **Windows / PowerShell.** Run shell commands **individually** — do NOT chain with
  `&&` or `;` (the user's pre-approved permission list depends on this).
- **Dev server is NOT running across sessions.** Start it with `cd site` then
  `npm run dev` → http://localhost:4321.
- `ODDS_API_KEY` is in `.env` (The Odds API free tier, ~490 requests/month left).
  Only `fetch_odds.py` and `fetch_results.py` call it — be frugal.
- Generated artifacts (don't hand-edit): `site/public/data/predictions.json`
  (+ `.hash.json` + append-only `predictions_ledger.json` + `predictions_archive.json`
  — frozen pre-kickoff 1X2 per match, drives the post-match card + live calibration),
  `news.json`, `calibration.json`, `simulation.json`; `model/data/calibration.json`,
  `ratings.json`.
- **Python↔TS logic is duplicated** (Kelly, mean-CI t-table, de-vig consumption)
  between `model/` and `site/src/lib/data.ts`. They're currently in sync (the t-table
  was just reconciled to df=30) but this is a standing drift risk — see the deferred
  "golden-fixture cross-check" item.

## The pipeline (how to run it)

Pre-tournament / weekly, from repo root, each line separately:
```
python model/fetch_fixtures.py                  # cup.txt+cup_finals.txt -> fixtures.json (parses too)
python model/train_ratings.py                   # Elo on history -> model/data/ratings.json
python model/fetch_odds.py --markets h2h,totals # consensus + per-book odds into fixtures.json
python model/anchor.py                          # fit per-confederation Elo offsets vs the market -> confederation_offsets.json (re-run when ratings/odds change; predict.py + simulate.py apply them)
python model/predict.py                         # -> predictions.json (anchored model, de-vigged + best-price edges) + hash + predictions_ledger.json + predictions_archive.json (frozen pre-kickoff preds)
python model/fetch_news.py                       # RSS team news -> news.json (free, no key)
python model/export_calibration.py              # backtest -> calibration.json (drives /calibration)
python model/simulate.py                         # Monte-Carlo -> simulation.json (drives /outrights); ~1s for 20k sims
python model/validate_bets.py                    # enforce >=5%-edge-or-rationale discipline
```
Log a bet from an edge: `python model/add_bet.py --edge m-007:HOME --odds 2.15`
(`--dry-run` to preview; stake defaults to ¼-Kelly).

Matchday (once games start, June 11+), in order:
```
python model/fetch_odds.py --closing   # snapshot the CLOSING line shortly BEFORE kickoff
python model/fetch_results.py          # pull final scores into fixtures.json
python model/settle.py                 # grade bets -> result + pnl
python model/clv.py                    # CLV vs de-vigged close + beat-rate/avg/CI
```

## 🔝 #1 next step — the ops prerequisite that unblocks everything

**Run `python model/fetch_odds.py --closing` before kickoffs to capture closing
snapshots.** Right now 0 fixtures have them, so:
- CLV has no data (the entire "did we beat the market" story is empty),
- the "line moves / steam" view can't be built.
This is an operational cadence, not code. It also needs the bet log to start being
populated (on warm-ups/qualifiers if possible) so a real track record exists before
the tournament. Everything the project is *for* depends on this.

## What was done recently (so you don't redo it)

**2026-06-06 session:** Rebuilt `/bracket` as a real *connected* bracket
(site-improvements #15). It derives the knockout feeder tree from `fixtures.json`
(`W<game_no>`/`L<game_no>` → match; post-order DFS for top-to-bottom order) and
draws deterministic SVG elbow connectors linking each feeder pair to the tie it
feeds, plus per-round colour accents, round headers, a 🏆 Champion apex node, and
an SR-only list fallback. Added `game_no?` to the `Match` type in `data.ts`.
Builds clean (111 pages); verified in-browser. Geometry is fixed-px (board height
1248, R32 pitch 78) so the connectors align exactly — it's a wide graphic in the
existing `.bk-scroll` horizontal-scroll container.

Then cleared the **quick-wins batch** (7 parallel lanes, disjoint files; see
`docs/site-improvements.md` items 4–14, all ✅ 2026-06-06): self-hosted fonts
(`@fontsource-variable/*`, dropped Google Fonts); dashboard reorder (empty bankroll
cards moved below actionable content); EV-longshot tags + Stake emphasis on `/edges`;
calibration metric glosses; SR text-alternatives for the equity + reliability charts;
typed the `bestBookPrices` accessor (removed the unchecked cast); explicit `render()`
guard in `matches/[id].astro`; de-duped the `/bets` stat rows; ★ + sr-only best-price
marker in `BookmakerOdds.astro`; edges a11y (aria-pressed/aria-live confirmed, 44px
chips). Build clean (111 pages); all four changed pages spot-checked in-browser.

Then shipped two data-backed product features (site-improvements #19, #20, both ✅):
a **Kelly portfolio-exposure strip** on `/edges` (open-edge count, total ¼-Kelly
stake, % of bankroll at risk — warn-coloured at 456% on the current edge set, with
an honest "this is the correlated ceiling" caveat), and an **injury flag on the
matchday hero** in `index.astro` (amber "✚ injury news" pill when a tagged
`is_injury_related` story touches either team — e.g. the Mexico v South Africa
opener). Build clean (111 pages); both verified in-browser.

Then shipped **TASK-025 — per-team / per-group SEO landing pages**: `team/[slug].astro`
(48) + `group/[id].astro` (12), each with hero, fixtures, value-edges table, group
standings (current team highlighted) and team-filtered news. New `teamSlug()` +
`teamGroups()` in `data.ts`; `Base.astro` gained a `description` prop + canonical/OG/
Twitter meta (no XML sitemap yet — needs `site` set in `astro.config`); `GroupCard`
now links team names → team pages and "Group X" → group pages, wired from /groups +
dashboard. **Build now 171 pages** (was 111); verified in-browser incl. accented
`curacao` / `bosnia-and-herzegovina` slugs.

Then shipped **TASK-021 (tamper-evident ledger) + TASK-016 (/methodology page)**:
`predict.py` now appends each run to an append-only `site/public/data/predictions_ledger.json`
(de-duped on a timestamp-free content hash so identical re-runs don't bloat it). New
`/methodology` page explains the model (Elo→Poisson/Dixon-Coles→markets), value-finding,
honest CLV grading, a glossary, honest limitations, and surfaces the **latest SHA-256 +
time + a "how to verify" + recent-entries table** from the ledger. `loadLedger()` added
to `data.ts`; "Methodology" added to the nav + a footer link. **Build now 172 pages**;
86 pytest still green (predict.py change verified); methodology verified in-browser.
TASK-016's remaining slice = inline jargon tooltips across other pages (glossary is
centralised on /methodology for now).

While wiring the ledger I fixed a **latent Windows tamper-evidence bug**: `predict.py`
used `Path.write_text`, which translates `\n`→`\r\n` on Windows, so the on-disk
`predictions.json` bytes never matched the SHA-256 (computed over `\n` bytes) — the
"re-hash the live file" check would always have failed here. Now it writes
`write_bytes(payload.encode("utf-8"))` and is **idempotent**: it only rewrites the
file/hash/ledger when the *picks* change (keyed on a timestamp-free content hash), so
the live file ↔ sidecar ↔ latest ledger entry stay byte-consistent. Verified
end-to-end: `sha256(dist/data/predictions.json)` == ledger == the hash shown on the page.

Small-improvements pass (2026-06-06): match detail pages now link team names →
`/team/[slug]` (group-stage names only; knockout placeholders stay plain), completing
the SEO internal-linking web. New reusable `Tooltip.astro` (keyboard- + SR-accessible
dotted-underline term with a hover/focus bubble) wired for the terms each page *uses
but doesn't define* — "de-vigged" + "Kelly" on `/edges`, "de-vigged" on `/bets`
(TASK-016 now fully ✅). Build clean (172 pages); 86 pytest green; tooltip hover +
links verified in-browser.

Then shipped **TASK-015 — shareable OG cards**: build-time 1200×630 PNGs via
**satori → @resvg/resvg-js** (`site/src/lib/og.ts`), fonts vendored as static TTFs in
`site/src/assets/og-fonts/` so the build stays offline. 166 cards — per-match (with
the model prob bar), per-team, per-group, a track-record card, and a default site
card under `src/pages/og/*`. `Base.astro` emits `og:image`/`twitter:image`
(`summary_large_image`); pages set `ogImage` (match/team/group/bets override). All
cards verified visually. **Team flags are deferred** (remote flagcdn → would need a
build-time fetch and break offline builds); absolute `og:image` URLs need the deploy
domain (auto-upgrade via `Astro.site`). ⚠️ OG rendering adds **~30s to `npm run
build`** (now ~35s; `npm run dev` is unaffected — endpoints render on demand).

Then shipped **TASK-028 — outright Monte-Carlo**: `model/simulate.py` simulates the
whole tournament (group round-robins → 8-best-thirds → official R32 third-place
allocation via bipartite matching → knockout), **vectorised with NumPy** (20k sims in
~1.1s), writing `site/public/data/simulation.json`. New `/outrights` page (champion
leaderboard + full 48-team probability table, honest framing) + nav link;
`loadSimulation()` in `data.ts`. Goal sampling is `lambdas()`, a vectorised mirror of
`elo.expected_goals` (test-guarded). **92 pytest green** (6 new — exact probability
totals, monotonicity, seed determinism, lambdas-match-model). Build clean (173 pages);
verified in-browser. Re-run `python model/simulate.py` when ratings/fixtures change.

Then shipped **TASK-014 — newsletter + RSS digest**: `site/src/pages/feed.xml.ts`
builds a hand-rolled RSS 2.0 feed (40 items — top 20 edges + 20 tagged news, XML-escaped,
works with no configured domain — links auto-upgrade via `Astro.site`). New
`Newsletter.astro` signup stub on the dashboard (set `NEWSLETTER_ACTION` to a
Buttondown/Substack embed to go live; honestly points to the working RSS meanwhile).
RSS autodiscovery `<link>` in the head + a footer feed link. Build clean (173 pages);
feed validated as well-formed XML and verified in-browser.

**Front-end professional rework (in progress, 2026-06-06):** ran a **4-designer panel**
(junior/mid/senior/director) → consolidated into `docs/design-direction.md` (north star:
"an instrument, not an app"; the gap to premium is *discipline, not a rebuild*). Also added
new features: **"Beat the Model" prediction game** (`/predict`) and a **market-research
scan** (`docs/market-research.md`). Shipped the **first cut of the discipline pass**: body
wash 3 radials → 1 subtle green (magenta/cyan out); active nav green-fill → accent tint;
hero title gradient-text → solid + one accent phrase; `.panel` top-wash removed + shadows
flattened; radii 16→13 / 22→18; motion tokens (`--ease`/`--dur`); `theme-color`; skip link
+ global `.sr-only` + `:focus-visible` radius fix; nav active-pill scroll-into-view;
`selectionShort()` (no raw `OVER_2_5`/`HOME` on dashboard tiles/badge); dead newsletter
form → RSS CTA; dashboard empty-state dev-copy sanitised. Then **batch 2**: stage colours
re-ramped to a cool→gold progression; **data-viz tokens** (`--viz-home/draw/away`)
tokenised across ProbBar + MatchCard; type scale (h2 1.25→1.4rem, weight 800→700,
slashed-zero); **`PageHero` component** + applied to **/calibration** (the trust page
that lacked a hero); stat-cards retuned (left-rail accent, magenta demoted). Build clean
(174 pages); verified in-browser (bracket, calibration, match cards). Then **batch 3 — the SHARP pass** (owner wanted it less rounded / more professional;
research spec in `docs/sharp-direction.md`): radii **6px panels / 4px controls / 8px hero**
(was 13/9/18), **de-pilled every chip/pill/badge** sitewide (`999px`→`--radius-sm`, keeping
circular dots), and **crisper higher-contrast borders**. Then **batch 4** completed the
sharp typographic/elevation follow-up: added **JetBrains Mono** (`--font-mono`) on all
numerals + micro-labels (tables, stat values, eyebrows, hero-chip counts, edge tiles,
clocks — the "quant terminal" signal); **flat bordered elevation** (no blur shadows on
panels/cards; hover = border-step, not lift; crest glow killed); **ruled, denser tables**;
weight capped at 700 everywhere; body wash flattened to ~0.03. Build clean (174 pages);
verified — dashboard + edges now read like a precise data instrument. **Full progress log
+ remaining phases in `docs/design-direction.md`** (sharp spec in `docs/sharp-direction.md`).
NOTE: a 4th vendored font (`@fontsource-variable/jetbrains-mono`) was added. Then **batch 5**
(owner feedback): **muted the green** (`--accent #1fe07a→#2fb672` + glows removed — the neon
was eye-straining), **finished the mono sweep** (all secondary-page figures now mono), and
added **vertical column rules** to tables (ruled-ledger look). Build clean (174 pages); the
sharp/calm desktop direction is essentially complete. Then **batch 7 — Phase-2 mobile (core
✅)**: new **`MobileNav.astro` bottom tab bar** (5 routes, SVG icons, safe-area-aware, ≤720px)
+ a global **`.table--cards`** modifier that collapses wide tables into label:value cards at
≤560px — applied to the **edges**, **outrights** (9-col), and **bets** tables (verified the
edges EV/Stake columns are no longer off-screen; desktop unaffected, media-query-gated).
Then **batch 8** finished the **table sweep** — `.table--cards` now on *every* wide table
(match-page edges/bets, team/group edge tables, and the bookmaker-odds table with
team-name `data-label`s), verified collapsing on a phone; group standings kept as a
scroll compare-table on purpose. **Phase-2 mobile is done.** Then **batch 9 — finishing touches**: a restrained `main`
fade-up entrance (reduced-motion safe); **`PageHero` retrofit** (globalised `.hero-chip`,
converted groups/outrights/bracket heroes to the shared component — killed the 3-padding
drift); and a **true-minus `signed()`/`money()` formatter** applied to P/L·ROI·CLV on
`/bets` + dashboard. Build clean (174 pages). **The redesign is essentially complete** —
the interface went from soft/neon/rounded to a sharp, calm, mono, mobile-ready data
instrument. Full progress log (batches 1–9) in `docs/design-direction.md`; the sharp spec
is `docs/sharp-direction.md`. (Dashboard/team/group heroes intentionally kept bespoke;
a full inline-margin→utility sweep was deferred as low-payoff.) **Front-end design is
WRAPPED.** Last tweak: removed the redundant "Groups & standings" section from the
dashboard (it duplicated `/groups`). Next work returns to the backlog / research-panel
improvements (see `docs/backlog.md` + `docs/platform-research.md §5`).

**Then shipped the result-trust features (TASK-042 + TASK-043, the panel's top
"credibility differentiator"):** a **post-match "we said X → result Y" card** on finished
match pages (correct/missed verdict + pre-kickoff call vs actual + settled bets) and a
**"Tournament 2026 — live" calibration scorecard** on `/calibration` (matches graded,
top-pick hit rate, live Brier, one-vs-rest reliability table). Both are **empty-state-safe**
and light up automatically as results land. **Key new infra:** `predict.py` now writes
`predictions_archive.json` (frozen pre-kickoff 1X2 per match) so a match's prediction
survives kickoff. Verified both by injecting a 2–0 result (card showed "Top pick ✓ correct";
live cal showed 1 match graded, Brier 0.026) then reverting. 99 pytest green; build clean
(174 pages). (Live calibration's *de-vigged-closing* comparison series still needs the
closing-odds capture cadence — the standing #1 ops blocker.)

**Then TASK-044 — power-method de-vig.** `predict.devig_market()` now defaults to the
**power method** (`DEVIG_METHOD="power"`: fit one exponent so `sum((1/odds)^k)=1`)
instead of proportional/multiplicative — the favourite-longshot correction the quant
panel asked for. `"multiplicative"` still selectable; each edge records `devig_method`.
Regenerated predictions (edges 123→126, mostly a couple more *draw* edges — the expected
direction); hash chain + idempotency re-verified; methodology page/glossary updated;
+4 tests (103 green).

**Then TASK-024 — derived markets.** `elo.derived_markets()` sums the existing
Dixon-Coles matrix into double-chance, Draw-No-Bet, and the top-6 exact scores;
`predict.py` emits a `derived` block; a **"More markets"** section on the match page
renders them (display-only, no odds → no edges). +5 tests; suite 108 green; build clean
(174 pages); hash chain intact.

**Then TASK-045 — markets-vs-model divergence tracker (the "unique feature").**
`predict.find_divergences()` emits every priced outcome's signed model−fair gap (both
directions, no threshold, same power-de-vigged baseline as edges) into a `divergences`
block; `data.ts.topDivergences()` collapses each match-market to its largest-|Δ| leg and
ranks by |Δ|. New **`/divergence`** page (summary strip + direction/market filter chips +
ranked table) added to the top nav after Edges. **Surfaced a model signal worth noting:**
the biggest gaps are large *negative* ones — the model rates favourites well below the
market (e.g. Belgium–Iran model 34% vs market 70%), i.e. systematic favourite
under-rating, not 144 value bets. The page copy frames gaps as "edges OR model blind
spots." Same odds as the edges page. +4 tests; suite 112 green; build clean (175 pages);
hash chain intact.

**Then investigated that favourite under-rating and shipped TASK-046 — market-blend prior.**
Root cause (now resolved): NOT a bug. Diagnosed by elimination — data clean (6,015 matches
2020+, all teams covered), future WC rows dropped (NaN scores), names join, and the skew is
**K-invariant** (Iran/Morocco/Ivory Coast stay above Germany/Belgium/Netherlands at every K
from 32–101). It's vanilla Elo's **inter-confederation isolation** (CAF/AFC rarely play UEFA,
so pools aren't anchored) + real Euro underperformance; the model can't see squad value, the
market can. **Fix (user-chosen):** `predict.blend_forecast()` publishes `forecast = 0.5·model
+ 0.5·de-vigged-market` for 1X2/O-U where priced (`MARKET_BLEND_MODEL_WEIGHT`). Pure
`probabilities` stays the raw instrument (drives score-shape markets + sims); **edges +
calibration archive now use the blend**, so structural errors stop masquerading as value.
Edges fell **126→75**; Belgium 34%→52%. Match pages gained a **Model vs market** panel; edges
page says "Our call"; methodology documents it. +5 tests (117 green); build 175 pages; hash
chain intact.

**Then TASK-047 — tuned the blend (confidence-weighted) + found the O/U bias.** Measuring
first settled it: the model disagrees with the market by a **median 15 pts** and the biggest
gaps ARE the broken games, so a flat weight can't work. Made the blend **disagreement-aware**:
per group `w = 0.6 / (1 + (D/0.17)^2)`, `D = max|model−market|`. Model trusted ~0.6 when it
agrees, collapsing toward 0 as it strays. **Edges 75 → 12**, zero fake draw/away longshots,
all 12 biggest-disagreement matches now edge-free, Belgium–Iran trusts the model **11%**
(shown in the panel caption). Per-match weight on `forecast.weight`. 118 tests green; build 175.

**Then TASK-048 — fixed the totals over-bias at the source.** Diagnosed: the totals shape
coefs were fit blind (`GOALS_BASELINE` rode the 1X2 objective; the two coefs were never
fitted). The **positive** strength coef inflated totals on the strong WC field. Made the totals
params fittable to an **O/U-2.5 log-loss objective** (`calibrate.py fit_totals` / `--totals-only`,
loadable via `elo.py`/`calibration.json`) and refit (1X2 held): `GOALS_BASELINE 2.898→2.591`,
`STRENGTH_COEF +0.0011→~0`, `MISMATCH_COEF 0.0008→0.0015`. **WC over-rate 0.553→0.478** (market
0.496, realised 0.490); O/U edges went from one-sided 6-OVER/1-UNDER to balanced 1/5; total
edges 12→10. Improves walk-forward O/U *and* 1X2 log-loss. 119 tests green; hash chain intact.
Also fixed **C1** (TASK-052): `MatchCard.astro` + match OG card now use `publishedProbs()` (the
blend), not the raw skewed model.

> **5-agent expert review ran (market/quant/code/security/test).** Triaged into TASK-049…056 +
> quant modelling items in `docs/backlog.md`. **Cross-cutting #1 (market + quant): the audited
> CLV record is the whole moat and is still EMPTY — closing-odds capture must start on the
> June 11 openers or the first-week data is permanently lost; and if bets are logged off the
> current edge list before remaining biases are addressed, the first CLV sample is polluted.**
> Top fixes queued: XSS news-URL allowlist (TASK-049, HIGH), tamper-evidence claim vs reality
> (TASK-050), settle.py LIVE-grade bug (TASK-053), typed loaders + first TS tests (TASK-055).
> Durable model item: confederation anchoring at the ratings source (fixes the knockout sims the
> blend can't reach). **Also flagged: `astro.config.mjs` still has no `site` set — breaks every
> OG/RSS/sitemap absolute URL and all indexability; cheap unblock.**

**Then shipped post-review items 1/2/3 (2026-06-06):**
- **TASK-057 — closing-odds cadence (the #1 blocker):** `model/capture_closing.py`, a
  quota-aware wrapper that only calls the Odds API when a match is within `--within-hours`
  of kickoff and not freshly captured (`capture_plan` pure logic, `--plan`/`--dry-run`),
  `scripts/capture-closing.ps1` + `docs/closing-odds-runbook.md` (hourly Task Scheduler
  one-liner). +8 tests. **Owner still must register/run it for the June 11 openers.**
- **TASK-058 — SEO/social unblock:** `astro.config.mjs` sets `site` from `SITE_URL` (placeholder
  default + build warning), `@astrojs/sitemap` (emits `sitemap-index.xml`), absolute
  canonical/`og:url` in `Base.astro`, dynamic `robots.txt.ts`. **Owner: set `SITE_URL` at deploy.**
- **TASK-049 (XSS) + TASK-053 (settle LIVE-grade) FIXED** — see backlog. 128 tests green; build
  clean (175 pages, sitemap emitted).

**Then a UI-polish pass (2026-06-06), all verified live in-browser:**
- **Top nav de-cluttered:** 11 items → primary `Dashboard · Edges · Matches · Groups · Bracket ·
  Outrights · Bets · Calibration` + a **"More ▾" dropdown** (`Methodology · Divergence · Predict`).
  Fixes the methodology link clipping off the right edge. Dropdown is a static `<details>`
  (closes on outside-click/Esc); horizontal scroll moved to an inner `.nav-scroll` so the menu
  isn't clipped. (Groups was requested between Matches and Bracket.)
- **Bookmaker odds collapsible:** `BookmakerOdds.astro` now wraps the long per-book table in a
  `<details>` (collapsed by default) with the best 1X2 prices teased in the summary.
- **Matchday = host-region (Eastern) date; start times = viewer-local:** `data.ts` adds
  `matchdayKey()`/`matchdayLabel()` (`America/New_York`) and `nextMatchday` groups by it — so a
  late game like 02:00 UTC (22:00 ET) lands on the *previous* day's matchday. New
  `LocalTime.astro` renders a UTC `<time data-lt>` server-side that a global Base.astro script
  rewrites to the **viewer's** timezone on `DOMContentLoaded` (the script must wait for the DOM —
  it runs before `<main>`). Retrofitted match hero, MatchCard, dashboard rows, edges/divergence/
  group/team Kickoff cells, bracket. Verified: Helsinki viewer sees "22.00 UTC+3" under a
  "Thursday 11 June" matchday. Dead `fmtKick`/`kickoffTime` helpers removed.

**Then the honesty trio + small features (2026-06-06):**
- **TASK-050 (tamper-evidence):** ledger is now a real **prev-hash chain** (`ledger_entry_hash`
  in `predict.py`; existing entries backfilled), and the methodology copy is honest about what it
  does/doesn't prove (self-published; external anchor = roadmap). +3 chain tests.
- **TASK-054** CLV de-vig docstrings corrected (power, not multiplicative). **TASK-051** added
  `.env.example`; key rotation is still an owner action.
- **TASK-018** new **`/policy`** page (no-affiliate, jurisdiction, responsible gambling, data
  sources, privacy) linked from the footer.
- **TASK-029** freshness signals: `data.ts` `latestBookUpdate/oddsAsOf/oddsMovedSincePredictions`;
  "as of" stamp on match odds + a dashboard "in sync / odds moved" badge.
- **TASK-020** `model/check_edges.py` — local diff of edges (APPEARED/GONE/MOVED) vs a snapshot.
- **TASK-019** live mode: `model/publish_live.py` → `public/data/live.json`; a defensive dashboard
  poller patches LIVE/FT scores in without a rebuild. Matchday loop documented in the runbook.
- 137 tests green (+9); build clean (176 pages); hash chain intact.

**Then the robustness pass — TASK-055 + TASK-056 (2026-06-06):**
- **First JS/TS tests:** added **Vitest** (`npm --prefix site run test`) + `site/src/lib/data.test.ts`
  (19 tests over Kelly/meanCI/standings/teamSlug/divergences/calibration/validators). Hardened
  `readJson` (missing→fallback, corrupt→throw, optional **validator**→throw with filename) and added
  exported `validateFixtures/validateBets/validatePredictions` on the 3 core loaders (TASK-055/039).
- **Audit-trail + cross-language tests:** `tests/test_predict_main.py` runs real `predict.main()` on
  a temp fixture and asserts hash==sidecar==ledger, **valid prev-hash chain**, no CRLF, idempotent
  re-run. A **golden cross-check** (`tests/golden/staking_clv_golden.json`) is asserted by BOTH
  `tests/test_golden.py` and `site/src/lib/data.golden.test.ts` so the duplicated Kelly/t-table math
  can't drift (TASK-056).
- **CI gate:** `scripts/check.ps1` runs **pytest → vitest → build**, fails fast. Verified green:
  **pytest 148, vitest 26, build 176 pages.** New commands: `npm --prefix site run test`,
  `powershell -File scripts/check.ps1`.

**Then TASK-059 — confederation anchoring (the durable source fix).** `model/anchor.py` fits one
Elo offset per confederation against the de-vigged market on the 63 neutral priced games, mean-zero
across the 48-team field (UEFA +95, CONMEBOL +79; CAF −58, AFC −91, CONCACAF −113; stored in
`model/data/confederation_offsets.json` with the `confederations.json` map). `apply_offsets()` is
called in **both** `predict.py` and `simulate.py`, so the correction reaches per-match AND the
knockout/outright sims (the market blend never reached the sims). **Halved** the model-vs-market
disagreement (median 0.15→0.08); ratings now sane (Germany>Iran, Brazil>Morocco); **outrights sane**
(Spain 17/France 11/Argentina–Brazil 10, Morocco out of the top); edges 10→7; Belgium–Iran raw model
34%→54% so the blend does far less. Re-run order if ratings change: `anchor.py` → `predict.py` →
`simulate.py`. +6 tests; full gate green (pytest 154, vitest 26, build 176). Methodology/divergence/
outrights copy updated. Open: OFC offset noisy (NZ only).

**Then TASK-060 — quant transparency (A1 + A3).** (A1) every edge now carries `model_raw_prob` +
`raw_edge_pct` (the pre-blend gap), surfaced on the edges page + match table as "raw +W%" — so the
staked edge is honestly shown as `trust × raw gap` (staked ~5% vs raw 15–19%). (A3) `clvStats` gained
a **Wilson binomial CI** for the beat-rate (now the lead metric on `/bets`) + a **stake-weighted**
avg CLV, with the fragile per-bet mean t-interval demoted. +4 tests; full gate green (pytest 155,
vitest 29, build 176). **TASK-031 (attack/defence split) deliberately DEFERRED** — too large a
rating-model rewrite to land safely days before kickoff.

**Then the INFRA batch (TASK-061) — the project is now in git + CI (see `docs/infra-plan.md`).**
Repo: **https://github.com/JoonasHalme/soccer26** (pushed; `main`). Done: `git init` + first commit;
un-ignored `predictions.json` and **committed the source data** (`internationals.csv` + `cup*.txt`)
so the pipeline + ledger are fully reproducible; pinned `requirements.txt` to minor versions; a
`.gitattributes` keeps `predictions.json` byte-exact (LF) across OSes so the SHA-256 ledger verifies;
`.gitignore` now excludes `.claude/` + `closing-capture.log`. **GitHub Actions live:** `ci.yml`
(pytest+vitest+build on every push — **green** on a clean Ubuntu runner), `matchday-poll.yml`
(hourly, quota-safe: `capture_closing` + `fetch_results --only-if-active` + `settle` + `publish_live`,
commits changes → auto-deploys), `refresh-odds.yml` (manual, credit-spending odds refresh). Added a
`--only-if-active` quota gate to `fetch_results.py`. `site/public/_headers` edge-caches `live.json`
(poller dropped `no-store`).
**LIVE:** repo is **public** (so the SHA-256 ledger is now externally verifiable — anyone can clone
+ re-hash; partial TASK-050 anchor) and deployed on **Cloudflare Pages → https://matchprediction.pages.dev**
(auto-deploys on every push; sitemap/OG/canonical are absolute + correct). Branch protection: a
ruleset on `main` blocks **force-push + deletion** (admin bypass) — guards the ledger history without
blocking the auto-commit bots. (Require-PR/CI isn't possible on a personal repo — the GitHub Actions
integration can't be a bypass actor, so it'd block the bots; force-push/deletion protection is the
correct fit.)
**Still OWNER action (one thing):** **rotate `ODDS_API_KEY`** and add it as repo secret `ODDS_API_KEY`
(Settings → Secrets → Actions) before June 11 — the hourly `matchday-poll` runs harmlessly without it
pre-tournament but needs it once matches start. Keep the local `capture-closing.ps1` Task Scheduler
job as a June-11 backup.
**Follow-up (nice):** `/methodology` could now point to the public repo as the verification path for
the ledger (the external-anchor item).

**Then TASK-062 — squad/roster on team pages.** `model/fetch_squads.py` parses the public
"2026 FIFA World Cup squads" Wikipedia article (CC BY-SA, no key) → `site/public/data/squads.json`
(48 teams, 1245 players: no/pos/name/club/caps/goals/age + coach). `data.ts` `loadSquads()` +
`Squad.astro` render a **Squad** section on `/team/[slug]` grouped GK/DF/MF/FW; attributed on the
page + `/policy`; squad mentioned in the team-page SEO. +3 parse tests (158 pytest). Empty-state-safe.
Re-run `fetch_squads.py` occasionally (squads are fixed for the tournament).

Then a **smaller-features batch + an expert-panel research pass** (2026-06-06):
- **TASK-012** — matches index now has client-side search (by team), stage filter
  chips, sort, and a "★ Following" filter; hides empty stage sections, live count.
- **TASK-026** — `FollowButton.astro` (★ toggle, `soccer26:following` localStorage,
  `watchlist:change` event) on team pages; the matches "Following" filter reads it.
  Verified cross-page + persistent.
- **TASK-013** — AH + Asian-total **probabilities** from a new shared
  `elo.score_matrix` → `elo.asian_probabilities`; emitted as an `asian` block in
  `predictions.json` and rendered on match pages (handicap table + totals ladder).
  No AH odds sourced ⇒ no AH edges. **7 new pytest** (cross-checks vs 1X2/O-U).
- **TASK-027** — reviewed: `ProbBar` already meets it (role=img + aria-label +
  labeled legend, not colour-only). No change; noted in backlog.
- **Research/planning agents:** 1 front-end agent wrote `docs/frontend-improvement-plan.md`;
  4 expert personas (quant / UX-trust / growth / competitive) researched platform
  improvements → consolidated into `docs/platform-research.md` (read its §0 unblockers
  + §5 priority synthesis first). These are advisory docs, nothing auto-implemented.
**99 pytest green**; build clean (173 pages). `predict.py` re-run added the `asian`
block (ledger entry #2). All three features verified in-browser.

Then started on the panel's net-new picks: shipped **"Beat the Model"** — a
free-to-play prediction game at `/predict` (panel §5 / strategist #2). Users pick the
12 group winners + a champion (saved to `soccer26:picks` localStorage); the model's
picks are shown (from `simulation.json` win_group / champion) and both are scored as
results land (3 pts/group, 10/champion — empty-state until 11 Jun). New page + nav
link "Predict"; verified in-browser incl. localStorage persistence. Also ran a
**market/competition research agent** → `docs/market-research.md` (verdict: a real but
small seasonal niche; the defensible moat is the *audited CLV ledger* — still unproven/
empty until closing-odds capture runs; no head-on rival combines rigor + consumer
product + tamper-evident public record). Build clean (174 pages).


All ✅ — see `docs/backlog.md` "Recently shipped" + "Shipped in the latest pass":
- Model correctness: de-vigged edges, matchup-varying Over/Under, Dixon-Coles,
  fitted/calibrated constants (backtest log-loss 0.92, ECE 0.007, beats baseline).
- Pipeline: CLV + results-settlement (`fetch_results`/`settle`/`clv` + closing
  capture), tamper-evident prediction hash.
- Backlog P0 sequence: best-book price + EV on edges, `/edges` page, fractional
  Kelly staking, `add_bet.py` logger, RG/compliance footer, "today/matchday" hero +
  countdowns, CLV scoreboard + equity curve + CI, `/calibration` page, transparency
  repositioning.
- Review pass + fixes: discipline `>`→`>=`, t-table sync, atomic bet writes,
  de-Unicode CLI, real labels in tables, single edge-% formatter, mobile nav, edges
  a11y, plus a new `/bracket` page. New tests for `add_bet`, staking boundaries,
  predict gaps.
- Content: 72 group-stage match analyses (`site/src/content/matches/`), news feed,
  standings + flags, per-bookmaker odds table, full visual redesign.

## Open work (next candidates, roughly prioritized)

Big recent wins are all **done**: `/bracket` rebuild, the site quick-wins batch
(site-improvements 4–14), Kelly-exposure strip (#19), injury flag (#20), per-team/
group SEO pages (TASK-025), `/methodology` + tamper-evident hash-ledger (TASK-016 +
TASK-021), jargon `Tooltip`, match→team links, and shareable **OG cards** (TASK-015).
See `docs/backlog.md` + `docs/site-improvements.md` for the ✅ trail.

**The expert panel's top picks now lead the roadmap** — see `docs/platform-research.md`
§5. The two unblockers gate the most: (1) **deploy a domain + set `site`** in
`astro.config.mjs` (unblocks OG/RSS absolute URLs + the XML sitemap + SEO for all 173
pages), and (2) the **closing-odds capture cadence** (the standing #1 blocker — fills
the CLV record everything monetizable depends on). High-leverage net-new ideas from the
panel: a living post-match calibration scorecard + "we said X → result Y" card, a free
"Beat the Model" prediction leaderboard, per-team probability "drama curves", and
market-blend/Shin de-vig on the model side.

Remaining smaller items:
- **Wire `NEWSLETTER_ACTION`** to a real provider (Buttondown/Beehiiv) to make signup live.
- **Source AH/Asian-total odds** in `fetch_odds.py` to unlock AH edges (TASK-013 follow-up).
- **Surface best-book line-shopping on the dashboard** cards (still consensus odds).
- Add the "★ Following" filter to `/edges` + the dashboard (TASK-026 follow-up).
- **Task-based nav re-order + "Track record" framing** (#16) — confirm before doing.
- Python↔TS **golden-fixture cross-check tests** (Kelly/CI) — close the drift risk.

OG follow-ups (TASK-015 shipped): real **team flags** in cards (fetch+cache flagcdn
PNGs or vendor a flag sprite — currently brand+matchup+prob-bar only); absolute
`og:image` URLs need the deploy domain.

Bigger backlog features (see `docs/backlog.md` TASK-ids):
- Live calibration tracking (TASK-010), Asian-handicap markets (TASK-013),
  matches search/filter (TASK-012), watchlist (TASK-026), prob-bar a11y (TASK-027).
- One-time wiring when ready: set `NEWSLETTER_ACTION` (in `Newsletter.astro`) to a
  real email provider to make signup live; real flags in OG cards.

## How the user likes to work

Heavy use of **parallel sub-agents** in non-overlapping lanes (one writer at a time
since there's no git to isolate worktrees). Validate with build + tests after
changes. Keep the honest framing — don't overstate "beats the market."
