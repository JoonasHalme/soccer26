"""Tests for the H3 walk-forward backtest + calibration harness.

Run from the repo root:
    python -m pytest tests/ -q
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "model"
sys.path.insert(0, str(MODEL))

import backtest  # noqa: E402
import calibrate  # noqa: E402
import elo  # noqa: E402


# --------------------------------------------------------------------------- #
# Proper-scoring-rule correctness on tiny hand-computable inputs.
# --------------------------------------------------------------------------- #

def test_log_loss_perfect_and_uniform():
    # Perfect confident forecast -> ~0 loss.
    assert backtest.log_loss_one([1.0, 0.0, 0.0], 0) == pytest.approx(0.0, abs=1e-9)
    # Uniform forecast -> -ln(1/3) for any outcome.
    assert backtest.log_loss_one([1 / 3, 1 / 3, 1 / 3], 1) == pytest.approx(math.log(3), abs=1e-9)


def test_brier_known_value():
    # p=[0.5,0.3,0.2], outcome=home(0): (0.5-1)^2 + 0.3^2 + 0.2^2 = .25+.09+.04
    assert backtest.brier_one([0.5, 0.3, 0.2], 0) == pytest.approx(0.38, abs=1e-9)
    # Perfect forecast -> 0.
    assert backtest.brier_one([1.0, 0.0, 0.0], 0) == pytest.approx(0.0, abs=1e-9)


def test_rps_known_values():
    # Perfect ordered forecast -> 0.
    assert backtest.rps_one([1.0, 0.0, 0.0], 0) == pytest.approx(0.0, abs=1e-9)
    # Worst case: all mass on away, outcome home. cum_p steps (0,0); cum_o (1,1).
    # ((0-1)^2 + (0-1)^2)/2 = 1.0
    assert backtest.rps_one([0.0, 0.0, 1.0], 0) == pytest.approx(1.0, abs=1e-9)
    # Putting mass on the ADJACENT (draw) when home occurs is penalised less than
    # putting it on the FAR (away) outcome -- the ordinal property.
    near = backtest.rps_one([0.0, 1.0, 0.0], 0)
    far = backtest.rps_one([0.0, 0.0, 1.0], 0)
    assert near < far


def test_actual_outcome_mapping():
    assert backtest.actual_outcome(2, 0) == 0  # home win
    assert backtest.actual_outcome(1, 1) == 1  # draw
    assert backtest.actual_outcome(0, 3) == 2  # away win


# --------------------------------------------------------------------------- #
# No-leakage guarantee of the walk-forward split.
# --------------------------------------------------------------------------- #

def _synthetic_df(n=60):
    """Deterministic toy fixture set: a strong home team always beats a weak one."""
    rows = []
    base = pd.Timestamp("2021-01-01")
    for i in range(n):
        rows.append({
            "date": base + pd.Timedelta(days=i),
            "home_team": "Strong" if i % 2 == 0 else "Weak",
            "away_team": "Weak" if i % 2 == 0 else "Strong",
            "home_score": 2 if i % 2 == 0 else 0,
            "away_score": 0 if i % 2 == 0 else 2,
            "neutral": True,
        })
    return pd.DataFrame(rows)


def test_walk_forward_no_leakage_first_scored_match_uses_only_prior():
    """The rating used to PRICE a match must not reflect that match's result.

    We monkeypatch elo functions to capture the ratings passed to expected_goals
    for the first scored match, then independently rebuild the table from the
    matches strictly BEFORE it and assert they're identical (i.e. the predicted
    match contributed nothing to its own prediction)."""
    df = _synthetic_df(40)
    warmup = 10

    seen = {}
    real_expected = backtest.expected_goals

    def spy(rh, ra, neutral=False):
        if "first" not in seen:
            seen["first"] = (rh, ra)
        return real_expected(rh, ra, neutral=neutral)

    backtest.expected_goals = spy
    try:
        backtest.run_backtest(df, warmup=warmup)
    finally:
        backtest.expected_goals = real_expected

    # Rebuild ratings from ONLY the first `warmup` matches (those strictly before
    # the first scored match index == warmup).
    table = elo.EloTable()
    for row in df.iloc[:warmup].itertuples(index=False):
        table.update(row.home_team, row.away_team,
                     int(row.home_score), int(row.away_score), neutral=True)
    expected_rh = table.get(df.iloc[warmup].home_team)
    expected_ra = table.get(df.iloc[warmup].away_team)

    assert seen["first"][0] == pytest.approx(expected_rh)
    assert seen["first"][1] == pytest.approx(expected_ra)


def test_validation_window_is_strictly_after_train():
    """The train window (end_date=cutoff) and the validation window
    (start_date=cutoff) must be DISJOINT — every train match strictly before the
    cutoff, every validation match on/after it — so no match is scored twice.

    We reproduce the harness's own window arithmetic on the dataframe and assert
    the train/val match counts partition the post-warmup matches exactly, with
    the only shared boundary being matches dated exactly on the cutoff (which the
    inclusive end_date/start_date both admit). To make the windows truly disjoint
    we use a cutoff that no match falls on, and assert train.n + val.n equals the
    total scored matches after warmup with zero overlap."""
    import pandas as pd

    df = backtest.load_matches(since="2020-01-01")
    warmup = 800

    # Choose a cutoff timestamp strictly BETWEEN two consecutive post-warmup match
    # dates so no match lands exactly on it -> inclusive bounds can't double-count.
    post = df.iloc[warmup:]
    dates = sorted(post["date"].unique())
    assert len(dates) > 2
    mid = len(dates) // 2
    # midpoint between two distinct dates -> no match has this exact timestamp
    cutoff_ts = dates[mid - 1] + (dates[mid] - dates[mid - 1]) / 2
    cutoff = cutoff_ts.isoformat()

    train = backtest.run_backtest(df, warmup=warmup, end_date=cutoff)
    val = backtest.run_backtest(df, warmup=warmup, start_date=cutoff)

    # Independently count post-warmup matches on each side of the cutoff.
    n_before = int((post["date"] <= pd.Timestamp(cutoff)).sum())
    n_after = int((post["date"] >= pd.Timestamp(cutoff)).sum())
    n_total = len(post)

    assert train.n > 0 and val.n > 0
    # Each side matches the independent count.
    assert train.n == n_before
    assert val.n == n_after
    # DISJOINT: the two windows partition the post-warmup matches exactly — no
    # match is scored in both (would make the sum exceed the total).
    assert train.n + val.n == n_total


# --------------------------------------------------------------------------- #
# override_constants restores globals and actually changes the math.
# --------------------------------------------------------------------------- #

def test_override_constants_restores_globals():
    before = elo.current_constants()
    with elo.override_constants(K=12.34, HOME_ADV=200.0):
        assert elo.K == 12.34
        assert elo.HOME_ADV == 200.0
    assert elo.current_constants() == before


def test_override_constants_rejects_unknown():
    with pytest.raises(KeyError):
        with elo.override_constants(NOT_A_PARAM=1.0):
            pass


def test_override_changes_probabilities():
    rh, ra = 1700.0, 1600.0
    with elo.override_constants(HOME_ADV=0.0):
        lam_neutral_like = elo.expected_goals(rh, ra, neutral=False)
    with elo.override_constants(HOME_ADV=120.0):
        lam_big_home = elo.expected_goals(rh, ra, neutral=False)
    assert lam_big_home[0] > lam_neutral_like[0]


# --------------------------------------------------------------------------- #
# Fitted constants load + calibration improves on hand-set.
# --------------------------------------------------------------------------- #

def test_fitted_constants_loaded_from_json():
    """elo.py must reflect model/data/calibration.json when present."""
    path = MODEL / "data" / "calibration.json"
    if not path.exists():
        pytest.skip("calibration.json not generated yet")
    import json
    fitted = json.loads(path.read_text())["constants"]
    assert elo.K == pytest.approx(fitted["K"])
    assert elo.HOME_ADV == pytest.approx(fitted["HOME_ADV"])
    assert elo.DIXON_COLES_RHO == pytest.approx(fitted["DIXON_COLES_RHO"])


def test_calibration_fallback_when_missing(tmp_path, monkeypatch):
    """With no calibration.json the loader returns the hand-set defaults."""
    monkeypatch.setattr(elo, "_CALIBRATION_PATH", tmp_path / "nope.json")
    params = elo._load_calibrated()
    assert params == elo._DEFAULTS


def test_fitted_beats_or_matches_handset_on_train():
    """The fitted constants must not be WORSE than hand-set on train log-loss
    (the optimiser starts from hand-set, so it can only improve or tie)."""
    df = backtest.load_matches(since="2020-01-01")
    cutoff = "2025-01-01"
    handset = {n: elo._DEFAULTS[n] for n in calibrate.PARAM_NAMES}
    path = MODEL / "data" / "calibration.json"
    if not path.exists():
        pytest.skip("calibration.json not generated yet")
    import json
    fitted = json.loads(path.read_text())["constants"]
    old = backtest.run_backtest(df, warmup=800, end_date=cutoff, params=handset)
    new = backtest.run_backtest(df, warmup=800, end_date=cutoff, params=fitted)
    assert new.log_loss <= old.log_loss + 1e-6


def test_model_beats_baseline_on_full_backtest():
    """Sanity: the model must beat the naive base-rate forecast on log-loss."""
    df = backtest.load_matches(since="2020-01-01")
    res = backtest.run_backtest(df, warmup=800)
    base = backtest.baseline_metrics(res.records, res.base_rates)
    assert res.log_loss < base["log_loss"]


def test_ece_is_small_and_bounded():
    df = backtest.load_matches(since="2020-01-01")
    res = backtest.run_backtest(df, warmup=800)
    ece = backtest.expected_calibration_error(res.records)
    assert 0.0 <= ece < 0.10  # a well-calibrated model stays well under 10%
