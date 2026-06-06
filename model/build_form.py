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

from elo import canonical, match_importance  # noqa: E402

CSV = ROOT / "model" / "data" / "internationals.csv"
CONFEDS = ROOT / "model" / "data" / "confederations.json"
OUT = ROOT / "site" / "public" / "data" / "form.json"

N_RECENT = 6  # internationals shown per team (form string uses the last 5)


def _wc_teams() -> list[str]:
    data = json.loads(CONFEDS.read_text(encoding="utf-8"))
    return [k for k in data if not k.startswith("_")]


def build(df: pd.DataFrame, teams: list[str]) -> dict:
    played = df.dropna(subset=["home_score", "away_score"]).copy()
    played = played.sort_values("date")
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
            matches.append({
                "date": pd.Timestamp(r.date).date().isoformat(),
                "opp": opp,
                "gf": gf,
                "ga": ga,
                "res": res,
                "comp": tour,
                "friendly": "friendly" in tour.lower(),
                "weight": round(match_importance(tour), 2),
                "home": bool(home),
                "neutral": str(getattr(r, "neutral", "")).strip().lower() in {"true", "1", "yes", "t"},
            })
        out[team] = {
            # form string oldest->newest (reads left-to-right like a results run)
            "form": "".join(m["res"] for m in reversed(matches[:5])),
            "matches": matches,
        }
    return out


def main() -> None:
    df = pd.read_csv(CSV, parse_dates=["date"])
    teams = _wc_teams()
    teams_form = build(df, teams)
    last_date = max(
        (m["date"] for t in teams_form.values() for m in t["matches"]),
        default=None,
    )
    payload = {
        "_note": "Recent international form for each WC2026 team (model/build_form.py). "
                 "Display-only context; 'weight' is the model's match-importance weight.",
        "updated": last_date,
        "teams": teams_form,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    n_matches = sum(len(t["matches"]) for t in teams_form.values())
    print(f"Wrote {OUT.relative_to(ROOT)} — {len(teams_form)} teams, {n_matches} matches (through {last_date}).")


if __name__ == "__main__":
    main()
