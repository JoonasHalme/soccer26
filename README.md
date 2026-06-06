# soccer 26

A **transparent, auditable** FIFA World Cup 2026 model. One Elo + Poisson engine,
calibrated on thousands of historical internationals and open to inspection: every
probability is shown, every "value edge" is the model genuinely disagreeing with
the *de-vigged* market, and every bet is logged and graded against the closing
line (CLV). The goal isn't tips — it's to settle the profit/loss question with
data, honestly, at the end of the tournament.

Honest framing: the model is well-calibrated and beats a naive baseline (see
`/calibration`), but "beats the market" is a higher bar it has **not** yet proven
— that's what the public CLV track record is for.

## Layout

```
site/        Astro site (dashboard, matches, bet log)
model/       Python: Elo + Poisson model, prediction generator
bets/        bets.json (source of truth for P/L) + JSON schema
fixtures/    fixtures.json — 104 World Cup 2026 matches
```

## First-time setup

```
cd site
npm install
cd ..
pip install -r model/requirements.txt
```

## Weekend workflow

Run each step from the repo root, in order:

```
python model/fetch_fixtures.py             # download cup.txt + cup_finals.txt AND parse into fixtures/fixtures.json
python model/train_ratings.py              # train Elo on historical internationals -> model/data/ratings.json
python model/fetch_odds.py --markets h2h,totals   # merge consensus odds into fixtures.json (uses ODDS_API_KEY; skip to reuse existing odds)
python model/predict.py                    # write site/public/data/predictions.json (de-vigged edges) + tamper-evident predictions.hash.json
python model/fetch_news.py                 # pull football RSS, tag to teams -> site/public/data/news.json (FREE, no key)
python model/export_calibration.py         # walk-forward backtest -> site/public/data/calibration.json (drives the /calibration page)
python model/validate_bets.py              # enforce the >5%-edge-or-rationale discipline on bets/bets.json
cd site && npm run dev                     # http://localhost:4321
```

`predict.py` now also enriches each edge with the **best book price** (line
shopping) and its realisable EV. The `/edges` page lists every value edge across
all fixtures, priced against the best available book, with a fractional-Kelly
stake suggestion. To log a bet straight from an edge (pre-filled + validated):

```
python model/add_bet.py --edge m-007:HOME --odds 2.15   # appends a schema-valid bet; --stake defaults to ¼-Kelly; --dry-run to preview
```

### Matchday: results, settlement and CLV

Once matches start (June 11), run these — each is independently runnable and safe
to run anytime (they no-op cleanly while results/bets are empty), **in this order**:

```
python model/fetch_odds.py --closing       # CLOSING-line snapshot: writes match['closing_odds'] for fixtures at/near kickoff. Run shortly BEFORE kickoff so it captures the sharpest price (uses ODDS_API_KEY).
python model/fetch_results.py              # pull final/live scores into fixtures.json match.score + status (The Odds API /scores; daysFrom=3). Prints "0 completed matches" until games are played.
python model/settle.py                     # grade every bet whose match has a final score -> result + pnl + settled_at. Idempotent; re-running never double-counts.
python model/clv.py                        # de-vig each settled bet's CLOSING market the same way predict.py does, store closing_fair_prob + clv_pct, and report beat-rate / avg CLV.
python model/validate_bets.py              # re-check discipline + report model-vs-manual P/L now that bets are settled.
```

Cadence: snapshot the **close** just before each kickoff (`fetch_odds.py
--closing`), then after the match `fetch_results.py` → `settle.py` → `clv.py`.
The bets page (`/bets`) then shows settled P/L, ROI, and the CLV scoreboard
(average CLV, beat-rate, P/L split by source and market) — all of which stay at
empty/zero states until real results and bets exist, then populate automatically.

**Tamper-evident predictions.** `predict.py` writes a SHA-256 of the exact
`predictions.json` bytes (which embed `generated_at`) to a sibling
`predictions.hash.json`. Keep that hash; re-hashing the file later must reproduce
it, so a prediction can be proven to predate a kickoff.

Notes:
- `fetch_fixtures.py` now downloads **both** source files (group stage `cup.txt`
  and knockouts `cup_finals.txt`) and invokes `parse_fixtures.py` itself, so it
  produces a complete `fixtures.json` in one command. Use `--no-parse` to
  download only. Re-parsing is non-destructive: previously fetched odds are
  carried forward by (date, teams).
- `fetch_odds.py` is the only step that calls an external API (The Odds API free
  tier, ~500 req/month). One call per matchday is plenty — skip it to reuse the
  odds already merged into `fixtures.json`.
- The World Cup odds endpoint only serves `h2h` and `totals` (no BTTS), so BTTS
  edges are simply never produced (the de-vig step skips any market that isn't
  fully priced).
- `fetch_news.py` is **free and key-less** — it reads three public football RSS
  feeds (BBC Sport, The Guardian, ESPN) with the Python stdlib, tags each
  headline to the World Cup teams it mentions, dedupes and writes
  `site/public/data/news.json`. If a feed is down it is skipped and the others
  still produce output. The dashboard shows the latest items and each match page
  shows news tagged to its two teams.

## Tests

```
python -m pytest tests/ -q
```

Covers the model math (de-vig normalisation sums to 1, matchup-varying expected
goals, Elo/Poisson + Dixon-Coles sanity) and the bet-discipline validator.

## The discipline

A bet is only worth logging when the model says there is a real edge
(`model_edge_pct > 5%`), or when you write down explicit rationale for
overriding the model. Every bet is appended to `bets/bets.json`.

This is now **enforced**, not just documented: `python model/validate_bets.py`
fails (non-zero exit) on any bet that lacks a >5% model edge *and* a written
rationale, checks each bet against `bets/schema.json`, verifies `match_id`
resolves against `fixtures.json`, and reports model-vs-manual hit-rate / ROI over
settled bets. Run it as the last step of the workflow (or in CI).

### How edges are computed (de-vigged)

`predict.py` does **not** compare the model to a raw `1/odds` implied
probability — that still contains the bookmaker overround (the vig), which
distorts every edge. Instead it **de-vigs each market**: it normalises the
implied probabilities of a market's full set of outcomes (1X2 as a trio, O/U as a
pair) so they sum to 1, then measures `edge = model_prob − fair_prob`. Only
selections clearing the 5% threshold are surfaced. A market that isn't fully
priced is skipped (no recoverable overround).

## Data sources to wire up

- Historical international results — drop a CSV at `model/data/internationals.csv`
  (Kaggle "International football results" works).
- 2026 fixtures — `model/fetch_fixtures.py` downloads `model/data/cup.txt`
  (groups) and `model/data/cup_finals.txt` (knockouts) from openfootball and runs
  `model/parse_fixtures.py` to build `fixtures.json` end-to-end.
- Odds — either entered manually as part of each match record or fetched from a
  sportsbook API. `model/predict.py` already reads `match.odds` if present.
