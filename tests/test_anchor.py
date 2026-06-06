"""Tests for per-confederation Elo anchoring (model/anchor.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from elo import EloTable  # noqa: E402
import anchor  # noqa: E402


def test_prob_to_gap_is_zero_at_even_and_monotonic():
    assert anchor._prob_to_gap(0.5) == 0.0
    assert anchor._prob_to_gap(0.75) > 0          # favourite -> positive gap
    assert anchor._prob_to_gap(0.25) < 0
    assert anchor._prob_to_gap(0.9) > anchor._prob_to_gap(0.75)


def test_apply_offsets_adds_per_confederation():
    t = EloTable(ratings={"Germany": 1900.0, "Iran": 1900.0, "Narnia": 1500.0})
    confeds = {"Germany": "UEFA", "Iran": "AFC"}
    offsets = {"UEFA": 50.0, "AFC": -50.0}
    anchor.apply_offsets(t, offsets, confeds)
    assert t.get("Germany") == 1950.0
    assert t.get("Iran") == 1850.0
    assert t.get("Narnia") == 1500.0              # no confederation -> untouched


def test_apply_offsets_handles_aliased_names():
    # ratings are keyed by the CANONICAL name; confeds use the fixture spelling.
    t = EloTable(ratings={"United States": 1765.0})
    anchor.apply_offsets(t, {"CONCACAF": -100.0}, {"USA": "CONCACAF"})
    assert t.get("USA") == 1665.0                 # canonicalised + adjusted


def test_apply_offsets_noop_when_empty():
    t = EloTable(ratings={"Germany": 1900.0})
    anchor.apply_offsets(t, {}, {"Germany": "UEFA"})
    assert t.get("Germany") == 1900.0


def test_confederation_map_covers_all_six_confederations():
    confeds = anchor.load_confederations()
    assert len(confeds) == 48
    assert set(confeds.values()) == {"UEFA", "CONMEBOL", "CAF", "AFC", "CONCACAF", "OFC"}


def test_persisted_offsets_are_mean_zero_across_the_field():
    """The recentring invariant — applying the offsets must not shift the average
    WC rating (so the totals strength term stays calibrated)."""
    offsets = anchor.load_offsets()
    if not offsets:
        return  # not fitted in this checkout
    confeds = anchor.load_confederations()
    total = sum(offsets.get(c, 0.0) for c in confeds.values())
    assert abs(total / len(confeds)) < 0.5        # ~0 within rounding
    # and the diagnosed direction: UEFA up, CONCACAF/AFC down
    assert offsets["UEFA"] > 0 > offsets["CONCACAF"]
    assert offsets["AFC"] < 0
