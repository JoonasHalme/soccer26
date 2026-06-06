"""Fit the model's calibration constants by minimising walk-forward log-loss.

This is the H3 / L3 deliverable. We fit a SMALL set of constants (5) so the
probabilities are calibrated against history instead of hand-set:

    K, HOME_ADV, ELO_TO_GOAL_DIFF, GOALS_BASELINE, DIXON_COLES_RHO

Methodology (honest, leakage-free):
  - Split the history by DATE into a TRAIN window and a later, held-out
    VALIDATION window (walk-forward: validation is strictly after train).
  - The objective fits on the TRAIN window's walk-forward log-loss only. Ratings
    are always built forward in time (predict-before-update), so even within
    train there is no leakage.
  - We optimise with scipy's Nelder-Mead (derivative-free, robust for a handful
    of params) when scipy is present, otherwise a stdlib coordinate descent.
  - We report TRAIN vs VALIDATION metrics for both the old hand-set constants and
    the fitted ones, so over/underfitting is visible, and persist the fitted set
    to model/data/calibration.json (which elo.py loads at import).

Usage:
    python model/calibrate.py                       # fit + report + persist
    python model/calibrate.py --no-write            # fit + report only
    python model/calibrate.py --val-cutoff 2025-01-01
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import elo
from backtest import (
    baseline_metrics,
    expected_calibration_error,
    load_matches,
    run_backtest,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "model" / "data" / "calibration.json"

# Default temporal split. Train: warmup..val_cutoff; Validation: val_cutoff..end.
DEFAULT_VAL_CUTOFF = "2025-01-01"
DEFAULT_SINCE = "2020-01-01"
DEFAULT_WARMUP = 800

# The fit is split by OBJECTIVE. The 1X2 params are fit to multiclass 1X2 log-loss;
# the TOTALS params are fit to Over/Under-2.5 log-loss. They were previously lumped
# together against the 1X2 objective, which barely constrains the totals — so the
# totals shape was effectively unfit and ran hot (model P(over) >> realised/market on
# the strong WC field; see docs/backlog.md TASK-048).
PARAM_NAMES = ("K", "HOME_ADV", "ELO_TO_GOAL_DIFF", "DIXON_COLES_RHO")
TOTALS_NAMES = ("GOALS_BASELINE", "GOALS_STRENGTH_COEF", "GOALS_MISMATCH_COEF")
BOUNDS = {
    "K": (5.0, 110.0),
    "HOME_ADV": (0.0, 150.0),
    "ELO_TO_GOAL_DIFF": (0.0005, 0.012),
    "DIXON_COLES_RHO": (-0.25, 0.10),
    "GOALS_BASELINE": (1.8, 3.2),
    "GOALS_STRENGTH_COEF": (-0.004, 0.004),
    "GOALS_MISMATCH_COEF": (-0.004, 0.004),
}


def _clamp(name: str, value: float) -> float:
    lo, hi = BOUNDS[name]
    return min(hi, max(lo, value))


def params_from_vector(x, names=PARAM_NAMES) -> dict:
    return {name: _clamp(name, float(v)) for name, v in zip(names, x)}


def train_logloss(x, df, warmup, val_cutoff) -> float:
    """Walk-forward TRAIN log-loss for a candidate parameter vector.

    Ratings are built forward over the whole frame, but only matches in the
    train window [warmup .. val_cutoff) are scored. Returns +inf on a degenerate
    candidate so the optimiser steps away from it.
    """
    params = params_from_vector(x)
    try:
        res = run_backtest(df, warmup=warmup, end_date=val_cutoff, params=params)
    except Exception:
        return float("inf")
    return res.log_loss


def fit(df, warmup: int, val_cutoff: str, x0: list[float]) -> dict:
    """Minimise train log-loss. Prefers scipy Nelder-Mead; falls back to a
    stdlib coordinate descent so the script runs even without scipy.optimize."""
    try:
        from scipy.optimize import minimize

        result = minimize(
            train_logloss, x0, args=(df, warmup, val_cutoff),
            method="Nelder-Mead",
            options={"xatol": 1e-3, "fatol": 1e-5, "maxiter": 400, "disp": False},
        )
        best = params_from_vector(result.x)
        best_loss = float(result.fun)
        method = "scipy.Nelder-Mead"
    except ImportError:
        best, best_loss = _coordinate_descent(df, warmup, val_cutoff, x0)
        method = "coordinate-descent"
    return {"constants": best, "train_log_loss": best_loss, "optimizer": method}


def _coordinate_descent(df, warmup, val_cutoff, x0):
    """Stdlib fallback: cycle through params, line-searching each on a shrinking
    grid. Robust if unglamorous; enough for 5 smooth-ish parameters."""
    x = list(x0)
    best_loss = train_logloss(x, df, warmup, val_cutoff)
    steps = {
        "K": 8.0, "HOME_ADV": 20.0, "ELO_TO_GOAL_DIFF": 0.0015,
        "GOALS_BASELINE": 0.2, "DIXON_COLES_RHO": 0.04,
    }
    step_vec = [steps[n] for n in PARAM_NAMES]
    for _sweep in range(6):
        improved = False
        for i in range(len(x)):
            for direction in (+1, -1):
                cand = list(x)
                cand[i] = _clamp(PARAM_NAMES[i], cand[i] + direction * step_vec[i])
                loss = train_logloss(cand, df, warmup, val_cutoff)
                if loss < best_loss - 1e-7:
                    x, best_loss = cand, loss
                    improved = True
        step_vec = [s * 0.5 for s in step_vec]
        if not improved:
            continue
    return params_from_vector(x), best_loss


def train_ou_logloss(x_totals, fixed_1x2, df, warmup, val_cutoff) -> float:
    """Walk-forward TRAIN Over/Under-2.5 log-loss for a candidate totals vector,
    holding the (already-fit) 1X2 constants fixed. This is the objective the totals
    shape SHOULD be fit to — the 1X2 objective barely sees GOALS_BASELINE/coefs."""
    params = dict(fixed_1x2)
    params.update(params_from_vector(x_totals, TOTALS_NAMES))
    try:
        res = run_backtest(df, warmup=warmup, end_date=val_cutoff, params=params)
    except Exception:
        return float("inf")
    return res.ou_log_loss


def fit_totals(df, warmup: int, val_cutoff: str, fixed_1x2: dict, x0: list[float]) -> dict:
    """Minimise train O/U log-loss over the totals params, 1X2 constants held fixed."""
    try:
        from scipy.optimize import minimize

        result = minimize(
            train_ou_logloss, x0, args=(fixed_1x2, df, warmup, val_cutoff),
            method="Nelder-Mead",
            options={"xatol": 1e-4, "fatol": 1e-6, "maxiter": 200, "disp": False},
        )
        best = params_from_vector(result.x, TOTALS_NAMES)
        best_loss = float(result.fun)
        method = "scipy.Nelder-Mead"
    except ImportError:
        x = list(x0)
        best_loss = train_ou_logloss(x, fixed_1x2, df, warmup, val_cutoff)
        steps = {"GOALS_BASELINE": 0.2, "GOALS_STRENGTH_COEF": 0.0008, "GOALS_MISMATCH_COEF": 0.0008}
        step_vec = [steps[n] for n in TOTALS_NAMES]
        for _sweep in range(8):
            for i in range(len(x)):
                for direction in (+1, -1):
                    cand = list(x)
                    cand[i] = _clamp(TOTALS_NAMES[i], cand[i] + direction * step_vec[i])
                    loss = train_ou_logloss(cand, fixed_1x2, df, warmup, val_cutoff)
                    if loss < best_loss - 1e-9:
                        x, best_loss = cand, loss
            step_vec = [s * 0.5 for s in step_vec]
        best = params_from_vector(x, TOTALS_NAMES)
        method = "coordinate-descent"
    return {"constants": best, "train_ou_log_loss": best_loss, "optimizer": method}


def evaluate(df, warmup, val_cutoff, params, label):
    """Score a parameter set on both train and validation windows."""
    train = run_backtest(df, warmup=warmup, end_date=val_cutoff, params=params)
    val = run_backtest(df, warmup=warmup, start_date=val_cutoff, params=params)
    train_ece = expected_calibration_error(train.records)
    val_ece = expected_calibration_error(val.records)
    train_base = baseline_metrics(train.records, train.base_rates)
    val_base = baseline_metrics(val.records, val.base_rates)
    return {
        "label": label,
        "params": {k: round(v, 6) for k, v in params.items()},
        "train": {**train.summary(), "ece": round(train_ece, 5),
                  "baseline_log_loss": train_base["log_loss"],
                  "beats_baseline": train.log_loss < train_base["log_loss"]},
        "validation": {**val.summary(), "ece": round(val_ece, 5),
                       "baseline_log_loss": val_base["log_loss"],
                       "beats_baseline": val.log_loss < val_base["log_loss"]},
    }


def _print_eval(ev):
    print(f"\n=== {ev['label']} ===")
    print(f"params: {ev['params']}")
    for split in ("train", "validation"):
        s = ev[split]
        print(f"  {split:11s} n={s['n']:5d}  "
              f"log-loss={s['log_loss']:.4f}  brier={s['brier']:.4f}  "
              f"rps={s['rps']:.4f}  acc={s['accuracy']:.4f}  ece={s['ece']:.4f}  "
              f"| baseline LL={s['baseline_log_loss']:.4f}  "
              f"beats={s['beats_baseline']}")


def _active_1x2() -> dict:
    """The currently-loaded 1X2 constants (from calibration.json via elo)."""
    return {n: getattr(elo, n) for n in PARAM_NAMES}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit Elo/Poisson calibration constants")
    ap.add_argument("--since", default=DEFAULT_SINCE)
    ap.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    ap.add_argument("--val-cutoff", default=DEFAULT_VAL_CUTOFF)
    ap.add_argument("--no-write", action="store_true", help="don't persist calibration.json")
    ap.add_argument("--totals-only", action="store_true",
                    help="keep the active 1X2 constants; refit ONLY the totals "
                         "(GOALS_BASELINE + shape coefs) to O/U log-loss")
    args = ap.parse_args()

    df = load_matches(since=args.since)
    handset = {n: elo._DEFAULTS[n] for n in PARAM_NAMES + TOTALS_NAMES}

    print(f"Loaded {len(df)} played matches since {args.since}.")
    print(f"Warmup {args.warmup}; train < {args.val_cutoff} <= validation.")

    # --- Stage 1: 1X2 constants (skipped under --totals-only) ---
    if args.totals_only:
        fitted_1x2 = _active_1x2()
        method_1x2 = "kept (active calibration.json)"
        print(f"\n--totals-only: keeping active 1X2 constants {('%s' % {k: round(v,4) for k,v in fitted_1x2.items()})}")
    else:
        print(f"Fitting 1X2 {PARAM_NAMES} by minimising walk-forward TRAIN log-loss...")
        fit_out = fit(df, args.warmup, args.val_cutoff, [handset[n] for n in PARAM_NAMES])
        fitted_1x2 = fit_out["constants"]
        method_1x2 = fit_out["optimizer"]
        print(f"  optimizer: {method_1x2}  train 1X2 log-loss -> {fit_out['train_log_loss']:.5f}")

    # --- Stage 2: totals constants, fit to O/U log-loss with 1X2 held fixed ---
    print(f"Fitting totals {TOTALS_NAMES} by minimising walk-forward TRAIN O/U log-loss...")
    tot_out = fit_totals(df, args.warmup, args.val_cutoff, fitted_1x2,
                         [getattr(elo, n) for n in TOTALS_NAMES])
    fitted_totals = tot_out["constants"]
    print(f"  optimizer: {tot_out['optimizer']}  train O/U log-loss -> {tot_out['train_ou_log_loss']:.5f}")

    fitted = {**fitted_1x2, **fitted_totals}

    old_eval = evaluate(df, args.warmup, args.val_cutoff, handset, "HAND-SET (old)")
    new_eval = evaluate(df, args.warmup, args.val_cutoff, fitted, "FITTED (new)")
    _print_eval(old_eval)
    _print_eval(new_eval)
    print(f"\nFitted constants: { {k: round(v,6) for k,v in fitted.items()} }")

    if not args.no_write:
        payload = {
            "constants": {k: round(v, 6) for k, v in fitted.items()},
            "fitted_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(),
            "method": {"one_x_two": method_1x2, "totals": tot_out["optimizer"]},
            "objective": {"one_x_two": "1X2 log-loss", "totals": "O/U-2.5 log-loss"},
            "split": {"since": args.since, "warmup": args.warmup,
                      "val_cutoff": args.val_cutoff},
            "handset_fallback": handset,
            "metrics": {"handset": old_eval, "fitted": new_eval},
        }
        OUT.write_text(json.dumps(payload, indent=2))
        print(f"\nWrote fitted constants to {OUT.relative_to(ROOT)}")
    else:
        print("\n(--no-write: calibration.json NOT updated)")


if __name__ == "__main__":
    main()
