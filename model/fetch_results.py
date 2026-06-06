"""Populate fixtures.json `match.score` and `status` from The Odds API scores.

GET /v4/sports/soccer_fifa_world_cup/scores?daysFrom=N returns completed AND
in-progress events with their current scores. We map each event to our fixture
by the same team-name normalization + same-day kickoff used by fetch_odds.py,
and write the score onto `match.score = {home, away}` (the single source of truth
the standings + settlement features read).

This is SAFE to run anytime. Since no World Cup games have been played yet, the
endpoint returns zero completed events and the script writes nothing destructive
(prints "0 completed matches"). It only ever touches matches the API reports a
score for; it never blanks an existing score it can't see.

Usage:
    python model/fetch_results.py                 # daysFrom=3 (API max for free tier window)
    python model/fetch_results.py --days-from 1
    python model/fetch_results.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# Reuse the env loader, key handling, normalization and matching from fetch_odds.
from fetch_odds import (
    BASE,
    FIXTURES,
    ROOT,
    SPORT_KEY,
    _load_env,
    find_match,
    normalize,
)

import os


def _parse_scores(event: dict) -> tuple[int, int] | None:
    """Extract (home_goals, away_goals) from a scores-endpoint event.

    The API returns `scores: [{name, score}, ...]` keyed by team NAME. Returns
    None if either side's score is missing or non-numeric (e.g. just kicked off
    with no goals reported yet)."""
    home_team = normalize(event.get("home_team", ""))
    away_team = normalize(event.get("away_team", ""))
    scores = event.get("scores")
    if not scores:
        return None
    by_name: dict[str, str] = {}
    for s in scores:
        name = normalize(s.get("name", ""))
        by_name[name] = s.get("score")
    h, a = by_name.get(home_team), by_name.get(away_team)
    try:
        return int(h), int(a)
    except (TypeError, ValueError):
        return None


def apply_results(fixtures: dict, events: list[dict]) -> list[dict]:
    """Merge completed/live scores into fixtures in-place. Returns change records."""
    matches = fixtures.get("matches", [])
    changes: list[dict] = []
    for event in events:
        match = find_match(matches, event.get("home_team", ""),
                           event.get("away_team", ""), event.get("commence_time", ""))
        if not match:
            continue
        parsed = _parse_scores(event)
        if parsed is None:
            continue
        hs, as_ = parsed
        completed = bool(event.get("completed"))
        new_status = "FINISHED" if completed else "LIVE"
        old_score = match.get("score") or {}
        if (old_score.get("home") == hs and old_score.get("away") == as_
                and match.get("status") == new_status):
            continue  # no change
        before = {"score": match.get("score"), "status": match.get("status")}
        match["score"] = {"home": hs, "away": as_}
        match["status"] = new_status
        changes.append({"id": match.get("id"), "before": before,
                        "after": {"score": match["score"], "status": new_status}})
    return changes


def _has_active_match(window_hours: float) -> bool:
    """True if any fixture is LIVE or kicked off within the last `window_hours` (and
    isn't already FINISHED) — i.e. there are fresh scores worth an API call. Lets a
    scheduled job poll only when matches are actually on, staying within quota."""
    try:
        fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True  # can't tell -> don't block the call
    now = datetime.now(timezone.utc)
    lo = now - timedelta(hours=window_hours)
    for m in fixtures.get("matches", []):
        if m.get("status") == "LIVE":
            return True
        if m.get("status") == "FINISHED":
            continue
        ko = m.get("kickoff")
        try:
            t = datetime.fromisoformat((ko or "").replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if lo <= t <= now:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-from", type=int, default=3,
                        help="How many days back to fetch completed scores (1-3).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change; write nothing.")
    parser.add_argument("--only-if-active", action="store_true",
                        help="exit 0 WITHOUT calling the API unless a match is LIVE or "
                             "kicked off within --active-window-hours (keeps scheduled runs in quota)")
    parser.add_argument("--active-window-hours", type=float, default=3.0)
    args = parser.parse_args()

    if args.only_if_active and not _has_active_match(args.active_window_hours):
        print(f"No match LIVE or kicked off within {args.active_window_hours:g}h — "
              "skipping the scores API call (saves quota).")
        return 0

    _load_env()
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit("ODDS_API_KEY not set (see .env / fetch_odds.py).")

    url = f"{BASE}/sports/{SPORT_KEY}/scores"
    params = {"apiKey": api_key, "daysFrom": max(1, min(3, args.days_from))}
    print(f"Fetching scores from {url} (daysFrom={params['daysFrom']})")
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        sys.exit(f"Scores API returned {resp.status_code}: {resp.text[:200]}")
    events = resp.json()
    remaining = resp.headers.get("x-requests-remaining", "?")
    completed = [e for e in events if e.get("completed")]
    live = [e for e in events if not e.get("completed") and e.get("scores")]
    print(f"  {len(completed)} completed match(es), {len(live)} live. "
          f"Requests remaining this month: {remaining}")

    if not events:
        print("  0 events returned — nothing to write (no games in window yet).")
        return 0

    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    changes = apply_results(fixtures, events)

    if not changes:
        print("  0 fixtures updated (scores unchanged or no fixture match).")
        return 0

    for c in changes:
        a = c["after"]
        print(f"  {c['id']}: -> {a['score']['home']}-{a['score']['away']} ({a['status']})")

    if args.dry_run:
        print(f"[dry-run] would update {len(changes)} fixture(s); no file written.")
        return 0

    FIXTURES.write_text(json.dumps(fixtures, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Updated {len(changes)} fixture(s) in {FIXTURES.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
