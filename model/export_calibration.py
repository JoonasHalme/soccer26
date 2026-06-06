"""Export a site-readable calibration report to site/public/data/calibration.json.

Runs ONE walk-forward backtest with the current (fitted) constants, attaches the
reliability bins for the 1X2 reliability curve, and folds in the headline
train/validation metrics and constants already recorded by calibrate.py in
model/data/calibration.json. The Astro calibration page reads the result — so
the page's numbers come from the artifact, never hardcoded.

Usage:
    python model/export_calibration.py
"""

from __future__ import annotations

import json
from pathlib import Path

import backtest  # imports elo, which loads the fitted constants at import time

ROOT = Path(__file__).resolve().parent.parent
CALIB_IN = ROOT / "model" / "data" / "calibration.json"
OUT = ROOT / "site" / "public" / "data" / "calibration.json"


def main() -> int:
    df = backtest.load_matches()
    res = backtest.run_backtest(df)
    bins = backtest.reliability_bins(res.records)
    ece = backtest.expected_calibration_error(res.records)
    baseline = backtest.baseline_metrics(res.records, res.base_rates)

    fitted = json.loads(CALIB_IN.read_text(encoding="utf-8")) if CALIB_IN.exists() else {}

    report = {
        "generated_at": fitted.get("fitted_at"),
        "method": fitted.get("method"),
        "split": fitted.get("split"),
        "constants": fitted.get("constants"),
        "handset_fallback": fitted.get("handset_fallback"),
        # train/validation table (HAND-SET vs FITTED) straight from calibrate.py
        "metrics": fitted.get("metrics"),
        # full-history backtest with the live constants — drives the curve
        "overall": {
            **res.summary(),
            "ece": round(ece, 5),
            "baseline_log_loss": round(baseline["log_loss"], 5),
            "beats_baseline": res.log_loss < baseline["log_loss"],
        },
        "reliability": [
            {
                "lo": round(b["lo"], 2),
                "hi": round(b["hi"], 2),
                "mean_pred": round(b["mean_pred"], 4) if b["count"] else None,
                "mean_obs": round(b["mean_obs"], 4) if b["count"] else None,
                "count": b["count"],
            }
            for b in bins
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote calibration report to {OUT.relative_to(ROOT)} "
          f"(n={res.n}, ECE={ece:.4f}, log-loss={res.log_loss:.4f}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
