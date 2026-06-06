"""Fractional-Kelly staking.

The Kelly criterion sizes a bet to the edge AND the price: it maximises the
long-run growth rate of the bankroll. For a decimal-odds bet,

    f* = (b·p - q) / b

where b = odds - 1 (net fractional odds), p = model probability of winning, and
q = 1 - p. f* is the fraction of the bankroll to stake. f* <= 0 means no +EV
bet (don't stake).

We never bet full Kelly: it's optimal only if the probabilities are exactly
right, and ours aren't (the model is well-calibrated but not perfect). Betting a
FRACTION of Kelly (¼ is the common professional default) sacrifices a little
growth for a large reduction in variance and in the damage done by mis-estimated
edges. We also hard-cap the stake at a percentage of bankroll so a single
mispriced longshot can't command a huge stake.
"""

from __future__ import annotations


def full_kelly_fraction(model_prob: float, odds: float) -> float:
    """Unscaled Kelly fraction f* for a decimal-odds bet. <= 0 ⇒ no edge."""
    if odds is None or odds <= 1 or not (0 < model_prob < 1):
        return 0.0
    b = odds - 1.0
    q = 1.0 - model_prob
    f = (b * model_prob - q) / b
    return f if f > 0 else 0.0


def kelly_stake(
    model_prob: float,
    odds: float,
    bankroll: float,
    fraction: float = 0.25,
    cap_pct: float = 5.0,
) -> dict:
    """Suggested stake for one bet.

    Returns the unscaled Kelly fraction, the fractional-Kelly stake (rounded to
    cents), whether the cap bound it, and the cap amount. A non-positive edge
    yields a zero stake.
    """
    f_star = full_kelly_fraction(model_prob, odds)
    cap_amount = round(bankroll * cap_pct / 100.0, 2)
    raw = bankroll * f_star * fraction
    capped = raw > cap_amount
    stake = round(min(raw, cap_amount), 2)
    return {
        "full_kelly": round(f_star, 4),
        "fraction": fraction,
        "stake": stake,
        "capped": capped,
        "cap_amount": cap_amount,
    }
