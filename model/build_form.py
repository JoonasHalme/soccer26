"""Build each WC team's recent international form ("Road to the World Cup").

Reads the same martj42 results CSV the ratings train on and emits a small
`site/public/data/form.json` of each qualified team's last few internationals —
results, opponents, the competition, and the IMPORTANCE WEIGHT the model gives
that match (the eloratings-style weight from elo.match_importance, so a warm-up
friendly is openly shown at 0.5). Display-only; this does NOT feed the model
(the CSV already does, weighted). Keyed by the fixtures team name (e.g. "USA")
so the team pages can look it up directly, while matching the CSV via canonical().

Run: python model/build_form.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from elo import (  # noqa: E402
    EloTable, canonical, expected_goals, match_importance, match_probabilities,
)

CSV = ROOT / "model" / "data" / "internationals.csv"
CONFEDS = ROOT / "model" / "data" / "confederations.json"
OUT = ROOT / "site" / "public" / "data" / "form.json"

N_RECENT = 6  # internationals shown per team (form string uses the last 5)
FEED_SINCE = "2026-05-01"  # the pre-tournament run-in shown on the Road-to-the-WC feed


def _is_tournament(comp: str) -> bool:
    """True for an actual World Cup *finals* match (martj42 tournament == 'FIFA World
    Cup'), as opposed to a warm-up friendly or a qualifier ('FIFA World Cup
    qualification'). Once the tournament kicks off these stop being part of the
    pre-tournament run-in and are shown separately."""
    return comp.strip().lower() == "fifa world cup"


def _wc_teams() -> list[str]:
    data = json.loads(CONFEDS.read_text(encoding="utf-8"))
    return [k for k in data if not k.startswith("_")]


def _is_neutral(val) -> bool:
    return str(val).strip().lower() in {"true", "1", "yes", "t"}


def walkforward_predictions(df: pd.DataFrame, wc_canon: set[str]) -> dict:
    """Replay every result forward (importance-weighted, exactly as the model trains)
    and capture each WC-involving match's PRE-match 1X2 prediction.

    The prediction for match i is computed from ratings built ONLY from matches
    strictly before it, then the ratings are updated — so these are honest, no-
    hindsight calls (the same walk-forward discipline as backtest.py). Keyed by
    (date, home, away); values are home-perspective (p_home, p_draw, p_away)."""
    played = df.dropna(subset=["home_score", "away_score"]).sort_values("date")
    table = EloTable()
    preds: dict[tuple, tuple] = {}
    for r in played.itertuples(index=False):
        h, a = r.home_team, r.away_team
        neutral = _is_neutral(getattr(r, "neutral", ""))
        if h in wc_canon or a in wc_canon:
            p = match_probabilities(*expected_goals(table.get(h), table.get(a), neutral=neutral))
            preds[(pd.Timestamp(r.date).date().isoformat(), h, a)] = (
                round(p["home"], 4), round(p["draw"], 4), round(p["away"], 4))
        table.update(h, a, int(r.home_score), int(r.away_score), neutral=neutral,
                     importance=match_importance(str(getattr(r, "tournament", "") or "")))
    return preds


def _model_view(pred: tuple, home: bool, res: str) -> dict:
    """Turn a home-perspective (p_home,p_draw,p_away) into the team's own
    perspective + its pre-match pick and whether that pick was correct."""
    ph, pd_, pa = pred
    pw, pl = (ph, pa) if home else (pa, ph)   # win/loss flip with venue; draw is shared
    pick = "W" if (pw >= pd_ and pw >= pl) else ("D" if pd_ >= pl else "L")
    return {
        "pw": round(pw, 3), "pd": round(pd_, 3), "pl": round(pl, 3),
        "pick": pick,
        "correct": pick == res,
        "p_actual": round({"W": pw, "D": pd_, "L": pl}[res], 3),
    }


def recent_feed(df: pd.DataFrame, preds: dict, teams: list[str], since: str = FEED_SINCE) -> list[dict]:
    """A deduped, most-recent-first feed of every WC-involving match since `since`,
    each with the model's PRE-match (no-hindsight) home-perspective call — the
    "Road to the World Cup" warm-up scoreboard. Names are mapped back to the
    fixtures spelling (e.g. United States -> USA) for display."""
    wc_canon = {canonical(t) for t in teams}
    disp = {canonical(t): t for t in teams}            # canonical -> fixtures display name
    played = df.dropna(subset=["home_score", "away_score"]).sort_values("date")
    played = played[played["date"] >= pd.Timestamp(since)]
    feed: list[dict] = []
    for r in played.itertuples(index=False):
        h, a = r.home_team, r.away_team
        if h not in wc_canon and a not in wc_canon:
            continue
        pr = preds.get((pd.Timestamp(r.date).date().isoformat(), h, a))
        if not pr:
            continue
        ph, pd_, pa = pr
        hs, as_ = int(r.home_score), int(r.away_score)
        actual = "H" if hs > as_ else ("D" if hs == as_ else "A")
        pick = "H" if (ph >= pd_ and ph >= pa) else ("D" if pd_ >= pa else "A")
        tour = str(getattr(r, "tournament", "") or "")
        feed.append({
            "date": pd.Timestamp(r.date).date().isoformat(),
            "home": disp.get(h, h),
            "away": disp.get(a, a),
            "hs": hs, "as": as_,
            "comp": tour,
            "friendly": "friendly" in tour.lower(),
            "tournament": _is_tournament(tour),
            "weight": round(match_importance(tour), 2),
            "neutral": _is_neutral(getattr(r, "neutral", "")),
            "model": {
                "ph": round(ph, 3), "pd": round(pd_, 3), "pa": round(pa, 3),
                "pick": pick, "correct": pick == actual,
                "p_actual": round({"H": ph, "D": pd_, "A": pa}[actual], 3),
            },
        })
    feed.reverse()  # most-recent first
    return feed


def build(df: pd.DataFrame, teams: list[str], preds: dict | None = None) -> dict:
    played = df.dropna(subset=["home_score", "away_score"]).copy()
    played = played.sort_values("date")
    wc_canon = {canonical(t) for t in teams}
    disp = {canonical(t): t for t in teams}            # canonical -> fixtures display name
    if preds is None:
        preds = walkforward_predictions(df, wc_canon)
    out: dict[str, dict] = {}

    for team in teams:
        cname = canonical(team)
        mine = played[(played["home_team"] == cname) | (played["away_team"] == cname)]
        if mine.empty:
            continue
        recent = mine.tail(N_RECENT).iloc[::-1]  # most-recent first

        matches = []
        for r in recent.itertuples(index=False):
            home = r.home_team == cname
            gf = int(r.home_score if home else r.away_score)
            ga = int(r.away_score if home else r.home_score)
            res = "W" if gf > ga else ("D" if gf == ga else "L")
            opp = r.away_team if home else r.home_team
            tour = str(getattr(r, "tournament", "") or "")
            date_iso = pd.Timestamp(r.date).date().isoformat()
            m = {
                "date": date_iso,
                "opp": disp.get(opp, opp),
                "gf": gf,
                "ga": ga,
                "res": res,
                "comp": tour,
                "friendly": "friendly" in tour.lower(),
                "weight": round(match_importance(tour), 2),
                "home": bool(home),
                "neutral": _is_neutral(getattr(r, "neutral", "")),
            }
            pred = preds.get((date_iso, r.home_team, r.away_team))
            if pred:
                m["model"] = _model_view(pred, home, res)
            matches.append(m)

        graded = [m for m in matches if "model" in m]
        out[team] = {
            # form string oldest->newest (reads left-to-right like a results run)
            "form": "".join(m["res"] for m in reversed(matches[:5])),
            "matches": matches,
            # the model's pre-match hit-rate over the shown games (no hindsight)
            "record": {"correct": sum(m["model"]["correct"] for m in graded), "total": len(graded)},
        }
    return out


def main() -> None:
    df = pd.read_csv(CSV, parse_dates=["date"])
    teams = _wc_teams()
    wc_canon = {canonical(t) for t in teams}
    preds = walkforward_predictions(df, wc_canon)            # compute once, share
    teams_form = build(df, teams, preds)
    all_feed = recent_feed(df, preds, teams)
    # Split the actual World Cup *finals* games out of the pre-tournament run-in:
    # once the tournament starts they're real results, not warm-ups, so they get
    # their own section and don't pollute the warm-up track record / "all friendly"
    # framing. (Qualifiers stay in the run-in.)
    tournament = [m for m in all_feed if m.get("tournament")]
    runin = [m for m in all_feed if not m.get("tournament")]
    last_date = max(
        (m["date"] for t in teams_form.values() for m in t["matches"]),
        default=None,
    )
    runin_correct = sum(1 for m in runin if m["model"]["correct"])
    tour_correct = sum(1 for m in tournament if m["model"]["correct"])
    payload = {
        "_note": "Recent international form + pre-match model calls for each WC2026 team "
                 "(model/build_form.py). Display-only; 'weight' is the model's match-importance "
                 "weight, model calls are walk-forward (no hindsight).",
        "updated": last_date,
        "since": FEED_SINCE,
        # aggregate pre-match record over the pre-tournament run-in (the headline)
        "record": {"correct": runin_correct, "total": len(runin)},
        "recent": runin,
        # actual World Cup games so far, shown separately, with their own record
        "tournament": tournament,
        "tournament_record": {"correct": tour_correct, "total": len(tournament)},
        "teams": teams_form,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    n_matches = sum(len(t["matches"]) for t in teams_form.values())
    pct = round(100 * runin_correct / len(runin)) if runin else 0
    print(f"Wrote {OUT.relative_to(ROOT)} — {len(teams_form)} teams, {n_matches} team-matches; "
          f"run-in {len(runin)} games, model {runin_correct}/{len(runin)} ({pct}%); "
          f"tournament {len(tournament)} games, model {tour_correct}/{len(tournament)} "
          f"(through {last_date}).")


if __name__ == "__main__":
    main()
