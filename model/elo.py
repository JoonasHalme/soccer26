"""Elo + Poisson goal model for international football.

The Elo rating maps strength difference to a win probability for a single team.
We convert that into expected goals for each side, then sample the result
distribution via independent Poissons. That gives P(home), P(draw), P(away),
plus over/under and BTTS probabilities for the same match in one pass.

Calibration constants are intentionally simple — tune `K`, `HOME_ADV`, and
`GOALS_BASELINE` against historical results once we have the dataset wired up.
"""

from __future__ import annotations

import json
import math
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.stats import poisson


# --------------------------------------------------------------------------- #
# Calibration constants.
#
# These were originally HAND-SET (see the docstring caveat above and
# docs/improvements.md L3). They are now FITTED by minimising walk-forward
# log-loss on historical internationals — see model/calibrate.py and the report
# in docs/calibration.md. The fitted values live in model/data/calibration.json
# and are loaded at import time; the literals below are the documented hand-set
# FALLBACKS used when that file is absent (e.g. a fresh checkout before
# calibration has been run).
#
# Anything that consumes these (predict.py, train_ratings.py, backtest.py) reads
# the module-level names, so loading the JSON here propagates the fitted values
# everywhere without further changes.
# --------------------------------------------------------------------------- #

# Hand-set fallbacks (documented provenance: conventional Elo/eloratings values).
# GOALS_BASELINE + the two totals shape coefficients are fit to an OVER/UNDER
# log-loss objective (not the 1X2 objective — see calibrate.py), because they
# drive totals, which the 1X2 objective barely constrains.
_DEFAULTS = {
    "K": 32.0,
    "HOME_ADV": 65.0,
    "GOALS_BASELINE": 2.55,
    "ELO_TO_GOAL_DIFF": 0.0040,
    "DIXON_COLES_RHO": -0.05,
    "GOALS_STRENGTH_COEF": 0.0011,
    "GOALS_MISMATCH_COEF": 0.0008,
}

DEFAULT_RATING = 1500.0

_CALIBRATION_PATH = Path(__file__).resolve().parent / "data" / "calibration.json"


def _load_calibrated() -> dict:
    """Load fitted constants from calibration.json, falling back to hand-set."""
    params = dict(_DEFAULTS)
    if _CALIBRATION_PATH.exists():
        try:
            data = json.loads(_CALIBRATION_PATH.read_text())
            fitted = data.get("constants", data)  # accept either shape
            for k in _DEFAULTS:
                if k in fitted and isinstance(fitted[k], (int, float)):
                    params[k] = float(fitted[k])
        except (json.JSONDecodeError, OSError):
            pass  # corrupt/unreadable -> hand-set fallbacks
    return params


_CALIBRATED = _load_calibrated()

K = _CALIBRATED["K"]
HOME_ADV = _CALIBRATED["HOME_ADV"]
GOALS_BASELINE = _CALIBRATED["GOALS_BASELINE"]
ELO_TO_GOAL_DIFF = _CALIBRATED["ELO_TO_GOAL_DIFF"]

# --- Matchup-dependent total-goals model (fixes the structurally-constant O/U) ---
#
# The old expected_goals() split a fixed GOALS_BASELINE between the two sides, so
# lam_home + lam_away was identical (2.55) for EVERY fixture. That made Over/Under
# and BTTS structurally constant and the "edges" they produced meaningless.
#
# We now let the expected TOTAL goals vary by matchup using two principled signals:
#
#   1. Absolute strength of the two teams, measured RELATIVE TO THE TYPICAL
#      WORLD-CUP SIDE (GOALS_STRENGTH_REF ≈ the mean rating of the 48 qualified
#      nations, not the 1500 global average — qualified teams are all well above
#      1500). Stronger-than-typical pairs trend higher-scoring; weaker pairs
#      (debutants, minnows) trend lower. Centring on the WC mean keeps this term
#      roughly zero-mean across the tournament instead of biasing every total up.
#
#   2. Mismatch (rating gap). Lopsided games tend to produce MORE total goals than
#      strength alone implies — the favourite piles them on while the underdog
#      still concedes — so a larger |rating gap| nudges the total up modestly.
#      Evenly matched games are tighter/lower-scoring.
#
# Both effects are bounded so totals stay in a realistic football range. The
# constants are deliberately modest; they should be tuned against a backtest (see
# docs/improvements.md H3) but already make O/U matchup-specific instead of a
# single fixed number.
# NOTE on scale: these reference points are EXPRESSED IN THE RATING SCALE, which
# depends on K. After calibration (K≈101) the trained ratings spread wider than
# under the old hand-set K=32, so the references were re-measured on the fitted
# scale to keep both terms ~zero-mean across the 2026 field (mean qualified Elo
# ≈1826, mean group-fixture |gap| ≈177). The COEFs are kept modest/hand-set —
# total-goals shape isn't part of the 1X2 log-loss objective, so it's documented
# rather than fitted; see docs/calibration.md "limitations".
GOALS_STRENGTH_REF = 1826.0    # ≈ mean Elo of the 48 qualified WC 2026 sides (fitted scale)
GOALS_MISMATCH_REF = 177.0     # ≈ mean |rating gap| across WC 2026 group fixtures (fitted scale)
# The two coefficients ARE fitted now (to walk-forward O/U log-loss — see calibrate.py
# fit_totals). The fit found strength_coef ≈ 0 (total goals barely depend on absolute
# pair strength — strength predicts the WINNER, not the goal count; the old +0.0011 made
# the model run hot on the strong WC field) and a larger mismatch_coef (lopsided games
# genuinely produce more total goals). Literals above are the hand-set fallbacks.
GOALS_STRENGTH_COEF = _CALIBRATED["GOALS_STRENGTH_COEF"]  # goals per Elo pt of pair-mean above ref
GOALS_MISMATCH_COEF = _CALIBRATED["GOALS_MISMATCH_COEF"]  # goals per Elo pt of |home-away| gap
GOALS_TOTAL_MIN = 1.6
GOALS_TOTAL_MAX = 3.8

# Maps the team names used in fixtures.json to the canonical names used by the
# martj42/international_results CSV (where the ratings come from).
NAME_ALIASES: dict[str, str] = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}


# Names of the constants the calibrator is allowed to fit. Kept small to avoid
# overfitting (5 free parameters against thousands of matches).
TUNABLE = ("K", "HOME_ADV", "GOALS_BASELINE", "ELO_TO_GOAL_DIFF", "DIXON_COLES_RHO",
           "GOALS_STRENGTH_COEF", "GOALS_MISMATCH_COEF")


@contextmanager
def override_constants(**params):
    """Temporarily set module-level calibration constants.

    The model math (expected_goals/expected_total_goals/match_probabilities and
    the Elo update) reads module globals, so the backtest and calibrator can
    evaluate CANDIDATE parameter sets through the *exact same* functions used in
    production by swapping the globals inside a `with` block — no duplicated math,
    no leakage of fitted values into other runs. Only names in TUNABLE are
    accepted; everything is restored on exit (even on exception).
    """
    g = globals()
    saved = {}
    for name, value in params.items():
        if name not in TUNABLE:
            raise KeyError(f"{name!r} is not a tunable constant ({TUNABLE})")
        saved[name] = g[name]
        g[name] = float(value)
    try:
        yield
    finally:
        g.update(saved)


def current_constants() -> dict:
    """Snapshot the active tunable constants (for reporting/persistence)."""
    g = globals()
    return {name: g[name] for name in TUNABLE}


def canonical(team: str) -> str:
    return NAME_ALIASES.get(team, team)


@dataclass
class EloTable:
    ratings: dict[str, float] = field(default_factory=dict)

    def get(self, team: str) -> float:
        return self.ratings.get(canonical(team), DEFAULT_RATING)

    def expected_score(self, home: str, away: str, neutral: bool = False) -> float:
        ra = self.get(home) + (0 if neutral else HOME_ADV)
        rb = self.get(away)
        return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))

    def update(self, home: str, away: str, gh: int, ga: int, neutral: bool = False) -> None:
        expected = self.expected_score(home, away, neutral)
        if gh > ga:
            actual = 1.0
        elif gh < ga:
            actual = 0.0
        else:
            actual = 0.5
        goal_diff = abs(gh - ga)
        multiplier = math.log(max(goal_diff, 1) + 1) * (2.2 / (abs(self.get(home) - self.get(away)) * 0.001 + 2.2))
        delta = K * multiplier * (actual - expected)
        # Write to the canonical key so an aliased spelling can't split a team's
        # rating across two keys (get() canonicalises but the write previously
        # used the raw name — latent bug per docs/improvements.md L1).
        self.ratings[canonical(home)] = self.get(home) + delta
        self.ratings[canonical(away)] = self.get(away) - delta

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.ratings, indent=2, sort_keys=True))

    @classmethod
    def load(cls, path: Path) -> "EloTable":
        if not path.exists():
            return cls()
        return cls(ratings=json.loads(path.read_text()))


def expected_total_goals(rating_home: float, rating_away: float) -> float:
    """Matchup-specific expected TOTAL goals.

    Starts from GOALS_BASELINE and adjusts by (a) how strong the pair is in
    absolute terms (mean rating vs. the 1500 population average) and (b) how
    lopsided the matchup is (|rating gap|). The home-advantage Elo bump is a
    redistribution between the two sides, not a creation of goals, so it does NOT
    enter the total here — it only shifts the split in expected_goals().
    """
    pair_mean = (rating_home + rating_away) / 2.0
    strength_term = (pair_mean - GOALS_STRENGTH_REF) * GOALS_STRENGTH_COEF
    # Centre the mismatch term on the typical WC gap so it, too, is ~zero-mean
    # across the tournament rather than only ever pushing totals up.
    mismatch_term = (abs(rating_home - rating_away) - GOALS_MISMATCH_REF) * GOALS_MISMATCH_COEF
    total = GOALS_BASELINE + strength_term + mismatch_term
    return min(GOALS_TOTAL_MAX, max(GOALS_TOTAL_MIN, total))


def expected_goals(rating_home: float, rating_away: float, neutral: bool = False) -> tuple[float, float]:
    """Map Elo strength to expected goals per side.

    The TOTAL is matchup-dependent (see expected_total_goals); the rating
    difference (plus home advantage) then decides how that total is split between
    the two sides via ELO_TO_GOAL_DIFF.
    """
    adj_home = rating_home + (0 if neutral else HOME_ADV)
    diff = adj_home - rating_away
    total = expected_total_goals(rating_home, rating_away)
    half_diff = diff * ELO_TO_GOAL_DIFF
    lam_home = max(0.05, total / 2.0 + half_diff)
    lam_away = max(0.05, total / 2.0 - half_diff)
    return lam_home, lam_away


# Dixon-Coles low-score dependence parameter. Independent Poisson under-predicts
# the 0-0/1-0/0-1/1-1 cells (real football has positive correlation at low scores),
# which systematically under-states draws and over-states the favourite. A negative
# rho lifts 0-0 and 1-1 and trims 1-0/0-1, nudging draw probability up. -0.05 is a
# conventional, conservative hand-set value; the fitted value (when present) is
# loaded from calibration.json above. See docs/calibration.md.
DIXON_COLES_RHO = _CALIBRATED["DIXON_COLES_RHO"]


def _dixon_coles_tau(i: int, j: int, lam: float, mu: float, rho: float) -> float:
    """Multiplicative correction applied to the four lowest-score cells."""
    if i == 0 and j == 0:
        return 1.0 - lam * mu * rho
    if i == 0 and j == 1:
        return 1.0 + lam * rho
    if i == 1 and j == 0:
        return 1.0 + mu * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(lam_home: float, lam_away: float, max_goals: int = 10,
                 rho: float = DIXON_COLES_RHO) -> np.ndarray:
    """The Dixon-Coles-corrected joint scoreline distribution (rows=home goals,
    cols=away goals), normalised to sum to 1. Shared by match_probabilities and
    asian_probabilities so the two never drift apart."""
    h = poisson.pmf(np.arange(max_goals + 1), lam_home)
    a = poisson.pmf(np.arange(max_goals + 1), lam_away)
    m = np.outer(h, a)
    for i in (0, 1):
        for j in (0, 1):
            m[i, j] *= _dixon_coles_tau(i, j, lam_home, lam_away, rho)
    m /= m.sum()
    return m


def match_probabilities(lam_home: float, lam_away: float, max_goals: int = 10,
                        rho: float = DIXON_COLES_RHO) -> dict:
    """Return 1X2, over/under 2.5, BTTS probabilities.

    Builds the score matrix from two Poissons, then applies the Dixon-Coles
    low-score correction (rho) so draws and 0-0/1-1 scorelines aren't under-
    predicted the way pure independent Poisson does.
    """
    score_matrix_ = score_matrix(lam_home, lam_away, max_goals, rho)

    p_home = np.tril(score_matrix_, -1).sum()
    p_draw = np.trace(score_matrix_)
    p_away = np.triu(score_matrix_, 1).sum()

    total_goals = np.add.outer(np.arange(max_goals + 1), np.arange(max_goals + 1))
    p_over_2_5 = score_matrix_[total_goals > 2].sum()

    btts = score_matrix_.copy()
    btts[0, :] = 0
    btts[:, 0] = 0
    p_btts = btts.sum()

    return {
        "home": float(p_home),
        "draw": float(p_draw),
        "away": float(p_away),
        "over_2_5": float(p_over_2_5),
        "under_2_5": float(1 - p_over_2_5),
        "btts_yes": float(p_btts),
        "btts_no": float(1 - p_btts),
        "expected_goals": {"home": lam_home, "away": lam_away},
    }


# Asian-handicap and Asian-total lines shown per match. Half lines (.5) can't push;
# whole lines can. Quarter lines (split stakes) are deliberately omitted for clarity.
ASIAN_HANDICAP_LINES = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5)
ASIAN_TOTAL_LINES = (1.5, 2.5, 3.5)


def asian_probabilities(lam_home: float, lam_away: float, max_goals: int = 10,
                        rho: float = DIXON_COLES_RHO) -> dict:
    """Asian-handicap and Asian-total probabilities, derived from the SAME
    Dixon-Coles score matrix the 1X2/O-U markets use (so they're internally
    consistent). Handicaps are from the HOME team's perspective: `line` is the
    goals added to home's score, so -0.5 ⇒ home must win, +0.5 ⇒ draw-no-bet for
    the underdog, etc. Returns cover/push probabilities per line.
    """
    m = score_matrix(lam_home, lam_away, max_goals, rho)
    idx = np.arange(max_goals + 1)
    diff = np.subtract.outer(idx, idx)   # home_goals - away_goals
    total = np.add.outer(idx, idx)

    # Margin distribution P(home - away = d) and total distribution P(total = t).
    margins = {int(d): float(m[diff == d].sum()) for d in range(-max_goals, max_goals + 1)}
    totals = {int(t): float(m[total == t].sum()) for t in range(0, 2 * max_goals + 1)}

    handicaps = []
    for line in ASIAN_HANDICAP_LINES:
        home_p = push_p = away_p = 0.0
        for d, p in margins.items():
            adj = d + line
            if adj > 1e-9:
                home_p += p
            elif adj < -1e-9:
                away_p += p
            else:
                push_p += p
        entry = {"line": round(line, 2), "home": round(home_p, 4), "away": round(away_p, 4)}
        if push_p > 1e-9:
            entry["push"] = round(push_p, 4)
        handicaps.append(entry)

    totals_out = []
    for line in ASIAN_TOTAL_LINES:
        over = sum(p for t, p in totals.items() if t > line)
        under = sum(p for t, p in totals.items() if t < line)
        totals_out.append({"line": line, "over": round(over, 4), "under": round(under, 4)})

    return {"handicaps": handicaps, "totals": totals_out}


def derived_markets(lam_home: float, lam_away: float, top_scores: int = 6,
                    max_goals: int = 10, rho: float = DIXON_COLES_RHO) -> dict:
    """Markets that fall straight out of the Dixon-Coles score matrix the rest of
    the model already builds — no new fitting, just different sums over the same
    cells, so they stay internally consistent with the 1X2 numbers.

    - double_chance: P(home or draw), P(home or away), P(draw or away).
    - dnb (Draw-No-Bet): 1X2 with the draw refunded, i.e. renormalised over the
      home/away cells only — home/(home+away) and away/(home+away).
    - correct_scores: the `top_scores` most likely exact scorelines (display only).
    """
    m = score_matrix(lam_home, lam_away, max_goals, rho)
    p_home = float(np.tril(m, -1).sum())
    p_draw = float(np.trace(m))
    p_away = float(np.triu(m, 1).sum())

    decisive = p_home + p_away
    dnb = {
        "home": round(p_home / decisive, 4) if decisive > 0 else 0.0,
        "away": round(p_away / decisive, 4) if decisive > 0 else 0.0,
    }

    # Flatten to (home_goals, away_goals, prob) and take the most likely scorelines.
    cells = [(int(i), int(j), float(m[i, j]))
             for i in range(max_goals + 1) for j in range(max_goals + 1)]
    cells.sort(key=lambda c: c[2], reverse=True)
    correct_scores = [
        {"home": i, "away": j, "prob": round(p, 4)}
        for i, j, p in cells[:top_scores]
    ]

    return {
        "double_chance": {
            "home_or_draw": round(p_home + p_draw, 4),
            "home_or_away": round(p_home + p_away, 4),
            "draw_or_away": round(p_draw + p_away, 4),
        },
        "dnb": dnb,
        "correct_scores": correct_scores,
    }
