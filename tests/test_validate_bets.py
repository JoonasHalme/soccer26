"""Tests for the betting-discipline validator (model/validate_bets.py)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "model"
sys.path.insert(0, str(MODEL))

import validate_bets as vb  # noqa: E402

SCHEMA = json.loads((ROOT / "bets" / "schema.json").read_text(encoding="utf-8"))


def _base_bet(**overrides) -> dict:
    bet = {
        "id": "b-0001",
        "placed_at": "2026-06-11T18:00:00Z",
        "match_id": "m-001",
        "market": "1X2",
        "selection": "HOME",
        "odds_decimal": 1.9,
        "stake": 2,
        "source": "Pinnacle",
        "model_edge_pct": 0.08,
    }
    bet.update(overrides)
    return bet


def test_compliant_model_bet_passes():
    bet = _base_bet(model_edge_pct=0.08)
    assert vb.validate_schema(bet, SCHEMA) == []
    assert vb.validate_discipline(bet) == []


def test_low_edge_no_rationale_fails_discipline():
    bet = _base_bet(model_edge_pct=0.02)
    assert vb.validate_discipline(bet)  # non-empty -> violation


def test_exact_threshold_edge_passes_discipline():
    """An edge of EXACTLY 5% (0.05) must satisfy the discipline on its own: the
    rule is >= threshold, matching what predict.py surfaces and add_bet logs.
    A whisker below still requires a rationale."""
    on_threshold = _base_bet(model_edge_pct=0.05)
    assert vb.validate_discipline(on_threshold) == []
    just_below = _base_bet(model_edge_pct=0.0499)
    assert vb.validate_discipline(just_below)  # needs rationale


def test_low_edge_with_rationale_passes_discipline():
    bet = _base_bet(model_edge_pct=0.02, rationale="Key striker injured, fade the line.")
    assert vb.validate_discipline(bet) == []


def test_manual_bet_null_edge_needs_rationale():
    no_rationale = _base_bet(model_edge_pct=None)
    assert vb.validate_discipline(no_rationale)
    with_rationale = _base_bet(model_edge_pct=None, rationale="Gut call on the derby.")
    assert vb.validate_discipline(with_rationale) == []


def test_schema_catches_bad_enum_and_missing_field():
    bad_market = _base_bet(market="ACCUMULATOR")
    assert any("enum" in e for e in vb.validate_schema(bad_market, SCHEMA))
    missing = _base_bet()
    del missing["stake"]
    assert any("stake" in e for e in vb.validate_schema(missing, SCHEMA))


def test_schema_catches_below_minimum_odds():
    bet = _base_bet(odds_decimal=1.0)  # below schema minimum 1.01
    assert any("minimum" in e for e in vb.validate_schema(bet, SCHEMA))


def test_match_id_must_exist():
    assert vb.validate_match_id(_base_bet(match_id="m-999"), {"m-001"})
    assert vb.validate_match_id(_base_bet(match_id="m-001"), {"m-001"}) == []


def test_head_to_head_splits_model_and_manual():
    bets = [
        _base_bet(id="b1", model_edge_pct=0.08, result="WIN", pnl=1.8, stake=2),
        _base_bet(id="b2", model_edge_pct=0.07, result="LOSS", pnl=-2, stake=2),
        _base_bet(id="b3", model_edge_pct=None, rationale="manual", result="WIN", pnl=2.0, stake=2),
    ]
    h2h = vb.head_to_head(bets)
    assert h2h["model"]["bets"] == 2
    assert h2h["model"]["decided"] == 2
    assert h2h["model"]["wins"] == 1
    assert h2h["model"]["hit_rate"] == 0.5
    assert h2h["manual"]["bets"] == 1
    assert h2h["manual"]["wins"] == 1
