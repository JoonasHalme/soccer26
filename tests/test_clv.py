"""Tests for closing-line-value computation (model/clv.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

import clv  # noqa: E402
from predict import devig_market  # noqa: E402


def _match_with_close(consensus, mid="m-001"):
    return {"id": mid, "closing_odds": {"consensus": consensus}}


# A simple, balanced 1X2 closing market with a known overround.
CLOSE_1X2 = {"home": 2.0, "draw": 4.0, "away": 4.0}


def test_devig_sums_to_one():
    fair = devig_market(CLOSE_1X2, ["home", "draw", "away"])
    assert abs(sum(fair.values()) - 1.0) < 1e-9


def test_beating_the_close_is_positive_clv():
    match = _match_with_close(CLOSE_1X2)
    fair = devig_market(CLOSE_1X2, ["home", "draw", "away"])
    fair_odds_home = 1.0 / fair["home"]
    # Bet odds ABOVE the fair closing odds -> positive CLV.
    bet = {"market": "1X2", "selection": "HOME", "odds_decimal": fair_odds_home * 1.1,
           "result": "WIN"}
    out = clv.compute_clv(bet, match)
    assert out is not None
    assert out["clv_pct"] > 0
    assert out["closing_odds_decimal"] == 2.0


def test_missing_the_close_is_negative_clv():
    match = _match_with_close(CLOSE_1X2)
    fair = devig_market(CLOSE_1X2, ["home", "draw", "away"])
    fair_odds_home = 1.0 / fair["home"]
    bet = {"market": "1X2", "selection": "HOME", "odds_decimal": fair_odds_home * 0.9,
           "result": "LOSS"}
    out = clv.compute_clv(bet, match)
    assert out is not None
    assert out["clv_pct"] < 0


def test_betting_exactly_fair_is_zero_clv():
    match = _match_with_close(CLOSE_1X2)
    fair = devig_market(CLOSE_1X2, ["home", "draw", "away"])
    bet = {"market": "1X2", "selection": "AWAY", "odds_decimal": 1.0 / fair["away"],
           "result": "LOSS"}
    out = clv.compute_clv(bet, match)
    assert abs(out["clv_pct"]) < 1e-6


def test_totals_market_clv():
    close = {"over_2_5": 1.9, "under_2_5": 1.9}
    match = _match_with_close(close)
    fair = devig_market(close, ["over_2_5", "under_2_5"])
    bet = {"market": "OVER_UNDER", "selection": "OVER_2_5",
           "odds_decimal": (1.0 / fair["over_2_5"]) * 1.2, "result": "WIN"}
    out = clv.compute_clv(bet, match)
    assert out["clv_pct"] > 0


def test_no_closing_snapshot_returns_none():
    match = {"id": "m-001"}  # no closing_odds
    bet = {"market": "1X2", "selection": "HOME", "odds_decimal": 2.0, "result": "WIN"}
    assert clv.compute_clv(bet, match) is None


def test_unsupported_market_returns_none():
    match = _match_with_close(CLOSE_1X2)
    bet = {"market": "ASIAN_HANDICAP", "selection": "AHC_-1.5_HOME",
           "odds_decimal": 2.0, "result": "WIN"}
    assert clv.compute_clv(bet, match) is None


def test_portfolio_beat_rate_and_avg():
    bets = [
        {"clv_pct": 5.0}, {"clv_pct": -2.0}, {"clv_pct": 3.0}, {"clv_pct": 0.0},
    ]
    port = clv.portfolio_clv(bets)
    assert port["rated"] == 4
    assert port["beat_rate"] == 0.5  # 2 of 4 strictly positive
    assert port["avg_clv"] == 1.5    # (5-2+3+0)/4


def test_annotate_only_settled_bets():
    fixtures = {"matches": [_match_with_close(CLOSE_1X2)]}
    fair = devig_market(CLOSE_1X2, ["home", "draw", "away"])
    odds = (1.0 / fair["home"]) * 1.1
    data = {"bets": [
        {"id": "b1", "match_id": "m-001", "market": "1X2", "selection": "HOME",
         "odds_decimal": odds, "result": "WIN"},
        {"id": "b2", "match_id": "m-001", "market": "1X2", "selection": "HOME",
         "odds_decimal": odds, "result": None},  # unsettled -> skipped
    ]}
    data, changes = clv.annotate_all(data, fixtures)
    assert len(changes) == 1
    assert data["bets"][0]["clv_pct"] > 0
    assert "clv_pct" not in data["bets"][1]


def test_empty_inputs_handled():
    data, changes = clv.annotate_all({"bets": []}, {"matches": []})
    assert changes == []
    assert clv.portfolio_clv([])["beat_rate"] is None


# --------------------------------------------------------------------------- #
# TASK-011 — confidence interval on mean CLV
# --------------------------------------------------------------------------- #

def test_mean_ci_none_for_small_sample():
    assert clv.mean_ci([]) is None
    assert clv.mean_ci([3.0]) is None  # one point has no interval


def test_mean_ci_brackets_the_mean():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    ci = clv.mean_ci(vals)
    assert ci is not None
    assert ci["mean"] == 3.0
    assert ci["low"] < ci["mean"] < ci["high"]
    # margin = t(df=4)=2.776 * (std/sqrt(n)); std=1.5811, se=0.7071 -> ~1.963
    assert ci["margin"] == round(2.776 * (1.5811388 / (5 ** 0.5)), 2)


def test_mean_ci_zero_width_when_identical():
    ci = clv.mean_ci([2.5, 2.5, 2.5])
    assert ci["margin"] == 0.0
    assert ci["low"] == ci["high"] == 2.5


def test_portfolio_clv_includes_ci():
    bets = [{"clv_pct": 1.0}, {"clv_pct": 3.0}, {"clv_pct": 5.0}]
    port = clv.portfolio_clv(bets)
    assert port["rated"] == 3
    assert port["clv_ci"] is not None
    assert port["clv_ci"]["mean"] == 3.0
