"""Tests for the recent-form builder (model/build_form.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from build_form import build, _model_view, recent_feed, walkforward_predictions  # noqa: E402


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


def test_model_view_flips_perspective_and_scores_pick():
    pred = (0.60, 0.25, 0.15)                       # home-perspective (home, draw, away)
    # home team won -> backs the 60% home win, correct
    mv = _model_view(pred, home=True, res="W")
    assert mv["pw"] == 0.6 and mv["pick"] == "W" and mv["correct"] is True and mv["p_actual"] == 0.6
    # the AWAY team's own win prob is 0.15 and loss is 0.60; they lost -> pick L, correct
    mv2 = _model_view(pred, home=False, res="L")
    assert mv2["pw"] == 0.15 and mv2["pl"] == 0.6 and mv2["pick"] == "L" and mv2["correct"] is True
    # away team actually drew -> wrong pick, p_actual is the shared draw prob
    mv3 = _model_view(pred, home=False, res="D")
    assert mv3["correct"] is False and mv3["p_actual"] == 0.25


def test_build_attaches_walkforward_model_and_record():
    df = _df([
        {"date": pd.Timestamp("2026-03-01"), "home_team": "Spain", "away_team": "X",
         "home_score": 3, "away_score": 0, "tournament": "Friendly", "neutral": False},
        {"date": pd.Timestamp("2026-04-01"), "home_team": "Spain", "away_team": "Y",
         "home_score": 1, "away_score": 1, "tournament": "Friendly", "neutral": False},
    ])
    out = build(df, ["Spain"])["Spain"]
    assert out["record"]["total"] == 2 and 0 <= out["record"]["correct"] <= 2
    assert all("model" in m for m in out["matches"])
    # probabilities are a distribution
    mv = out["matches"][0]["model"]
    assert abs(mv["pw"] + mv["pd"] + mv["pl"] - 1.0) < 0.02


def test_recent_feed_dedupes_and_maps_display_names():
    df = _df([
        # WC team under its CSV-canonical spelling; opponent is non-WC
        {"date": pd.Timestamp("2026-05-20"), "home_team": "United States", "away_team": "Senegal",
         "home_score": 2, "away_score": 1, "tournament": "Friendly", "neutral": False},
        # before the feed cutoff -> excluded
        {"date": pd.Timestamp("2026-04-01"), "home_team": "United States", "away_team": "Mexico",
         "home_score": 0, "away_score": 0, "tournament": "Friendly", "neutral": False},
    ])
    preds = walkforward_predictions(df, {"United States"})
    feed = recent_feed(df, preds, ["USA"], since="2026-05-01")
    assert len(feed) == 1                       # the April game is before the cutoff
    g = feed[0]
    assert g["home"] == "USA"                    # canonical -> fixtures display name
    assert g["model"]["pick"] in {"H", "D", "A"}
    assert g["model"]["correct"] is (g["model"]["pick"] == "H")   # USA won at home
