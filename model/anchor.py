"""Per-confederation Elo anchoring — the durable fix for the cross-confederation
ratings skew (the market blend only patched priced group games).

Vanilla Elo is mis-scaled ACROSS confederations that rarely play each other: it
under-rates UEFA and over-rates CAF/AFC (Germany below Iran, Morocco #2). The market
prices cross-confederation strength correctly, so we fit a per-confederation Elo
OFFSET that brings the model's implied strength into line with the de-vigged market
on the priced group games, then RE-CENTRE it to mean-zero across the 48-team field
(fixing relative scaling without shifting the average rating, so the totals
calibration stays intact). The offsets are applied to the ratings used for WC
predictions AND the knockout/outright sims — fixing the skew at the source.

    python model/anchor.py             # fit + write model/data/confederation_offsets.json
    python model/anchor.py --no-write  # fit + report only
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFEDS = ROOT / "model" / "data" / "confederations.json"
OFFSETS = ROOT / "model" / "data" / "confederation_offsets.json"


def load_confederations() -> dict[str, str]:
    """team -> confederation (drops the leading _note key)."""
    raw = json.loads(CONFEDS.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def load_offsets() -> dict[str, float]:
    """confederation -> Elo offset. Empty (all-zero) if not fitted yet."""
    try:
        raw = json.loads(OFFSETS.read_text(encoding="utf-8"))
        return {k: float(v) for k, v in raw.items() if not k.startswith("_")}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def apply_offsets(table, offsets: dict[str, float] | None = None,
                  confeds: dict[str, str] | None = None) -> None:
    """Add each team's confederation offset to its rating, in place. A no-op for
    teams without a known confederation (e.g. non-WC sides). Canonicalises team names
    so aliased sides (USA→'United States', 'Bosnia & Herzegovina'→'…and…') are
    adjusted too. Imports only `canonical` from elo (no cycle: elo imports nothing
    of ours), so predict.py / simulate.py can call it at load time safely."""
    offsets = load_offsets() if offsets is None else offsets
    if not offsets:
        return
    from elo import canonical
    confeds = load_confederations() if confeds is None else confeds
    for team, confed in confeds.items():
        d = offsets.get(confed)
        if not d:
            continue
        key = canonical(team)
        if key in table.ratings:
            table.ratings[key] = table.ratings[key] + d


# Elo expected-score <-> two-way-probability conversion (logistic, base-10/400).
def _prob_to_gap(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return 400.0 * math.log10(p / (1.0 - p))


def fit_offsets(reference: str = "UEFA") -> dict:
    """Least-squares fit of per-confederation offsets against the de-vigged market.

    For each NEUTRAL priced group match we compute the market's and the model's
    two-way (win/loss) home probability, convert both to an Elo-equivalent gap, and
    regress the residual (market_gap - model_gap) on the confederation indicator
    difference (home_confed - away_confed). One confederation is the reference
    (offset 0) for identifiability; the result is then recentred to mean-zero across
    the field. Imports predict/elo lazily to avoid a cycle (predict imports anchor)."""
    import numpy as np
    from elo import EloTable, expected_goals, match_probabilities
    from predict import devig_market, is_true_home, RATINGS, FIXTURES

    confeds = load_confederations()
    elo = EloTable.load(RATINGS)
    fixtures = json.loads(FIXTURES.read_text())

    rows, residuals, used = [], [], 0
    confed_list = sorted(set(confeds.values()) - {reference})  # reference column dropped
    idx = {c: i for i, c in enumerate(confed_list)}

    for m in fixtures.get("matches", []):
        if m.get("status") != "SCHEDULED":
            continue
        h, a = m.get("home"), m.get("away")
        odds = m.get("odds")
        if not h or not a or h not in confeds or a not in confeds or not odds:
            continue
        if is_true_home(h, m.get("venue", "")):
            continue  # skip host-advantage games — keep offsets about confed strength only
        fair = devig_market(odds, ["home", "draw", "away"])
        if not fair:
            continue
        # two-way (drop the draw) implied home win share, market vs model
        lam_h, lam_a = expected_goals(elo.get(h), elo.get(a), neutral=True)
        mod = match_probabilities(lam_h, lam_a)
        pm = fair["home"] / (fair["home"] + fair["away"])
        pmod = mod["home"] / (mod["home"] + mod["away"])
        residual = _prob_to_gap(pm) - _prob_to_gap(pmod)

        row = [0.0] * len(confed_list)
        if confeds[h] in idx:
            row[idx[confeds[h]]] += 1.0
        if confeds[a] in idx:
            row[idx[confeds[a]]] -= 1.0
        rows.append(row)
        residuals.append(residual)
        used += 1

    X = np.array(rows, dtype=float)
    y = np.array(residuals, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    offsets = {reference: 0.0, **{c: float(beta[i]) for c, i in idx.items()}}

    # Re-centre to mean-zero across the 48-team field (preserve the average rating
    # so the totals model's strength term is undisturbed).
    counts = {}
    for c in confeds.values():
        counts[c] = counts.get(c, 0) + 1
    n = sum(counts.values())
    mean = sum(offsets.get(c, 0.0) * counts.get(c, 0) for c in offsets) / n
    offsets = {c: round(v - mean, 2) for c, v in offsets.items()}
    return {"offsets": offsets, "n_matches": used, "reference": reference}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Fit per-confederation Elo offsets vs the market")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    res = fit_offsets()
    offsets = res["offsets"]
    print(f"Fitted on {res['n_matches']} neutral priced matches (reference {res['reference']}, mean-zero):")
    for c, d in sorted(offsets.items(), key=lambda kv: kv[1]):
        print(f"  {c:10s} {d:+7.1f}")

    if not args.no_write:
        payload = {"_note": "Per-confederation Elo offsets fitted to the market (model/anchor.py). Mean-zero across the WC field.",
                   **offsets}
        OFFSETS.write_text(json.dumps(payload, indent=2))
        print(f"\nWrote {OFFSETS.relative_to(ROOT)}")
    else:
        print("\n(--no-write: offsets NOT persisted)")


if __name__ == "__main__":
    main()
