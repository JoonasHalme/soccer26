"""Tests for the bet logger (model/add_bet.py).

add_bet.main() reads its paths from module-level constants (BETS, SCHEMA,
FIXTURES, PREDICTIONS) and its inputs from argv, so we drive it by monkeypatching
those constants to tmp files and patching sys.argv. Nothing touches the real
bets/bets.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "model"
sys.path.insert(0, str(MODEL))

import add_bet  # noqa: E402

SCHEMA = json.loads((ROOT / "bets" / "schema.json").read_text(encoding="utf-8"))


def _prediction(match_id="m-001", edges=None):
    return {
        "match_id": match_id,
        "home": "Mexico",
        "away": "South Africa",
        "edges": edges if edges is not None else [],
    }


def _edge(selection="HOME", edge_pct=8.0, model_prob=0.55, **extra):
    e = {
        "market": "1X2",
        "selection": selection,
        "model_prob": model_prob,
        "implied_prob": 0.45,
        "odds_decimal": 2.1,
        "edge_pct": edge_pct,
        "best_book": "Pinnacle",
    }
    e.update(extra)
    return e


def _wire(monkeypatch, tmp_path, predictions, *, bets=None, fixture_ids=("m-001",),
          argv=None):
    """Point add_bet's module constants at tmp files and set argv."""
    bets_path = tmp_path / "bets.json"
    bets_path.write_text(
        json.dumps({
            "currency": "EUR", "starting_bankroll": 100, "unit_size": 2,
            "kelly_fraction": 0.25, "kelly_cap_pct": 5,
            "bets": bets if bets is not None else [],
        }),
        encoding="utf-8",
    )
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    fixtures_path = tmp_path / "fixtures.json"
    fixtures_path.write_text(
        json.dumps({"matches": [{"id": mid} for mid in fixture_ids]}),
        encoding="utf-8",
    )
    pred_path = tmp_path / "predictions.json"
    pred_path.write_text(json.dumps({"predictions": predictions}), encoding="utf-8")

    monkeypatch.setattr(add_bet, "BETS", bets_path)
    monkeypatch.setattr(add_bet, "SCHEMA", schema_path)
    monkeypatch.setattr(add_bet, "FIXTURES", fixtures_path)
    monkeypatch.setattr(add_bet, "PREDICTIONS", pred_path)
    monkeypatch.setattr(sys, "argv", ["add_bet.py", *(argv or [])])
    return bets_path


def _bets_in(bets_path: Path) -> list[dict]:
    return json.loads(bets_path.read_text(encoding="utf-8")).get("bets", [])


def test_percent_to_decimal_conversion(monkeypatch, tmp_path):
    """edge_pct=8.0 (percent) -> logged model_edge_pct == 0.08 (decimal)."""
    preds = [_prediction(edges=[_edge("HOME", edge_pct=8.0)])]
    bets_path = _wire(monkeypatch, tmp_path, preds,
                      argv=["--edge", "m-001:HOME", "--odds", "2.15"])
    rc = add_bet.main()
    assert rc == 0
    logged = _bets_in(bets_path)
    assert len(logged) == 1
    assert logged[0]["model_edge_pct"] == pytest.approx(0.08)


def test_bad_selection_exits(monkeypatch, tmp_path):
    """A selection not among the match's surfaced edges -> SystemExit."""
    preds = [_prediction(edges=[_edge("HOME", edge_pct=8.0)])]
    bets_path = _wire(monkeypatch, tmp_path, preds,
                      argv=["--edge", "m-001:AWAY", "--odds", "2.15"])
    with pytest.raises(SystemExit):
        add_bet.main()
    assert _bets_in(bets_path) == []  # nothing written


def test_bad_match_id_exits(monkeypatch, tmp_path):
    """A match_id absent from predictions.json -> SystemExit."""
    preds = [_prediction(match_id="m-001", edges=[_edge("HOME", edge_pct=8.0)])]
    bets_path = _wire(monkeypatch, tmp_path, preds,
                      argv=["--edge", "m-999:HOME", "--odds", "2.15"])
    with pytest.raises(SystemExit):
        add_bet.main()
    assert _bets_in(bets_path) == []


def test_invalid_candidate_not_written(monkeypatch, tmp_path):
    """A candidate that fails validation (match_id not in fixtures) must NOT be
    written and main() returns 1. We surface an edge on m-002 but omit m-002 from
    the fixtures so validate_match_id fails the validate-before-write gate."""
    preds = [_prediction(match_id="m-002", edges=[_edge("HOME", edge_pct=8.0)])]
    bets_path = _wire(monkeypatch, tmp_path, preds, fixture_ids=("m-001",),
                      argv=["--edge", "m-002:HOME", "--odds", "2.15"])
    rc = add_bet.main()
    assert rc == 1
    assert _bets_in(bets_path) == []  # nothing written


def test_dry_run_writes_nothing(monkeypatch, tmp_path):
    preds = [_prediction(edges=[_edge("HOME", edge_pct=8.0)])]
    bets_path = _wire(monkeypatch, tmp_path, preds,
                      argv=["--edge", "m-001:HOME", "--odds", "2.15", "--dry-run"])
    rc = add_bet.main()
    assert rc == 0
    assert _bets_in(bets_path) == []  # dry run: nothing persisted
