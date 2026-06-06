"""Tests for the derived markets (Double Chance / Draw-No-Bet / correct scores).

These all fall out of the same Dixon-Coles score matrix as 1X2, so the key
property is internal consistency with match_probabilities()."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from elo import derived_markets, match_probabilities  # noqa: E402


LAMS = [(1.6, 0.9), (1.1, 1.1), (0.6, 2.0)]


def test_double_chance_matches_1x2_pairs():
    """Each double-chance prob must equal the sum of its two 1X2 legs."""
    for lh, la in LAMS:
        d = derived_markets(lh, la)["double_chance"]
        p = match_probabilities(lh, la)
        assert abs(d["home_or_draw"] - (p["home"] + p["draw"])) < 1e-3
        assert abs(d["home_or_away"] - (p["home"] + p["away"])) < 1e-3
        assert abs(d["draw_or_away"] - (p["draw"] + p["away"])) < 1e-3


def test_double_chance_three_pairs_sum_to_two():
    """The three double-chance outcomes each drop one leg, so together they count
    every 1X2 leg exactly twice -> they sum to 2."""
    for lh, la in LAMS:
        d = derived_markets(lh, la)["double_chance"]
        assert abs(sum(d.values()) - 2.0) < 1e-3


def test_dnb_renormalises_over_decisive_outcomes():
    """Draw-No-Bet drops the draw and renormalises, so the two legs sum to 1 and
    keep the home/away ratio from the full 1X2 distribution."""
    for lh, la in LAMS:
        dnb = derived_markets(lh, la)["dnb"]
        p = match_probabilities(lh, la)
        assert abs(dnb["home"] + dnb["away"] - 1.0) < 1e-3
        expected_home = p["home"] / (p["home"] + p["away"])
        assert abs(dnb["home"] - expected_home) < 1e-3


def test_correct_scores_sorted_and_bounded():
    """Top scorelines come back in descending probability and sum to <= 1."""
    for lh, la in LAMS:
        cs = derived_markets(lh, la)["correct_scores"]
        assert len(cs) == 6
        probs = [c["prob"] for c in cs]
        assert probs == sorted(probs, reverse=True)
        assert 0 < sum(probs) <= 1.0 + 1e-9
        for c in cs:
            assert c["home"] >= 0 and c["away"] >= 0


def test_correct_scores_top_pick_reasonable():
    """For a strong home favourite (1.6 vs 0.9) the single likeliest scoreline
    should be a home win or a draw, never an away win."""
    cs = derived_markets(1.6, 0.9)["correct_scores"]
    top = cs[0]
    assert top["home"] >= top["away"]
