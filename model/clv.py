"""Compute Closing-Line Value (CLV) for every settled bet.

WHAT CLV IS, HONESTLY
---------------------
CLV asks one question: did you get a better price than the market's de-vigged
CLOSING line? The closing line (the consensus the instant before kickoff) is the
sharpest, most-informed price the market produces, so it's the best available
proxy for the "true" probability. If you consistently beat it, you are very
likely picking up genuine value; if you don't, your sample of wins/losses is
probably noise. Over a small sample (a 7-game World Cup run), CLV is a far more
honest skill signal than raw P/L, because P/L is dominated by variance.

WHAT CLV IS NOT
---------------
  * It is NOT proof of profit. You can beat the close and still lose money over a
    short run (variance), or fail to beat it and win (luck).
  * It assumes the close is efficient. For a thin World Cup market that assumption
    is weaker than for, say, the NFL — treat the magnitude with humility.
  * It needs a genuine CLOSING snapshot. We de-vig the SAME way predict.py does
    (the power method — its DEVIG_METHOD default — over the full market) so the fair
    probability is apples-to-apples with how edges were measured when betting.

COMPUTATION
-----------
For each settled bet we:
  1. Find the bet's match closing_odds (consensus dict captured by
     `fetch_odds.py --closing`).
  2. De-vig the relevant market with predict.devig_market() -> fair probs.
  3. closing_fair_prob = fair prob of the bet's selection.
     closing_fair_odds  = 1 / closing_fair_prob.
     clv_pct = (bet.odds_decimal / closing_fair_odds - 1) * 100.
     (Equivalently (odds * closing_fair_prob - 1) * 100.) Positive => you beat
     the de-vigged close.
  4. Store closing_odds_decimal, closing_fair_prob, clv_pct on the bet.

Portfolio metrics: beat-rate (% bets with clv_pct > 0) and average CLV.

Usage:
    python model/clv.py            # compute + write bets.json back
    python model/clv.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from predict import devig_market  # reuse the EXACT de-vig used to find edges

# Two-tailed 95% Student-t critical values by degrees of freedom. On a tiny
# World Cup sample the t-interval (not the normal 1.96) is the honest one — with
# 6 settled bets the multiplier is 2.57, not 1.96. Beyond df=30 t ≈ z = 1.96.
_T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080,
    22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048,
    29: 2.045, 30: 2.042,
}


def _t95(df: int) -> float:
    return _T95.get(df, 1.96)


def _atomic_write(path: Path, text: str) -> None:
    """Write atomically via a temp file + os.replace so a crash can't truncate
    the source-of-truth bet log."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def mean_ci(values: list[float]) -> dict | None:
    """95% t-confidence interval for the mean of `values`.

    Needs >=2 points to estimate the spread; returns None otherwise (a single
    bet's CLV has no interval). Returns mean, the +/- margin, and the bounds.
    """
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)  # sample variance
    se = math.sqrt(var) / math.sqrt(n)
    margin = _t95(n - 1) * se
    return {
        "mean": round(mean, 2),
        "margin": round(margin, 2),
        "low": round(mean - margin, 2),
        "high": round(mean + margin, 2),
    }

ROOT = Path(__file__).resolve().parent.parent
BETS = ROOT / "bets" / "bets.json"
FIXTURES = ROOT / "fixtures" / "fixtures.json"

# Map a (market, selection) to the prob-key used in the consensus odds dict, plus
# the full set of keys for that market (needed to de-vig the whole market).
MARKET_KEYS: dict[str, list[str]] = {
    "1X2": ["home", "draw", "away"],
    "OVER_UNDER": ["over_2_5", "under_2_5"],
    "BTTS": ["btts_yes", "btts_no"],
}

SELECTION_TO_KEY: dict[str, str] = {
    "HOME": "home", "1": "home",
    "DRAW": "draw", "X": "draw",
    "AWAY": "away", "2": "away",
    "OVER_2_5": "over_2_5", "OVER": "over_2_5",
    "UNDER_2_5": "under_2_5", "UNDER": "under_2_5",
    "BTTS_YES": "btts_yes", "YES": "btts_yes",
    "BTTS_NO": "btts_no", "NO": "btts_no",
}


def selection_key(market: str, selection: str) -> str | None:
    return SELECTION_TO_KEY.get(selection.upper())


def closing_consensus(match: dict) -> dict | None:
    """Pull the consensus closing odds dict off a fixture, if snapshotted."""
    closing = match.get("closing_odds")
    if not closing:
        return None
    # Accept both the structured snapshot and a bare dict, for flexibility.
    if isinstance(closing, dict) and "consensus" in closing:
        return closing.get("consensus")
    return closing if isinstance(closing, dict) else None


def compute_clv(bet: dict, match: dict) -> dict | None:
    """Return {closing_odds_decimal, closing_fair_prob, clv_pct} or None if the
    closing market for this bet's selection isn't available/priced."""
    market = bet.get("market", "")
    keys = MARKET_KEYS.get(market)
    if not keys:
        return None  # market not de-viggable (AH/correct score/outright)
    key = selection_key(market, bet.get("selection", ""))
    if key is None or key not in keys:
        return None

    consensus = closing_consensus(match)
    if not consensus:
        return None

    fair = devig_market(consensus, keys)  # same de-vig (power method) as predict.py
    if not fair or key not in fair:
        return None

    fair_prob = fair[key]
    if fair_prob <= 0:
        return None
    fair_odds = 1.0 / fair_prob
    odds = bet.get("odds_decimal", 0) or 0
    clv_pct = (odds / fair_odds - 1.0) * 100.0
    return {
        "closing_odds_decimal": consensus.get(key),
        "closing_fair_prob": round(fair_prob, 4),
        "clv_pct": round(clv_pct, 2),
    }


def annotate_all(data: dict, fixtures: dict) -> tuple[dict, list[dict]]:
    """Attach CLV fields to every settled bet that has a closing snapshot."""
    by_id = {m["id"]: m for m in fixtures.get("matches", [])}
    changes: list[dict] = []
    for bet in data.get("bets", []):
        # Only meaningful for bets that are settled (the close has happened).
        if not bet.get("result"):
            continue
        match = by_id.get(bet.get("match_id"))
        if not match:
            continue
        clv = compute_clv(bet, match)
        if clv is None:
            continue
        if (bet.get("clv_pct") == clv["clv_pct"]
                and bet.get("closing_fair_prob") == clv["closing_fair_prob"]):
            continue  # unchanged
        bet.update(clv)
        changes.append({"id": bet.get("id"), "clv_pct": clv["clv_pct"]})
    return data, changes


def portfolio_clv(bets: list[dict]) -> dict:
    """Beat-rate (% positive CLV) and average CLV over bets carrying clv_pct."""
    rated = [b for b in bets if isinstance(b.get("clv_pct"), (int, float))]
    if not rated:
        return {"rated": 0, "beat_rate": None, "avg_clv": None}
    positive = sum(1 for b in rated if b["clv_pct"] > 0)
    avg = sum(b["clv_pct"] for b in rated) / len(rated)
    ci = mean_ci([b["clv_pct"] for b in rated])
    return {
        "rated": len(rated),
        "beat_rate": round(positive / len(rated), 3),
        "avg_clv": round(avg, 2),
        "clv_ci": ci,  # {mean, margin, low, high} or None for n<2
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print CLV without writing bets.json")
    args = parser.parse_args()

    data = json.loads(BETS.read_text(encoding="utf-8"))
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))

    bets = data.get("bets", [])
    if not bets:
        print("No bets logged yet - no CLV to compute (bets/bets.json is empty).")
        return 0

    settled = [b for b in bets if b.get("result")]
    have_closing = sum(1 for m in fixtures.get("matches", []) if m.get("closing_odds"))
    print(f"{len(settled)} settled bet(s); {have_closing} fixture(s) have a closing snapshot.")

    data, changes = annotate_all(data, fixtures)
    port = portfolio_clv(data.get("bets", []))

    if not changes:
        print("No CLV updates - no settled bet has a matching closing snapshot yet.")
    else:
        for c in changes:
            sign = "+" if c["clv_pct"] >= 0 else ""
            print(f"  {c['id']}: CLV {sign}{c['clv_pct']}%")

    ci = port.get("clv_ci")
    ci_str = f" (95% CI {ci['low']}..{ci['high']})" if ci else ""
    print(f"Portfolio: rated={port['rated']} beat_rate={port['beat_rate']} "
          f"avg_clv={port['avg_clv']}{ci_str}")

    if args.dry_run:
        print("[dry-run] no file written.")
        return 0
    if changes:
        _atomic_write(BETS, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote CLV onto {len(changes)} bet(s) in {BETS.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
