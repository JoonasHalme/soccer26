"""Tests for the recent-form builder (model/build_form.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from build_form import build  # noqa: E402


def _df(rows):
    return pd.DataFrame(rows)


def test_result_perspective_and_friendly_weight():
    df = _df([
        # USA (CSV canonical "United States") at home, win, friendly
        {"date": pd.Timestamp("2026-05-31"), "home_team": "United States", "away_team": "Senegal",
         "home_score": 3, "away_score": 2, "tournament": "Friendly", "neutral": False},
        # USA away, loss, a competitive game
        {"date": pd.Timestamp("2025-11-18"), "home_team": "Mexico", "away_team": "United States",
         "home_score": 2, "away_score": 0, "tournament": "FIFA World Cup qualification", "neutral": False},
    ])
    out = build(df, ["USA"])                       # keyed by the fixtures name, matched via canonical()
    assert "USA" in out
    ms = out["USA"]["matches"]
    assert ms[0]["date"] == "2026-05-31"           # most-recent first
    assert ms[0]["res"] == "W" and ms[0]["gf"] == 3 and ms[0]["ga"] == 2
    assert ms[0]["friendly"] is True and ms[0]["weight"] == 0.5 and ms[0]["home"] is True
    # away competitive loss, full weight, opponent from the team's perspective
    assert ms[1]["res"] == "L" and ms[1]["home"] is False and ms[1]["opp"] == "Mexico"
    assert ms[1]["friendly"] is False and ms[1]["weight"] == 1.0


def test_form_string_reads_oldest_to_newest():
    rows = []
    # three games, newest last in source; result sequence by date: L, D, W
    for d, hs, as_ in [("2026-01-01", 0, 1), ("2026-02-01", 1, 1), ("2026-03-01", 2, 0)]:
        rows.append({"date": pd.Timestamp(d), "home_team": "Spain", "away_team": "X",
                     "home_score": hs, "away_score": as_, "tournament": "Friendly", "neutral": False})
    out = build(_df(rows), ["Spain"])
    # form is oldest->newest, so the most recent (a win) is rightmost
    assert out["Spain"]["form"] == "LDW"


def test_unknown_team_is_skipped():
    df = _df([{"date": pd.Timestamp("2026-05-01"), "home_team": "Spain", "away_team": "France",
               "home_score": 1, "away_score": 0, "tournament": "Friendly", "neutral": True}])
    assert "Atlantis" not in build(df, ["Atlantis"])
