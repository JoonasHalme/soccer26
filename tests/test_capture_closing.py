"""Tests for the quota-aware closing-odds capture gating (model/capture_closing.py).

The decision logic is pure (takes `now` explicitly), so we can pin every branch:
not-yet-near, in-window-actionable, in-window-already-fresh, and past-kickoff+grace.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from capture_closing import capture_plan  # noqa: E402

NOW = datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc)


def _match(mins_to_kickoff, mid="m-x", captured_mins_ago=None, status="SCHEDULED"):
    ko = NOW + timedelta(minutes=mins_to_kickoff)
    m = {"id": mid, "status": status, "home": "A", "away": "B",
         "kickoff": ko.isoformat().replace("+00:00", "Z")}
    if captured_mins_ago is not None:
        cap = NOW - timedelta(minutes=captured_mins_ago)
        m["closing_odds"] = {"captured_at": cap.isoformat().replace("+00:00", "Z")}
    return m


def _plan(matches, within=3.0, grace=20.0, refresh=30.0):
    return capture_plan(matches, NOW, within, grace, refresh)


def test_far_from_kickoff_is_not_due():
    # 5 days out -> nothing due, no call.
    p = _plan([_match(60 * 24 * 5)])
    assert p.due == [] and p.actionable == [] and not p.should_call


def test_within_window_is_actionable():
    # Kicks off in 2h (< 3h window), never captured -> due + actionable -> call.
    p = _plan([_match(120)])
    assert len(p.due) == 1 and len(p.actionable) == 1 and p.should_call


def test_freshly_captured_is_due_but_not_actionable():
    # In window but captured 10 min ago (< 30 min refresh) -> skip, save quota.
    p = _plan([_match(60, captured_mins_ago=10)])
    assert len(p.due) == 1 and p.actionable == [] and not p.should_call


def test_stale_capture_is_actionable_again():
    # In window, captured 45 min ago (> 30 min refresh) -> recapture.
    p = _plan([_match(60, captured_mins_ago=45)])
    assert len(p.actionable) == 1 and p.should_call


def test_just_after_kickoff_within_grace_still_due():
    p = _plan([_match(-10)])           # kicked off 10 min ago, grace is 20
    assert len(p.actionable) == 1 and p.should_call


def test_well_past_kickoff_is_not_due():
    p = _plan([_match(-120)])          # 2h after kickoff, beyond grace
    assert p.due == [] and not p.should_call


def test_finished_match_ignored():
    p = _plan([_match(60, status="FINISHED")])
    assert p.due == [] and not p.should_call


def test_only_actionable_drives_the_call():
    # One fresh + one stale in window -> still call (the stale one needs it).
    p = _plan([_match(60, mid="fresh", captured_mins_ago=5),
               _match(90, mid="stale", captured_mins_ago=40)])
    assert len(p.due) == 2 and len(p.actionable) == 1 and p.should_call
    assert p.actionable[0][1]["id"] == "stale"
