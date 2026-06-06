"""Tests for Asian-handicap / Asian-total probabilities (model/elo.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from elo import asian_probabilities, match_probabilities, score_matrix  # noqa: E402


LAMS = [(1.6, 0.9), (1.1, 1.1), (0.6, 2.0)]


def test_score_matrix_normalised():
    for lh, la in LAMS:
        assert abs(score_matrix(lh, la).sum() - 1.0) < 1e-9


def test_each_handicap_line_sums_to_one():
    """home cover + away cover + push must be a proper distribution per line."""
    for lh, la in LAMS:
        for h in asian_probabilities(lh, la)["handicaps"]:
            tot = h["home"] + h["away"] + h.get("push", 0.0)
            assert abs(tot - 1.0) < 1e-3


def test_half_lines_have_no_push():
    for lh, la in LAMS:
        for h in asian_probabilities(lh, la)["handicaps"]:
            if abs(h["line"] * 2 % 2) == 1:  # .5 lines
                assert "push" not in h


def test_ah_minus_half_equals_home_win():
    """AH home -0.5 (home must win outright) == the 1X2 home-win probability.
    (asian_probabilities rounds to 4dp for JSON size, hence the 1e-3 tolerance.)"""
    for lh, la in LAMS:
        ah = {h["line"]: h for h in asian_probabilities(lh, la)["handicaps"]}
        assert abs(ah[-0.5]["home"] - match_probabilities(lh, la)["home"]) < 1e-3


def test_ah_zero_is_draw_no_bet():
    """AH line 0.0 push probability == the draw probability."""
    for lh, la in LAMS:
        ah = {h["line"]: h for h in asian_probabilities(lh, la)["handicaps"]}
        assert abs(ah[0.0].get("push", 0.0) - match_probabilities(lh, la)["draw"]) < 1e-3


def test_home_cover_monotonic_in_line():
    """A more generous handicap (higher line) never lowers home's cover chance."""
    for lh, la in LAMS:
        hs = asian_probabilities(lh, la)["handicaps"]
        homes = [h["home"] for h in sorted(hs, key=lambda x: x["line"])]
        assert homes == sorted(homes)


def test_asian_totals_consistent_with_over_2_5():
    """The Asian-total 2.5 over must equal the model's Over-2.5 probability."""
    for lh, la in LAMS:
        tots = {t["line"]: t for t in asian_probabilities(lh, la)["totals"]}
        assert abs(tots[2.5]["over"] - match_probabilities(lh, la)["over_2_5"]) < 1e-3
        for t in tots.values():
            assert abs(t["over"] + t["under"] - 1.0) < 1e-3
