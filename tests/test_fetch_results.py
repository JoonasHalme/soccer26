"""Tests for the quota-aware scores-call gate (model/fetch_results.py).

`needs_results_call` is pure (takes `matches` + `now` explicitly), so we can pin
every branch — and in particular the BACKFILL case that was the bug: a match that
finished while the scheduled poll was skipped/delayed (GitHub crons do this under
load) must still trigger a call so its result is recovered, instead of being
stranded forever (never FINISHED, kickoff older than the fresh window)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from fetch_results import needs_results_call  # noqa: E402

NOW = datetime(2026, 6, 12, 16, 0, tzinfo=timezone.utc)


def _match(hours_to_kickoff, status="SCHEDULED", mid="m-x"):
    ko = NOW + timedelta(hours=hours_to_kickoff)
    return {"id": mid, "status": status, "home": "A", "away": "B",
            "kickoff": ko.isoformat().replace("+00:00", "Z")}


def _call(matches, window=3.0, backfill=72.0):
    return needs_results_call(matches, NOW, window, backfill)


def test_far_future_match_no_call():
    # Kicks off in 5 days -> no fresh result, nothing to backfill.
    assert _call([_match(24 * 5)]) is False


def test_live_match_calls():
    assert _call([_match(-1, status="LIVE")]) is True


def test_finished_match_alone_no_call():
    # Already graded -> never triggers a call (this is what stops the backfill loop).
    assert _call([_match(-10, status="FINISHED")]) is False


def test_fresh_result_within_window_calls():
    # Kicked off 2h ago, not yet graded -> a fresh result is landing.
    assert _call([_match(-2)]) is True


def test_backfill_missed_result_calls():
    # THE BUG: kicked off 14h ago, still SCHEDULED (poll was skipped during its
    # window). Outside the 3h fresh window but inside the 72h backfill window ->
    # must still call so we recover the result.
    assert _call([_match(-14)]) is True


def test_stale_unscored_match_aged_out_no_call():
    # Kicked off 4 days ago and somehow never graded -> beyond the scores API's
    # daysFrom reach, so calling can't help; stop polling for it.
    assert _call([_match(-24 * 4)]) is False


def test_mix_finished_plus_pending_backfill_calls():
    matches = [_match(-30, status="FINISHED", mid="m-001"),
               _match(-14, status="SCHEDULED", mid="m-002")]
    assert _call(matches) is True
