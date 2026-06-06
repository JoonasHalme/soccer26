"""Tests for fractional-Kelly staking (TASK-004)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

import staking  # noqa: E402


def test_no_edge_means_zero_kelly():
    """At fair or negative EV the Kelly fraction (and stake) is zero."""
    # p * odds = 1 exactly -> no edge
    assert staking.full_kelly_fraction(0.5, 2.0) == 0.0
    # p * odds < 1 -> negative EV
    assert staking.full_kelly_fraction(0.4, 2.0) == 0.0
    s = staking.kelly_stake(0.4, 2.0, bankroll=100)
    assert s["stake"] == 0.0


def test_kelly_scales_with_edge():
    """Bigger model edge at the same price -> bigger Kelly fraction."""
    small = staking.full_kelly_fraction(0.55, 2.0)
    big = staking.full_kelly_fraction(0.70, 2.0)
    assert 0 < small < big


def test_kelly_formula_matches_closed_form():
    """f* = (b·p − q)/b for a known case."""
    p, odds = 0.60, 2.0
    b, q = odds - 1, 1 - p
    assert staking.full_kelly_fraction(p, odds) == pytest.approx((b * p - q) / b)


def test_fractional_scaling_and_cap():
    # Full Kelly here is 0.2 of bankroll; quarter-Kelly = 0.05 -> 5.0 on 100.
    s = staking.kelly_stake(0.60, 2.0, bankroll=100, fraction=0.25, cap_pct=5)
    assert s["full_kelly"] == pytest.approx(0.2, abs=1e-9)
    assert s["stake"] == pytest.approx(5.0, abs=1e-9)
    assert s["capped"] is False
    # A huge edge would blow past the cap and get bound to cap_amount.
    capped = staking.kelly_stake(0.95, 5.0, bankroll=100, fraction=0.5, cap_pct=5)
    assert capped["capped"] is True
    assert capped["stake"] == pytest.approx(5.0)  # 5% of 100


def test_longshot_is_tamed():
    """The 46.0-odds outlier: huge EV but Kelly keeps the stake sane."""
    s = staking.kelly_stake(0.14, 46.0, bankroll=100, fraction=0.25, cap_pct=5)
    assert 0 < s["stake"] <= 5.0


def test_kelly_boundary_guards():
    """Degenerate inputs return 0 instead of dividing by zero / blowing up."""
    # odds == 1 -> b == 0 -> division-by-zero guard.
    assert staking.full_kelly_fraction(0.6, 1.0) == 0.0
    # model_prob at the 0/1 boundaries is rejected (not 0 < p < 1).
    assert staking.full_kelly_fraction(0.0, 2.0) == 0.0
    assert staking.full_kelly_fraction(1.0, 2.0) == 0.0
