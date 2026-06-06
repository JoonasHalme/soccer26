"""Tests for bet settlement (model/settle.py).

Synthetic FINISHED matches drive grading for every supported market, including
Asian-handicap half-win / push, plus idempotent re-settlement and empty inputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

import settle  # noqa: E402


def _match(home=2, away=1, mid="m-001", status="FINISHED"):
    return {"id": mid, "status": status, "score": {"home": home, "away": away}}


def _bet(market, selection, odds=2.0, stake=10.0, **kw):
    b = {
        "id": "b-test", "match_id": "m-001", "market": market,
        "selection": selection, "odds_decimal": odds, "stake": stake,
    }
    b.update(kw)
    return b


# ---- 1X2 -----------------------------------------------------------------

def test_1x2_home_win():
    g = settle.grade_bet(_bet("1X2", "HOME", odds=2.0, stake=10), _match(2, 1))
    assert g["result"] == "WIN"
    assert g["pnl"] == 10.0  # (2.0-1)*10


def test_1x2_away_loss():
    g = settle.grade_bet(_bet("1X2", "AWAY", odds=3.0, stake=10), _match(2, 1))
    assert g["result"] == "LOSS"
    assert g["pnl"] == -10.0


def test_1x2_draw_win_and_synonym():
    assert settle.grade_bet(_bet("1X2", "DRAW"), _match(1, 1))["result"] == "WIN"
    assert settle.grade_bet(_bet("1X2", "X"), _match(1, 1))["result"] == "WIN"
    assert settle.grade_bet(_bet("1X2", "1"), _match(2, 0))["result"] == "WIN"


# ---- OVER_UNDER ----------------------------------------------------------

def test_over_under_win_loss_push():
    assert settle.grade_bet(_bet("OVER_UNDER", "OVER_2_5"), _match(2, 1))["result"] == "WIN"   # 3>2.5
    assert settle.grade_bet(_bet("OVER_UNDER", "OVER_2_5"), _match(1, 0))["result"] == "LOSS"  # 1<2.5
    assert settle.grade_bet(_bet("OVER_UNDER", "UNDER_2_5"), _match(1, 0))["result"] == "WIN"
    # whole-number line can PUSH
    assert settle.grade_bet(_bet("OVER_UNDER", "OVER_3"), _match(2, 1))["result"] == "PUSH"     # total 3 == 3


# ---- BTTS ----------------------------------------------------------------

def test_btts():
    assert settle.grade_bet(_bet("BTTS", "BTTS_YES"), _match(1, 1))["result"] == "WIN"
    assert settle.grade_bet(_bet("BTTS", "YES"), _match(2, 0))["result"] == "LOSS"
    assert settle.grade_bet(_bet("BTTS", "NO"), _match(2, 0))["result"] == "WIN"


# ---- ASIAN_HANDICAP ------------------------------------------------------

def test_ah_full_line_win_and_loss():
    # HOME -1.5, final 2-0 -> margin 2-1.5 = +0.5 -> WIN
    assert settle.grade_bet(_bet("ASIAN_HANDICAP", "AHC_-1.5_HOME"), _match(2, 0))["result"] == "WIN"
    # HOME -1.5, final 1-0 -> margin 1-1.5 = -0.5 -> LOSS
    assert settle.grade_bet(_bet("ASIAN_HANDICAP", "AHC_-1.5_HOME"), _match(1, 0))["result"] == "LOSS"


def test_ah_push_on_integer_line():
    # AWAY +1, final 2-1 -> away margin -1 + 1 = 0 -> PUSH (stake returned)
    g = settle.grade_bet(_bet("ASIAN_HANDICAP", "AHC_+1_AWAY"), _match(2, 1))
    assert g["result"] == "PUSH"
    assert g["pnl"] == 0.0


def test_ah_quarter_line_half_win():
    # HOME +0.25, final 0-0 -> adj = 0 + 0.25 = +0.25 -> half-win
    # (the +0.25 splits across line 0 [push] and +0.5 [win]).
    g = settle.grade_bet(_bet("ASIAN_HANDICAP", "AHC_+0.25_HOME", odds=2.0, stake=10), _match(0, 0))
    assert g["result"] == "WIN"
    assert g["pnl"] == 5.0  # half stake wins at full odds: (2-1)*10/2


def test_ah_quarter_line_full_win():
    # HOME -0.25, final 1-0 -> adj = 0.75: line 0 wins AND line -0.5 wins -> full WIN.
    g = settle.grade_bet(_bet("ASIAN_HANDICAP", "AHC_-0.25_HOME", odds=2.0, stake=10), _match(1, 0))
    assert g["result"] == "WIN"
    assert g["pnl"] == 10.0


def test_ah_quarter_line_half_loss():
    # HOME -0.25, final 0-0 -> adj = 0 - 0.25 = -0.25 -> half-loss
    g = settle.grade_bet(_bet("ASIAN_HANDICAP", "AHC_-0.25_HOME", odds=2.0, stake=10), _match(0, 0))
    assert g["result"] == "LOSS"
    assert g["pnl"] == -5.0  # half stake lost


# ---- non-gradable -> VOID ------------------------------------------------

def test_correct_score_not_autogradable_is_void():
    g = settle.grade_bet(_bet("CORRECT_SCORE", "2-1"), _match(2, 1))
    assert g["result"] == "VOID"
    assert g["pnl"] == 0.0


# ---- settle_all / idempotency / empties ----------------------------------

def test_settle_all_grades_and_is_idempotent():
    fixtures = {"matches": [_match(2, 1)]}
    data = {"bets": [_bet("1X2", "HOME", odds=2.0, stake=10)]}
    data, changes = settle.settle_all(data, fixtures)
    assert len(changes) == 1
    assert data["bets"][0]["result"] == "WIN"
    assert data["bets"][0]["pnl"] == 10.0
    assert data["bets"][0]["settled_at"]
    # Re-running makes no change (idempotent).
    data, changes2 = settle.settle_all(data, fixtures)
    assert changes2 == []


def test_settle_resettles_when_score_changes():
    fixtures = {"matches": [_match(2, 1)]}
    data = {"bets": [_bet("1X2", "HOME", odds=2.0, stake=10)]}
    data, _ = settle.settle_all(data, fixtures)
    assert data["bets"][0]["result"] == "WIN"
    # Score corrected to an away win -> bet must flip to LOSS.
    fixtures["matches"][0]["score"] = {"home": 0, "away": 1}
    data, changes = settle.settle_all(data, fixtures)
    assert len(changes) == 1
    assert data["bets"][0]["result"] == "LOSS"


def test_unfinished_match_left_open():
    fixtures = {"matches": [{"id": "m-001", "status": "SCHEDULED", "score": {"home": None, "away": None}}]}
    data = {"bets": [_bet("1X2", "HOME")]}
    data, changes = settle.settle_all(data, fixtures)
    assert changes == []
    assert data["bets"][0].get("result") is None


def test_empty_inputs_handled():
    data, changes = settle.settle_all({"bets": []}, {"matches": []})
    assert changes == []
    assert data["bets"] == []


def test_match_is_final():
    assert settle.match_is_final(_match(1, 0))
    assert not settle.match_is_final({"status": "SCHEDULED", "score": {"home": None, "away": None}})


def test_live_match_with_score_is_not_graded():
    """A LIVE match carrying a (partial) score must NOT be settled — grading a
    half-played score would corrupt the bet log until full-time (code review H4)."""
    live = {"id": "m-001", "status": "LIVE", "score": {"home": 1, "away": 0}}
    assert not settle.match_is_final(live)
    # And settle_all must leave bets on a live match open.
    data = {"bets": [_bet("1X2", "HOME")]}
    data, changes = settle.settle_all(data, {"matches": [live]})
    assert changes == []
    assert data["bets"][0].get("result") is None
    # Once FINISHED with the same score, it grades.
    live["status"] = "FINISHED"
    assert settle.match_is_final(live)
