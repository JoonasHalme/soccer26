"""Tests for the Monte-Carlo tournament simulator (model/simulate.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

import simulate  # noqa: E402
from elo import expected_goals  # noqa: E402


def _result(n=400, seed=7):
    return simulate.simulate(n=n, seed=seed)


def test_probability_totals():
    """Per-sim there is exactly one champion, two finalists, four semi-finalists,
    32 qualifiers and 12 group winners — so the summed probabilities are exact."""
    teams = _result()["teams"]
    s = lambda k: sum(t[k] for t in teams)
    assert round(s("champion"), 3) == 1.0
    assert round(s("final"), 3) == 2.0
    assert round(s("sf"), 3) == 4.0
    assert round(s("qualify"), 3) == 32.0
    assert round(s("win_group"), 3) == 12.0


def test_stage_monotonicity():
    """A team can't reach a later round more often than an earlier one."""
    for t in _result()["teams"]:
        assert t["qualify"] >= t["r16"] >= t["qf"] >= t["sf"] >= t["final"] >= t["champion"]
        assert t["win_group"] <= t["qualify"]
        assert 0.0 <= t["champion"] <= 1.0


def test_deterministic_with_seed():
    """Same seed -> identical output (reproducible provenance)."""
    a = _result(seed=42)
    b = _result(seed=42)
    assert [t["champion"] for t in a["teams"]] == [t["champion"] for t in b["teams"]]


def test_all_48_teams_present():
    teams = _result()["teams"]
    assert len(teams) == 48
    assert len({t["team"] for t in teams}) == 48
    # Every team is in some group A..L.
    assert all(t["group"] in "ABCDEFGHIJKL" for t in teams)


def test_vectorised_lambdas_match_expected_goals():
    """simulate.lambdas must agree element-for-element with elo.expected_goals,
    or the sim silently drifts from the production model."""
    rng = np.random.default_rng(0)
    rh = rng.uniform(1500, 2100, 50)
    ra = rng.uniform(1500, 2100, 50)
    for neutral in (True, False):
        lh, la = simulate.lambdas(rh, ra, neutral=neutral)
        for i in range(len(rh)):
            eh, ea = expected_goals(rh[i], ra[i], neutral=neutral)
            assert abs(lh[i] - eh) < 1e-9
            assert abs(la[i] - ea) < 1e-9


def test_favourites_are_strong_teams():
    """Sanity: the title favourite should be a high-rated side, and a minnow's
    championship probability should be ~0."""
    teams = _result(n=800, seed=3)["teams"]  # sorted by champion desc
    assert teams[0]["rating"] > 1850
    nz = next((t for t in teams if t["team"] == "New Zealand"), None)
    if nz:
        assert nz["champion"] < 0.02
