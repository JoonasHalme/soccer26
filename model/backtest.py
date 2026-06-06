"""Walk-forward backtest + calibration assessment for the Elo/Poisson model.

This is the H3 deliverable: replay historical internationals in CHRONOLOGICAL
order, maintaining Elo ratings updated ONLY from matches strictly before the one
being predicted (no leakage), and score the model's 1X2 (and Over/Under 2.5)
probabilities against the realised result with proper scoring rules.

Metrics
    - multiclass log-loss (a.k.a. ignorance score)   -- lower is better
    - multiclass Brier score                         -- lower is better
    - Ranked Probability Score (RPS, ordered 1X2)    -- lower is better
    - accuracy / hit-rate (argmax == outcome)
    - calibration: reliability bins + Expected Calibration Error (ECE)

Everything runs through the SAME functions in elo.py (expected_goals,
match_probabilities, EloTable.update) so the backtest measures the production
model, not a re-implementation. Candidate parameter sets are evaluated via
elo.override_constants(), which the calibrator (model/calibrate.py) drives.

Usage:
    python model/backtest.py                 # full backtest with active constants
    python model/backtest.py --since 2020-01-01 --warmup 800
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import elo
from elo import EloTable, expected_goals, match_probabilities

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "model" / "data" / "internationals.csv"

# Outcome index convention for the ordered 1X2 vector: [home, draw, away].
OUTCOMES = ("home", "draw", "away")
_EPS = 1e-15


def _is_neutral(val) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in {"true", "1", "yes", "t"}


def load_matches(csv: Path = CSV, since: str | None = "2020-01-01") -> pd.DataFrame:
    """Load played internationals in chronological order.

    Drops unplayed (NA-score) rows — the CSV carries future WC fixtures — and
    rows before `since` (the model is trained on the modern era only). Returns a
    frame with stable integer index for deterministic iteration.
    """
    df = pd.read_csv(csv, parse_dates=["date"]).sort_values("date")
    df = df.dropna(subset=["home_score", "away_score"])
    if since is not None:
        df = df[df["date"] >= since]
    df = df.reset_index(drop=True)
    return df


def actual_outcome(gh: int, ga: int) -> int:
    """0 = home win, 1 = draw, 2 = away win."""
    if gh > ga:
        return 0
    if gh == ga:
        return 1
    return 2


def _probs_vector(prob: dict) -> list[float]:
    """[home, draw, away] renormalised to sum to 1 (guards rounding)."""
    v = [prob["home"], prob["draw"], prob["away"]]
    s = sum(v)
    if s <= 0:
        return [1 / 3, 1 / 3, 1 / 3]
    return [x / s for x in v]


# --------------------------------------------------------------------------- #
# Proper scoring rules (computed on a per-match basis, averaged by the caller).
# --------------------------------------------------------------------------- #

def log_loss_one(p: list[float], outcome: int) -> float:
    return -math.log(max(p[outcome], _EPS))


def brier_one(p: list[float], outcome: int) -> float:
    """Multiclass Brier: sum over classes of (p - onehot)^2."""
    return sum((p[k] - (1.0 if k == outcome else 0.0)) ** 2 for k in range(3))


def rps_one(p: list[float], outcome: int) -> float:
    """Ranked Probability Score for an ordered 3-outcome forecast.

    RPS = (1/(r-1)) * sum_{i=1..r-1} ( (sum_{j<=i} p_j) - (sum_{j<=i} o_j) )^2
    with r=3 ordered categories (home<draw<away).
    """
    cum_p = 0.0
    cum_o = 0.0
    total = 0.0
    for i in range(2):  # r-1 = 2 cumulative steps
        cum_p += p[i]
        cum_o += 1.0 if i == outcome else 0.0
        total += (cum_p - cum_o) ** 2
    return total / 2.0


@dataclass
class BacktestResult:
    n: int
    log_loss: float
    brier: float
    rps: float
    accuracy: float
    # over/under 2.5
    n_ou: int
    ou_log_loss: float
    ou_brier: float
    # raw per-match records for calibration / baselines
    records: list  # list of (probs_vector, outcome, p_over, over_actual)
    base_rates: tuple  # (home, draw, away) empirical frequencies

    def summary(self) -> dict:
        return {
            "n": self.n,
            "log_loss": round(self.log_loss, 5),
            "brier": round(self.brier, 5),
            "rps": round(self.rps, 5),
            "accuracy": round(self.accuracy, 5),
            "ou_n": self.n_ou,
            "ou_log_loss": round(self.ou_log_loss, 5),
            "ou_brier": round(self.ou_brier, 5),
            "base_rates": [round(x, 4) for x in self.base_rates],
        }


def run_backtest(df: pd.DataFrame, warmup: int = 800,
                 start_date: str | None = None,
                 end_date: str | None = None,
                 params: dict | None = None) -> BacktestResult:
    """Walk-forward backtest.

    For each match in chronological order:
      1. If we're past `warmup` matches (so ratings have stabilised) AND the
         match falls inside the optional [start_date, end_date] scoring window,
         PREDICT it using the ratings built from PRIOR matches only.
      2. Then UPDATE the ratings with the realised result.

    The predict-before-update ordering is what guarantees no leakage: the rating
    used to price a match never reflects that match's outcome.

    `params` (optional) overrides the tunable constants for the whole run via
    elo.override_constants — used by the calibrator to score candidate sets.
    """
    def _core() -> BacktestResult:
        table = EloTable()
        ll = bs = rp = 0.0
        hits = 0
        n = 0
        ou_ll = ou_bs = 0.0
        n_ou = 0
        records = []
        home_w = draw_c = away_w = 0

        start = pd.Timestamp(start_date) if start_date else None
        end = pd.Timestamp(end_date) if end_date else None

        for i, row in enumerate(df.itertuples(index=False)):
            gh, ga = int(row.home_score), int(row.away_score)
            neutral = _is_neutral(row.neutral)
            in_window = (
                i >= warmup
                and (start is None or row.date >= start)
                and (end is None or row.date <= end)
            )
            if in_window:
                rh = table.get(row.home_team)
                ra = table.get(row.away_team)
                lam_h, lam_a = expected_goals(rh, ra, neutral=neutral)
                probs = match_probabilities(lam_h, lam_a)
                pv = _probs_vector(probs)
                outcome = actual_outcome(gh, ga)

                ll += log_loss_one(pv, outcome)
                bs += brier_one(pv, outcome)
                rp += rps_one(pv, outcome)
                if max(range(3), key=lambda k: pv[k]) == outcome:
                    hits += 1
                n += 1

                if outcome == 0:
                    home_w += 1
                elif outcome == 1:
                    draw_c += 1
                else:
                    away_w += 1

                # Over/Under 2.5 (binary): score as 2-class log-loss/Brier.
                p_over = probs["over_2_5"]
                over_actual = 1 if (gh + ga) > 2 else 0
                p_o = min(max(p_over, _EPS), 1 - _EPS)
                ou_ll += -(over_actual * math.log(p_o) + (1 - over_actual) * math.log(1 - p_o))
                ou_bs += (p_over - over_actual) ** 2
                n_ou += 1

                records.append((pv, outcome, p_over, over_actual))

            # Update ratings AFTER predicting (no leakage).
            table.update(row.home_team, row.away_team, gh, ga, neutral=neutral)

        if n == 0:
            raise ValueError("No matches scored — check warmup / window vs data span.")

        base = (home_w / n, draw_c / n, away_w / n)
        return BacktestResult(
            n=n, log_loss=ll / n, brier=bs / n, rps=rp / n, accuracy=hits / n,
            n_ou=n_ou, ou_log_loss=ou_ll / n_ou, ou_brier=ou_bs / n_ou,
            records=records, base_rates=base,
        )

    if params:
        with elo.override_constants(**params):
            return _core()
    return _core()


# --------------------------------------------------------------------------- #
# Calibration / reliability.
# --------------------------------------------------------------------------- #

def reliability_bins(records: list, n_bins: int = 10) -> list[dict]:
    """Bin every (predicted prob, hit) pair over all 3 outcome classes.

    Each 1X2 forecast contributes 3 (prob, indicator) points: for class k the
    predicted prob is pv[k] and the indicator is 1 if outcome==k. Pooling across
    classes is the standard multiclass reliability construction.
    """
    bins = [{"lo": b / n_bins, "hi": (b + 1) / n_bins, "sum_p": 0.0,
             "sum_y": 0.0, "count": 0} for b in range(n_bins)]
    for pv, outcome, _p_over, _over in records:
        for k in range(3):
            p = pv[k]
            y = 1.0 if outcome == k else 0.0
            idx = min(int(p * n_bins), n_bins - 1)
            bins[idx]["sum_p"] += p
            bins[idx]["sum_y"] += y
            bins[idx]["count"] += 1
    for b in bins:
        if b["count"]:
            b["mean_pred"] = b["sum_p"] / b["count"]
            b["mean_obs"] = b["sum_y"] / b["count"]
        else:
            b["mean_pred"] = None
            b["mean_obs"] = None
    return bins


def expected_calibration_error(records: list, n_bins: int = 10) -> float:
    """ECE: count-weighted mean |mean_pred - mean_obs| across reliability bins."""
    bins = reliability_bins(records, n_bins)
    total = sum(b["count"] for b in bins)
    if total == 0:
        return float("nan")
    ece = 0.0
    for b in bins:
        if b["count"]:
            ece += (b["count"] / total) * abs(b["mean_pred"] - b["mean_obs"])
    return ece


def baseline_metrics(records: list, base_rates: tuple) -> dict:
    """Score a naive constant 'base-rate' forecast (same home/draw/away every
    match) on the SAME matches, for context. This is the bar any real model must
    clear to be worth anything."""
    pv = list(base_rates)
    s = sum(pv)
    pv = [x / s for x in pv]
    ll = bs = rp = 0.0
    hits = 0
    n = len(records)
    argmax = max(range(3), key=lambda k: pv[k])
    for _pred, outcome, _po, _oa in records:
        ll += log_loss_one(pv, outcome)
        bs += brier_one(pv, outcome)
        rp += rps_one(pv, outcome)
        if argmax == outcome:
            hits += 1
    return {
        "log_loss": round(ll / n, 5),
        "brier": round(bs / n, 5),
        "rps": round(rp / n, 5),
        "accuracy": round(hits / n, 5),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Walk-forward Elo/Poisson backtest")
    ap.add_argument("--since", default="2020-01-01")
    ap.add_argument("--warmup", type=int, default=800)
    ap.add_argument("--start-date", default=None, help="score only matches >= this date")
    ap.add_argument("--end-date", default=None, help="score only matches <= this date")
    args = ap.parse_args()

    df = load_matches(since=args.since)
    res = run_backtest(df, warmup=args.warmup,
                       start_date=args.start_date, end_date=args.end_date)
    ece = expected_calibration_error(res.records)
    base = baseline_metrics(res.records, res.base_rates)

    print(f"Active constants: {elo.current_constants()}")
    print(f"Scored matches:   {res.n}  (warmup {args.warmup}, since {args.since})")
    print()
    print("MODEL    1X2   log-loss={:.4f}  brier={:.4f}  rps={:.4f}  acc={:.4f}"
          .format(res.log_loss, res.brier, res.rps, res.accuracy))
    print("BASELINE 1X2   log-loss={:.4f}  brier={:.4f}  rps={:.4f}  acc={:.4f}"
          .format(base["log_loss"], base["brier"], base["rps"], base["accuracy"]))
    print(f"ECE (1X2, 10 bins): {ece:.4f}")
    print()
    print("MODEL    O/U2.5 log-loss={:.4f}  brier={:.4f}  (n={})"
          .format(res.ou_log_loss, res.ou_brier, res.n_ou))
    print(f"Base rates (H/D/A): {[round(x, 3) for x in res.base_rates]}")
    beats = res.log_loss < base["log_loss"]
    print()
    print(f"Model beats naive base-rate on log-loss: {beats} "
          f"(delta {base['log_loss'] - res.log_loss:+.4f})")


if __name__ == "__main__":
    main()
