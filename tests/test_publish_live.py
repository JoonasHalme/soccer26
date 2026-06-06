"""Tests for the live-results feed builder (model/publish_live.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from publish_live import build_live  # noqa: E402


def _m(mid, status, h=None, a=None):
    m = {"id": mid, "status": status}
    if h is not None:
        m["score"] = {"home": h, "away": a}
    return m


def test_only_scored_live_or_finished_included():
    matches = [
        _m("sched", "SCHEDULED"),                 # no score -> omitted
        _m("live", "LIVE", 1, 0),                 # included
        _m("ft", "FINISHED", 2, 1),               # included
        _m("live-noscore", "LIVE"),               # live but no score yet -> omitted
        _m("sched-score", "SCHEDULED", 0, 0),     # scheduled (shouldn't have score) -> omitted
    ]
    live = build_live(matches)
    assert set(live) == {"live", "ft"}
    assert live["live"] == {"status": "LIVE", "home": 1, "away": 0}
    assert live["ft"] == {"status": "FINISHED", "home": 2, "away": 1}


def test_empty_when_nothing_played():
    assert build_live([_m("a", "SCHEDULED"), _m("b", "SCHEDULED")]) == {}
