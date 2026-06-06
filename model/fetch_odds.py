"""Pull current odds from The Odds API and merge into fixtures/fixtures.json.

Set the API key in environment variable ODDS_API_KEY (or in `.env` at repo root).
Free tier at https://the-odds-api.com gives ~500 requests/month — one call per
matchday is plenty.

Usage:
    python model/fetch_odds.py                # default: head-to-head
    python model/fetch_odds.py --markets h2h,totals
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures" / "fixtures.json"
ENV_FILE = ROOT / ".env"
SPORT_KEY = "soccer_fifa_world_cup"
BASE = "https://api.the-odds-api.com/v4"


def _load_env() -> None:
    """Tiny .env loader so we don't pull in python-dotenv."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


# Map The Odds API's canonical names to our fixtures.json names.
ODDS_TO_FIXTURE: dict[str, str] = {
    "South Korea": "South Korea",
    "Korea Republic": "South Korea",
    "USA": "USA",
    "United States": "USA",
    "Czechia": "Czech Republic",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Iran": "Iran",
    "IR Iran": "Iran",
    "Ivory Coast": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "Cape Verde": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "DR Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Curacao": "Curaçao",
}


def normalize(team: str) -> str:
    return ODDS_TO_FIXTURE.get(team, team)


def _parse_kickoff(kickoff: str | None) -> datetime | None:
    """Parse an ISO kickoff string (e.g. '2026-06-11T19:00:00Z') to aware UTC."""
    if not kickoff:
        return None
    try:
        return datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
    except ValueError:
        return None


def _consensus(values: list[float]) -> float | None:
    if not values:
        return None
    return round(statistics.median(values), 2)


def aggregate_event(event: dict, markets: list[str]) -> dict[str, float]:
    """Average decimal odds across sportsbooks. Median is the consensus we use."""
    home_team = normalize(event["home_team"])
    away_team = normalize(event["away_team"])
    odds: dict[str, list[float]] = {
        "home": [], "draw": [], "away": [],
        "over_2_5": [], "under_2_5": [],
        "btts_yes": [], "btts_no": [],
    }
    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            key = market["key"]
            if key == "h2h":
                for outcome in market["outcomes"]:
                    name = normalize(outcome["name"])
                    price = outcome["price"]
                    if name == home_team:
                        odds["home"].append(price)
                    elif name == away_team:
                        odds["away"].append(price)
                    elif name.lower() == "draw":
                        odds["draw"].append(price)
            elif key == "totals":
                for outcome in market["outcomes"]:
                    if abs(outcome.get("point", 0) - 2.5) < 0.01:
                        if outcome["name"] == "Over":
                            odds["over_2_5"].append(outcome["price"])
                        elif outcome["name"] == "Under":
                            odds["under_2_5"].append(outcome["price"])
            elif key == "btts":
                for outcome in market["outcomes"]:
                    if outcome["name"] == "Yes":
                        odds["btts_yes"].append(outcome["price"])
                    elif outcome["name"] == "No":
                        odds["btts_no"].append(outcome["price"])
    return {k: c for k, v in odds.items() if (c := _consensus(v)) is not None}


def book_odds(event: dict) -> list[dict]:
    """Extract per-bookmaker odds for line-shopping.

    Returns one entry per sportsbook with its own h2h (home/draw/away) and
    totals (over_2_5/under_2_5) decimal prices, using the same team
    normalization as the consensus aggregation. Sorted by book title.
    """
    home_team = normalize(event["home_team"])
    away_team = normalize(event["away_team"])
    books: list[dict] = []
    for bookmaker in event.get("bookmakers", []):
        h2h: dict[str, float] = {}
        totals: dict[str, float] = {}
        for market in bookmaker.get("markets", []):
            key = market["key"]
            if key == "h2h":
                for outcome in market["outcomes"]:
                    name = normalize(outcome["name"])
                    price = outcome["price"]
                    if name == home_team:
                        h2h["home"] = price
                    elif name == away_team:
                        h2h["away"] = price
                    elif name.lower() == "draw":
                        h2h["draw"] = price
            elif key == "totals":
                for outcome in market["outcomes"]:
                    if abs(outcome.get("point", 0) - 2.5) < 0.01:
                        if outcome["name"] == "Over":
                            totals["over_2_5"] = outcome["price"]
                        elif outcome["name"] == "Under":
                            totals["under_2_5"] = outcome["price"]
        # Skip books that returned neither market for this event.
        if not h2h and not totals:
            continue
        books.append({
            "key": bookmaker.get("key", ""),
            "title": bookmaker.get("title", bookmaker.get("key", "")),
            "last_update": bookmaker.get("last_update", ""),
            "h2h": h2h,
            "totals": totals,
        })
    books.sort(key=lambda b: b["title"].lower())
    return books


def best_book_prices(books: list[dict]) -> dict[str, dict]:
    """Best (highest) decimal price per outcome across books, with the book name.

    Used for the closing snapshot's best-of-book line so CLV can optionally be
    measured against the sharpest available close, not just the consensus.
    """
    outcomes = [("home", "h2h"), ("draw", "h2h"), ("away", "h2h"),
                ("over_2_5", "totals"), ("under_2_5", "totals")]
    best: dict[str, dict] = {}
    for b in books:
        for key, group in outcomes:
            price = b.get(group, {}).get(key)
            if not isinstance(price, (int, float)):
                continue
            if key not in best or price > best[key]["price"]:
                best[key] = {"price": price, "book": b.get("title", "")}
    return best


def find_match(fixtures: list[dict], home: str, away: str, commence: str) -> dict | None:
    """Match The Odds API event to our fixture by teams + same-day kickoff."""
    home = normalize(home)
    away = normalize(away)
    day = commence[:10]
    for m in fixtures:
        if m.get("kickoff", "")[:10] != day:
            continue
        if {m["home"], m["away"]} == {home, away}:
            return m
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markets", default="h2h,totals",
                        help="Comma-separated market keys (the World Cup endpoint "
                             "rejects 'btts' — h2h,totals are the supported ones)")
    parser.add_argument("--regions", default="eu,uk",
                        help="Region groups (controls which bookmakers)")
    parser.add_argument("--closing", action="store_true",
                        help="Snapshot the CLOSING line: write match['closing_odds'] "
                             "(consensus + best-of-book) for fixtures at/after kickoff "
                             "instead of overwriting the live match['odds']. Run shortly "
                             "before/after kickoff to capture the close for CLV.")
    parser.add_argument("--closing-window-hours", type=float, default=2.0,
                        help="With --closing, also snapshot fixtures kicking off within "
                             "this many hours (so you can capture just before kickoff).")
    args = parser.parse_args()

    _load_env()
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        sys.exit(
            "ODDS_API_KEY not set. Sign up at https://the-odds-api.com and add\n"
            f"  ODDS_API_KEY=your_key_here\n"
            f"to {ENV_FILE.relative_to(ROOT)}"
        )

    url = f"{BASE}/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": api_key,
        "regions": args.regions,
        "markets": args.markets,
        "oddsFormat": "decimal",
    }
    print(f"Fetching odds from {url}")
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        sys.exit(f"Odds API returned {resp.status_code}: {resp.text[:200]}")
    events = resp.json()
    remaining = resp.headers.get("x-requests-remaining", "?")
    print(f"  Got {len(events)} events. Requests remaining this month: {remaining}")

    fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
    matches = fx["matches"]
    matched = 0
    book_counts: list[int] = []
    now = datetime.now(timezone.utc)
    window = timedelta(hours=args.closing_window_hours)
    skipped_not_near = 0
    for event in events:
        match = find_match(matches, event["home_team"], event["away_team"], event["commence_time"])
        if not match:
            continue
        consensus = aggregate_event(event, args.markets.split(","))
        books = book_odds(event)

        if args.closing:
            # CLOSING snapshot: only capture fixtures at/after kickoff (or within
            # the pre-kickoff window). The LAST snapshot before a match starts is
            # its closing line — so re-running this near kickoff keeps overwriting
            # closing_odds with progressively-closer prices until the match begins.
            ko = _parse_kickoff(match.get("kickoff"))
            near = ko is not None and (now >= ko - window)
            if not near:
                skipped_not_near += 1
                continue
            match["closing_odds"] = {
                "captured_at": now.isoformat(),
                "consensus": consensus,
                "best_book": best_book_prices(books),
            }
            matched += 1
            book_counts.append(len(books))
            continue

        # Default (live) behaviour — unchanged; predict.py depends on this shape.
        match["odds"] = consensus
        match["books"] = books
        book_counts.append(len(books))
        matched += 1
    FIXTURES.write_text(json.dumps(fx, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.closing:
        print(f"  Snapshotted closing_odds onto {matched} fixture(s) "
              f"(skipped {skipped_not_near} not within {args.closing_window_hours}h of kickoff).")
    else:
        print(f"  Merged odds into {matched} fixtures.")
    if book_counts:
        book_counts.sort()
        print(
            f"  Books per matched fixture — min {book_counts[0]}, "
            f"median {int(statistics.median(book_counts))}, max {book_counts[-1]}."
        )


if __name__ == "__main__":
    main()
