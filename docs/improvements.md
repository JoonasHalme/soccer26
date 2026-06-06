# Soccer 26 — Improvement Backlog

Prioritized engineering/product review of the World Cup 2026 betting-analysis site.
Effort: **S** = <0.5 day, **M** = 0.5–2 days, **L** = >2 days. UX is owned by a
separate agent and is only flagged briefly here.

---

## Executive summary — top 5 highest-leverage changes

1. **De-vig the bookmaker odds before computing edges.** `find_edges()` compares
   the model probability to `1/odds`, which still contains the bookmaker's
   overround (3–8%). Every edge is therefore overstated by roughly the margin.
   The empirical symptom: **62 of 72 predicted matches show a ">5% edge"** — the
   discipline that is supposed to be the whole point of the project filters
   almost nothing. *(model/predict.py)* — **S/M**

2. **Fix the structurally-constant Over/Under model.** `expected_goals()` always
   splits a fixed `GOALS_BASELINE` (2.55) between the two sides, so total expected
   goals is *identical for every match*. Across all 72 predictions there are only
   **2 distinct Over-2.5 values**. The 19 O/U "edges" the model emits are noise —
   a fixed model number meeting varying book lines — and are actively dangerous to
   bet. Total goals must scale with the strength/attacking profile of the teams.
   *(model/elo.py)* — **M**

3. **No tests, no calibration, no backtest.** There is zero automated testing and
   no way to answer "is the model any good?" before staking real money. A
   historical backtest + calibration check (reliability curve, log-loss/Brier)
   is the single most valuable addition for a project whose stated mission is
   "settle the P/L question by data." *(new model/backtest.py, model/tests/)* — **L**

4. **The README's betting discipline is documented but never enforced in code.**
   Nothing validates that a logged bet actually had `model_edge_pct > 5%` or a
   written rationale; nothing computes model-vs-manual head-to-head accuracy or
   CLV. A `validate_bets.py` + settlement helper turns the prose rule into a
   checkable invariant. *(bets/, new model/settle.py)* — **M**

5. **The data pipeline has an unwritten parser and brittle, silent failure modes.**
   `fetch_fixtures.py` only downloads `cup.txt` and prints "write a parser next"
   (the parser exists in `parse_fixtures.py` but the README workflow never calls
   it, and nothing fetches `cup_finals.txt`). Odds/name normalization is a hand-
   maintained dict that will silently drop unmatched teams. *(model/fetch_fixtures.py,
   parse_fixtures.py, fetch_odds.py)* — **M**

---

## Status (HIGH items addressed in this pass)

- **H1 DONE** — `predict.py` now de-vigs each market (1X2 trio, O/U pair) to
  fair probabilities summing to 1 before computing `edge = model − fair`. Markets
  that aren't fully priced are skipped. Note: de-vigging *raises* per-selection
  edges (fair prob < raw 1/odds), so the headline ">5% edge" count did **not**
  fall by itself — the residual count reflects model-vs-market disagreement
  (calibration, see H3/H4), not the vig. The math is now correct and auditable.
- **H2 DONE** — `expected_goals()` no longer partitions a fixed 2.55. Total goals
  scale with absolute pair strength (vs the WC-mean rating) and matchup mismatch;
  Over-2.5 now takes ~70 distinct values across the 72 priced matches.
- **H4 PARTIAL** — Added a Dixon-Coles low-score correction (`rho`) in
  `match_probabilities` so draws/0-0/1-1 aren't under-predicted. Constant is
  conventional (−0.05); proper fit still needs the backtest (H3).
- **H5 DONE** — New `model/validate_bets.py` enforces schema + the
  >5%-edge-or-rationale discipline (non-zero exit on violation) and reports
  model-vs-manual hit-rate/ROI. Wired into the README workflow.
- **M1 DONE** — `fetch_fixtures.py` now downloads `cup.txt` + `cup_finals.txt`
  and invokes `parse_fixtures.py`; re-parsing preserves already-merged odds.
- **L1 DONE** — `EloTable.update` writes to the canonical key.
- **Tests added** — `tests/` (pytest): de-vig sums to 1, expected goals vary,
  Elo/Poisson/Dixon-Coles + validator sanity (23 tests, all green).
- **Deferred (still open):** H3 (backtest/calibration, L-effort), H6 (rating
  decay / in-tournament feedback), M2–M8, L2–L8.

## HIGH impact

### H1 — Edges computed against vig-inflated implied probabilities
`find_edges()` uses `implied_prob = 1/odds_decimal`, which sums to >100% across a
market because of the bookmaker overround. The model's edge is overstated by the
margin on every selection, producing false positives at scale (62/72 matches flag
an edge). Normalize implied probabilities within each market (1X2 as a set,
O/U as a pair, BTTS as a pair) so they sum to 1 before differencing, or subtract
an explicit margin estimate. Files: `model/predict.py`. Effort: **S/M**.

### H2 — Over/Under is effectively a constant, yet emits "edges"
`expected_goals()` sets `lam_home = total/2 + half_diff`, `lam_away = total/2 - half_diff`
with `total = GOALS_BASELINE` fixed, so `lam_home + lam_away == 2.55` always. Over-2.5
probability barely moves (2 distinct values in 72 matches) and BTTS is similarly
flat. The model should derive each side's expected goals from attack/defence
strength (e.g. a Poisson/Dixon-Coles regression on the historical CSV, or scale
total goals by combined Elo) rather than partitioning a constant. Until fixed,
O/U and BTTS edges should be suppressed, not bet. Files: `model/elo.py`,
`model/predict.py`. Effort: **M**.

### H3 — No backtest / calibration harness
There is no script that replays the trained ratings against held-out historical
matches to measure log-loss, Brier score, and calibration (reliability curve),
nor a tournament-time tracker comparing predicted vs realized outcomes. Without
this the central claim ("did the model make money / is it accurate?") is
unfalsifiable. Add a walk-forward backtest over `internationals.csv` and a
post-hoc calibration page fed by settled results. Files: new `model/backtest.py`,
`model/calibration.py`; surface on the site. Effort: **L**.

### H4 — Independent-Poisson scoreline model overstates confidence and mis-prices draws
The score matrix is `np.outer(h, a)` — goals are assumed independent. Real
football has positive correlation at low scores; independent Poisson
systematically *under*-predicts draws and 0-0/1-1 scorelines. The module
docstring of the match note even says "draw probability... arguably should be even
higher." Add a Dixon-Coles low-score correction (the standard rho adjustment on
the 0-0/1-0/0-1/1-1 cells) and refit. This compounds with H1/H2 to inflate
1X2 edges. Files: `model/elo.py`. Effort: **M**.

### H5 — Betting discipline is prose-only; not enforced or measured
`README.md` states "only bet when `model_edge_pct > 5%` or with explicit
rationale," and `schema.json` says rationale is "required if model_edge_pct is
null" — but no code enforces either, and `bets.json` is empty so it's untested.
There is also no computation of: model-vs-manual ROI split, CLV (closing-line
value), or per-market performance. Add `validate_bets.py` (schema + discipline
gate, runnable in CI) and extend `bankrollStats` / a new page to split results by
`source` (model vs manual) and market. Files: `bets/schema.json`,
`site/src/lib/data.ts`, new `model/validate_bets.py`. Effort: **M**.

### H6 — Ratings are static and never decayed; tournament results don't feed back
`train_ratings.py` filters to matches since 2020 and trains once; `predict.py`
loads a frozen `ratings.json`. There is no time-decay/regression-to-mean on older
results, no in-tournament rating update as 2026 group games finish, and no
mechanism to mark a match `FINISHED` and re-predict downstream knockout edges.
For a month-long event this means later-round predictions ignore everything that
just happened. Files: `model/elo.py`, `model/train_ratings.py`, `model/predict.py`.
Effort: **M/L**.

---

## MEDIUM impact

### M1 — `fetch_fixtures.py` is a stub; the documented workflow is broken end-to-end
The README "weekend workflow" runs `fetch_fixtures.py` then `train_ratings.py`
then `predict.py` — but `fetch_fixtures.py` only saves `cup.txt` and prints
"Next: write a parser." The actual parser (`parse_fixtures.py`) is never invoked
by the workflow, and nothing fetches `cup_finals.txt` (the knockout source it
depends on). Wire `fetch_fixtures.py` → `parse_fixtures.py` into one command (or
document both), and fetch both source files. Files: `model/fetch_fixtures.py`,
`model/parse_fixtures.py`, `README.md`. Effort: **S/M**.

### M2 — Team-name normalization is a brittle hand-maintained dictionary
Three separate name maps exist (`NAME_ALIASES` in elo.py, `ODDS_TO_FIXTURE` in
fetch_odds.py, and the implicit roster-split heuristic in parse_fixtures.py).
Unmatched odds events are silently skipped (`if not match: continue`), so a
single new spelling drops odds for a fixture with no warning. `check_names.py`
exists as a diagnostic but isn't part of the pipeline. Consolidate to one
canonical alias table, and make `fetch_odds.py` log every unmatched event.
Files: `model/elo.py`, `model/fetch_odds.py`, `model/parse_fixtures.py`,
`model/check_names.py`. Effort: **M**.

### M3 — No staleness / freshness signals anywhere
`predictions.json` records `generated_at`, but nothing flags when odds or
predictions are stale relative to kickoff (the dashboard just prints the
timestamp). For a market that moves fast (the Brazil-Morocco note explicitly
worries about line movement), a "odds fetched N hours ago / predictions older than
fixtures" warning prevents betting on dead numbers. Files: `model/fetch_odds.py`
(record `odds_fetched_at`), `site/src/lib/data.ts`, `site/src/pages/index.astro`.
Effort: **S/M**.

### M4 — No settled-results backfill, so P/L can never populate
Nothing pulls final scores into `fixtures.json` (`status` is `SCHEDULED` for all
104, scores all null) and nothing settles bets (computes `result`/`pnl` from
score + selection). Both `bankrollStats` and the whole P/L premise are inert
until this exists. Add a results fetcher + a `settle.py` that grades open bets.
Files: new `model/fetch_results.py`, new `model/settle.py`, `fixtures/fixtures.json`,
`bets/bets.json`. Effort: **M**.

### M5 — Missing dedicated "value bets / edges" view
The model computes edges per match but the site only surfaces the single top edge
on the dashboard and a per-match table on `[id].astro`. There is no aggregated,
sortable "all current edges above threshold" page — the primary actionable
artifact for the whole workflow. (UX agent owns styling; this item is the missing
data view/route.) Files: new `site/src/pages/edges.astro`, `site/src/lib/data.ts`.
Effort: **S/M**.

### M6 — Missing group standings / bracket views
`fixtures.json` carries full group rosters and stages, but there is no standings
table or knockout bracket. These are high-value for contextualizing bets
(qualification scenarios drive prices). Files: new pages under `site/src/pages/`,
`site/src/lib/data.ts`. Effort: **M**.

### M7 — Odds endpoint can't fetch BTTS, but the model and edge logic emit BTTS
`fetch_odds.py` notes the World Cup endpoint rejects `btts`, and the default
markets are `h2h,totals`. Yet `match_probabilities` returns BTTS probs and
`find_edges` will compare them against any `btts_yes/no` odds that happen to be
present. This is dead/inconsistent surface area: either source BTTS odds another
way or drop BTTS from the edge set to avoid implying a tradeable signal. Files:
`model/fetch_odds.py`, `model/predict.py`. Effort: **S**.

### M8 — Knockout placeholder filtering is fragile
`predict.py` skips knockout fixtures whose teams are placeholders via two
ad-hoc regexes (`t.startswith(("W","L"))...` and `re.match(r"^[123]", t)`).
A real team starting with a digit-like token or a differently-formatted
placeholder would slip through or be wrongly excluded. A real team name should
never be a placeholder; key off `stage != GROUP` + an explicit placeholder marker
in the fixture instead. Files: `model/predict.py`, `model/parse_fixtures.py`.
Effort: **S**.

---

## LOW impact

### L1 — `EloTable.update` reads canonical names but writes raw keys
`update()` does `self.ratings[home] = self.get(home) + delta` — `get()` applies
`canonical()` but the write uses the raw `home`/`away` string. Benign today
(training CSV names are already canonical and `NAME_ALIASES` only maps fixture
spellings) but a latent split-key bug if an alias ever appears in training data.
Write to the canonical key. Files: `model/elo.py`. Effort: **S**.

### L2 — `.env` is committed/tracked in the working tree
`.env` exists in the repo root alongside `.env.example`. It is gitignored, but its
presence in the tree is a footgun for accidental commits of the Odds API key.
Confirm it is not tracked and consider documenting key rotation. Files: `.env`,
`.gitignore`. Effort: **S**.

### L3 — Hardcoded calibration constants with no provenance
`K`, `HOME_ADV`, `GOALS_BASELINE`, `ELO_TO_GOAL_DIFF` are magic numbers the
docstring admits are "intentionally simple — tune... once we have the dataset."
They were never tuned. Tie them to the backtest (H3) and move to a config block
or fitted output. Files: `model/elo.py`. Effort: **S** (config) / folds into H3.

### L4 — `VENUE_COUNTRY` map is a hardcoded subset of host venues
`predict.py` hardcodes ~16 venue→country strings to decide home advantage; any
venue spelling drift silently makes a host match "neutral." Derive host status
from a fixtures field or the groups data rather than string-matching venues.
Files: `model/predict.py`. Effort: **S**.

### L5 — No model uncertainty / interval surfaced
Predictions are point probabilities with no confidence interval, despite small/
noisy rating samples for minor nations. Even a coarse rating-count or
recent-matches-played indicator would flag low-confidence predictions (e.g.
debutant/low-cap teams). Files: `model/predict.py`, match page. Effort: **M**.

### L6 — No reproducibility pinning / data provenance
`requirements.txt` uses `>=` ranges (numpy/pandas/scipy/requests) with no lock
file; the training CSV is gitignored with only a prose pointer to a Kaggle
dataset, so `ratings.json` is not reproducible from the repo. Pin versions and
record the dataset snapshot/date used. Files: `model/requirements.txt`,
`model/data/`, `README.md`. Effort: **S**.

### L7 — Repeated data-loading boilerplate / weak typing on the site
`loadFixtures/loadBets/loadPredictions` re-read JSON per call with `unknown`
fallbacks and no validation against the schemas. A single typed loader that
zod-validates against `bets/schema.json` would catch malformed bet entries at
build time. Files: `site/src/lib/data.ts`. Effort: **S/M**.

### L8 — UX notes (handed to the frontend agent, not detailed here)
Brief: no mobile/responsive handling on the fixed `cols-3/cols-4` grids; no
empty-state guidance beyond plain text; no sorting/filtering on the matches and
bets tables; date strings shown raw in UTC. Flagged for the UX owner. Files:
`site/src/layouts/Base.astro`, `site/src/pages/*`. Effort: **M** (UX-owned).
