# Closing-odds capture — runbook

**Why this is the #1 ops task.** The closing line (the last odds before kickoff) is
the sharp benchmark CLV is measured against. The project's whole credibility moat is
the **audited CLV record**, and it stays EMPTY until closing odds are captured on real
matchdays. The capture is *time-built and uncopyable retroactively* — if you don't
capture the June 11 openers, that data is gone for good. Start day one.

> ⚠️ Capture closing odds **before logging any bets you'll grade on CLV** — and note
> that some current model edges still reflect known biases (see backlog TASK-045/048
> follow-ups), so a too-early bet log can pollute the first CLV sample.

## What's already built

- `model/fetch_odds.py --closing` snapshots `closing_odds` (consensus + best-of-book)
  onto each fixture near kickoff, leaving the live `odds` untouched.
- `model/capture_closing.py` is a **quota-aware wrapper**: run it as often as you like;
  it spends an Odds API request **only** when a SCHEDULED match is within
  `--within-hours` of kickoff AND hasn't been captured in the last `--min-refresh-mins`.
  Otherwise it exits without calling the API. One call captures every near-kickoff
  fixture at once.
- `scripts/capture-closing.ps1` wraps that with logging for Task Scheduler.

## Quota math (free tier ≈ 500 requests/month)

Hourly scheduling is safe: capture only fires when a match is within 3h of kickoff and
not freshly captured. WC kickoffs cluster into a handful of windows per day, so this is
well under quota for the whole tournament. Check remaining quota in the
`fetch_odds.py` output (`x-requests-remaining`).

## Option A — manual (simplest, fine if you're around at kickoffs)

```powershell
# See what's coming and what's already captured:
python model/capture_closing.py --plan

# A few hours before a kickoff wave, capture (spends a call only if due):
python model/capture_closing.py

# Preview without calling the API:
python model/capture_closing.py --dry-run
```

## Option B — automated (set-and-forget, recommended for the tournament)

Register the wrapper to run **hourly** via Windows Task Scheduler. Run this once in a
terminal (it creates a scheduled task; you'll only need to do it a single time):

```powershell
schtasks /Create /TN "soccer26-closing-odds" /SC HOURLY /F `
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File `"$HOME\projects\soccer26\scripts\capture-closing.ps1`""
```

Then:

```powershell
schtasks /Run    /TN "soccer26-closing-odds"   # test it now
schtasks /Query  /TN "soccer26-closing-odds"   # confirm it's registered
# ... after the tournament:
schtasks /Delete /TN "soccer26-closing-odds" /F
```

Captures + skips are appended to `closing-capture.log` at the repo root, so you can
audit exactly what was grabbed and when.

## Verifying captures

```powershell
# Shows each upcoming match and whether closing_odds was captured (with timestamp):
python model/capture_closing.py --plan
```

`closing_odds` lands on each fixture in `fixtures/fixtures.json`; `model/clv.py` then
measures each settled bet's taken price against the de-vigged closing consensus.

## Tuning

| flag | default | meaning |
|---|---|---|
| `--within-hours` | 3 | start capturing once kickoff is this close |
| `--grace-mins` | 20 | keep capturing up to N min after kickoff (last line) |
| `--min-refresh-mins` | 30 | skip a fixture captured within this window (saves quota) |

---

## During matches — results + live mode

The site is static, but **live scores update without a rebuild** via a small
`site/public/data/live.json` the dashboard polls (TASK-019). On matchdays, run the
results loop on a cadence (e.g. every 5–10 min while games are on):

```powershell
python model/fetch_results.py    # pulls completed/in-progress scores -> fixtures.json (status LIVE/FINISHED)
python model/publish_live.py     # emits public/data/live.json for the dashboard poller
python model/settle.py           # grades FINISHED bets (never LIVE — see TASK-053)
```

`fetch_results.py` uses the scores endpoint (counts against the same ~500/mo quota,
so don't poll faster than the matches change). The dashboard's `.md-row`s pick up
LIVE/FT scores from `live.json` every 60s; it's a no-op when nothing is in play.

## After a fresh odds pull — what changed?

```powershell
python model/predict.py          # re-price edges off the new odds
python model/check_edges.py      # report edges that APPEARED / GONE / MOVED vs last run (TASK-020)
```

`check_edges.py` is a pure local diff (no API). The dashboard also shows a freshness
badge — **"⚠ odds moved since — refresh"** — whenever a book quotes a price newer than
the current prediction set, so you know when to re-run `predict.py` (TASK-029).
