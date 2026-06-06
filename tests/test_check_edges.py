"""Tests for the edge-change / price-cross diff (model/check_edges.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from check_edges import diff_edges, current_edges  # noqa: E402


def _e(edge_pct, match="A vs B", market="1X2", sel="HOME", best=None):
    return {"match": match, "market": market, "selection": sel, "edge_pct": edge_pct, "best_odds": best}


def test_appeared_and_disappeared():
    prev = {"m1|1X2|HOME": _e(6.0)}
    curr = {"m2|1X2|AWAY": _e(7.0, sel="AWAY")}
    d = diff_edges(prev, curr, move=2.0)
    assert len(d["appeared"]) == 1 and d["appeared"][0]["selection"] == "AWAY"
    assert len(d["disappeared"]) == 1 and d["disappeared"][0]["selection"] == "HOME"
    assert d["moved"] == []


def test_moved_only_when_over_threshold():
    prev = {"k": _e(6.0)}
    curr = {"k": _e(9.0)}                 # +3pp move
    assert len(diff_edges(prev, curr, move=2.0)["moved"]) == 1
    assert diff_edges(prev, curr, move=5.0)["moved"] == []   # below 5pp threshold


def test_no_change_is_empty():
    snap = {"k": _e(6.0)}
    d = diff_edges(snap, dict(snap), move=2.0)
    assert not (d["appeared"] or d["disappeared"] or d["moved"])


def test_current_edges_builds_stable_identities():
    preds = [{
        "match_id": "m-001", "home": "Mexico", "away": "South Africa",
        "edges": [
            {"market": "1X2", "selection": "HOME", "edge_pct": 7.2, "best_odds": 1.5},
            {"market": "OVER_UNDER", "selection": "OVER_2_5", "edge_pct": 5.1},
        ],
    }]
    out = current_edges(preds)
    assert "m-001|1X2|HOME" in out and "m-001|OVER_UNDER|OVER_2_5" in out
    assert out["m-001|1X2|HOME"]["match"] == "Mexico vs South Africa"
    assert out["m-001|1X2|HOME"]["best_odds"] == 1.5
