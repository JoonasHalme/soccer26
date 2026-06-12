"""Quota-aware CLOSING-odds capture for World Cup CLV — the #1 ops task.

The closing line (the last odds before kickoff) is the sharp benchmark CLV is
measured against, and the audited CLV record — the project's whole moat — stays
EMPTY until this runs on real matchdays. `fetch_odds.py --closing` already snapshots
`closing_odds` for fixtures near kickoff, but The Odds API free tier is ~500
requests/month, so you can't just poll it every few minutes.

This wrapper makes capture SCHEDULABLE without burning quota. Run it as often as you
like (e.g. hourly via Windows Task Scheduler — see docs/closing-odds-runbook.md);
it spends an API call ONLY when a SCHEDULED match is within --within-hours of
kickoff AND hasn't had a closing snapshot in the last --min-refresh-mins. Otherwise
it exits 0 without touching the API. One call captures every near-kickoff fixture,
and each run inside the window refreshes the snapshot, so the LAST one before
kickoff is the closing line.

The window defaults to 6h (not 3h) on purpose: a closing line CANNOT be recovered
once kickoff passes, and scheduled runners (GitHub Actions crons especially) skip or
delay runs by multiple hours under load. A wider window gives ~6 hourly chances to
land a snapshot instead of 3 — so a missed run degrades to an hours-old line rather
than no line at all. It costs at most a few extra (1-credit) calls per matchday.

Usage:
    python model/capture_closing.py                 # capture if due (call only if needed)
    python model/capture_closing.py --dry-run       # report the plan; never calls the API
    python model/capture_closing.py --plan          # print the upcoming kickoff schedule and exit
    python model/capture_closing.py --within-hours 6 --min-refresh-mins 30
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures" / "fixtures.json"
FETCH = ROOT / "model" / "fetch_odds.py"


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@dataclass
class CapturePlan:
    """Result of deciding what to capture, with no side effects (so it's testable
    without the API). `actionable` drives whether an API call is spent."""
    due: list = field(default_factory=list)         # (kickoff, match) within the window
    actionable: list = field(default_factory=list)  # subset still needing a refresh
    upcoming: list = field(default_factory=list)     # next kickoffs (for --plan)

    @property
    def should_call(self) -> bool:
        return bool(self.actionable)


def capture_plan(matches: list[dict], now: datetime,
                 within_hours: float, grace_mins: float,
                 min_refresh_mins: float) -> CapturePlan:
    """Pure decision logic. A SCHEDULED match is DUE for a closing snapshot when now
    is within [kickoff - within_hours, kickoff + grace_mins]; it's ACTIONABLE unless
    its existing closing_odds was captured within the last min_refresh_mins (so we
    don't re-spend a request on a line we just grabbed)."""
    within = timedelta(hours=within_hours)
    grace = timedelta(minutes=grace_mins)
    refresh = timedelta(minutes=min_refresh_mins)

    sched = []
    for m in matches:
        if m.get("status") != "SCHEDULED":
            continue
        ko = _parse_iso(m.get("kickoff"))
        if ko is not None:
            sched.append((ko, m))
    sched.sort(key=lambda x: x[0])

    plan = CapturePlan()
    plan.upcoming = [(ko, m) for ko, m in sched if ko >= now - grace][:12]
    for ko, m in sched:
        if (ko - within) <= now <= (ko + grace):
            plan.due.append((ko, m))
            cap = _parse_iso((m.get("closing_odds") or {}).get("captured_at"))
            fresh = cap is not None and (now - cap) < refresh
            if not fresh:
                plan.actionable.append((ko, m))
    return plan


def main() -> None:
    ap = argparse.ArgumentParser(description="Quota-aware closing-odds capture")
    ap.add_argument("--within-hours", type=float, default=6.0,
                    help="capture a fixture's closing line once kickoff is this close "
                         "(default 6h — wide enough to survive a skipped/delayed scheduled run; "
                         "a closing line can't be recaptured after kickoff)")
    ap.add_argument("--grace-mins", type=float, default=20.0,
                    help="keep capturing up to this many minutes AFTER kickoff (last line)")
    ap.add_argument("--min-refresh-mins", type=float, default=30.0,
                    help="skip a fixture already captured within this many minutes (saves quota)")
    ap.add_argument("--regions", default="eu,uk", help="passed through to fetch_odds")
    ap.add_argument("--dry-run", action="store_true", help="report the plan; never call the API")
    ap.add_argument("--plan", action="store_true", help="print upcoming kickoffs and exit")
    args = ap.parse_args()

    fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    plan = capture_plan(fx.get("matches", []), now,
                        args.within_hours, args.grace_mins, args.min_refresh_mins)
    stamp = f"[{now:%Y-%m-%d %H:%M}Z]"

    if args.plan:
        print(f"{stamp} Next {len(plan.upcoming)} kickoffs (UTC):")
        for ko, m in plan.upcoming:
            cap = (m.get("closing_odds") or {}).get("captured_at")
            tail = f"  [closing captured {cap[:16]}Z]" if cap else ""
            print(f"  {ko:%Y-%m-%d %H:%M}  {m['home']} vs {m['away']}{tail}")
        return

    if not plan.due:
        print(f"{stamp} No match within {args.within_hours}h of kickoff — no API call.")
        return
    if not plan.actionable:
        print(f"{stamp} {len(plan.due)} match(es) near kickoff, all captured within "
              f"{args.min_refresh_mins:g}m — skipping (saves quota).")
        return

    print(f"{stamp} {len(plan.actionable)} match(es) due for a closing snapshot:")
    for ko, m in plan.actionable:
        print(f"    {ko:%H:%M}Z  {m['home']} vs {m['away']}")
    if args.dry_run:
        print("  --dry-run: NOT calling the API.")
        return

    # One request captures every fixture inside the window.
    cmd = [sys.executable, str(FETCH), "--closing",
           "--closing-window-hours", str(args.within_hours), "--regions", args.regions]
    print(f"  -> {' '.join(cmd)}")
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
