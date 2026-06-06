"""Monte-Carlo the World Cup 2026 from the model's match probabilities.

Simulates the whole tournament many times — group round-robins, the 8-best-thirds
qualification, the official R32 third-place allocation, and the knockout bracket —
to produce, per team, P(win group), P(qualify), P(reach R16/QF/SF/Final) and
P(champion). Output: site/public/data/simulation.json (read by /outrights).

This is an engagement / "what does the model think the tournament looks like" view,
NOT an edge source: outrights are high-vig and these are the model's own opinions
compounded over a month, so the tails are soft. Framed honestly on the page.

Goals are sampled as independent Poissons from the SAME expected-goals model used
everywhere (a vectorised mirror of elo.expected_goals — guarded by a test). The
whole simulation is vectorised over the N runs with NumPy, so 20k runs is seconds.

Usage:
    python model/simulate.py [--sims N] [--seed S]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

from elo import (
    EloTable, expected_goals,
    GOALS_BASELINE, GOALS_STRENGTH_REF, GOALS_STRENGTH_COEF,
    GOALS_MISMATCH_REF, GOALS_MISMATCH_COEF, GOALS_TOTAL_MIN, GOALS_TOTAL_MAX,
    ELO_TO_GOAL_DIFF, HOME_ADV,
)
from predict import is_true_home

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures" / "fixtures.json"
RATINGS = ROOT / "model" / "data" / "ratings.json"
OUT = ROOT / "site" / "public" / "data" / "simulation.json"


def lambdas(rh: np.ndarray, ra: np.ndarray, neutral: bool = True):
    """Vectorised mirror of elo.expected_goals (arrays in, arrays out).

    Reads the SAME calibration constants as the production scalar function, so it
    stays in lock-step with the model; test_simulate asserts they agree element-
    for-element. Vectorised because the scalar version's min()/max() don't
    broadcast over the N simulation runs.
    """
    adj_home = rh + (0.0 if neutral else HOME_ADV)
    pair_mean = (rh + ra) / 2.0
    strength = (pair_mean - GOALS_STRENGTH_REF) * GOALS_STRENGTH_COEF
    mismatch = (np.abs(rh - ra) - GOALS_MISMATCH_REF) * GOALS_MISMATCH_COEF
    total = np.clip(GOALS_BASELINE + strength + mismatch, GOALS_TOTAL_MIN, GOALS_TOTAL_MAX)
    half = (adj_home - ra) * ELO_TO_GOAL_DIFF
    lam_home = np.maximum(0.05, total / 2.0 + half)
    lam_away = np.maximum(0.05, total / 2.0 - half)
    return lam_home, lam_away


def _play(rng, rh, ra, neutral, draw_allowed):
    """Sample one match across all runs. Returns (goals_home, goals_away, home_wins).

    `home_wins` is the boolean advance mask: in the knockout (draw_allowed=False)
    level scores go to a 50/50 shootout.
    """
    lam_h, lam_a = lambdas(rh, ra, neutral=neutral)
    gh = rng.poisson(lam_h)
    ga = rng.poisson(lam_a)
    if draw_allowed:
        return gh, ga, None
    home_wins = gh > ga
    tie = gh == ga
    home_wins = np.where(tie, rng.random(len(gh)) < 0.5, home_wins)
    return gh, ga, home_wins


def _rank_key(rng, pts, gd, gf, n, k):
    """Composite sort key: points, then GD, then GF, then a random tiebreak.

    (Head-to-head — FIFA's first tiebreak — is approximated by the random draw;
    the effect on aggregate outright probabilities is negligible.)"""
    return pts * 1e6 + gd * 1e3 + gf + rng.random((n, k))


def _precompute_third_allocation(slot_allowed):
    """For every way 8 of the 12 groups can supply a qualifying third, find a
    valid slot->group assignment (each third-slot only accepts thirds from its
    listed groups). Returns {bitmask_of_qualifying_groups: [group_idx per slot]}.

    The official 2026 allocation lists are built so a perfect matching always
    exists; we still keep a greedy fallback for safety.
    """
    nslots = len(slot_allowed)

    def match(subset):
        # Bipartite matching: slots -> groups (augmenting path).
        slot_to_group = [-1] * nslots
        group_to_slot = {}

        def try_assign(s, seen):
            for g in slot_allowed[s]:
                if g in subset and g not in seen:
                    seen.add(g)
                    if g not in group_to_slot or try_assign(group_to_slot[g], seen):
                        slot_to_group[s] = g
                        group_to_slot[g] = s
                        return True
            return False

        for s in range(nslots):
            if not try_assign(s, set()):
                return None
        return slot_to_group

    out = {}
    for combo in combinations(range(12), nslots):
        subset = set(combo)
        assign = match(subset)
        if assign is None:  # shouldn't happen with the official lists
            assign = list(combo)  # arbitrary but valid-length fallback
        mask = sum(1 << g for g in combo)
        out[mask] = assign
    return out


def simulate(n: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    fixtures = json.loads(FIXTURES.read_text())
    elo = EloTable.load(RATINGS)
    # Confederation anchoring (model/anchor.py) — fixes the knockout/outright sims,
    # which the per-game market blend never reached. No-op if offsets aren't fitted.
    from anchor import apply_offsets
    apply_offsets(elo)
    groups = fixtures["groups"]
    matches = fixtures["matches"]

    letters = sorted(groups.keys())                 # A..L
    gidx = {l: i for i, l in enumerate(letters)}
    teams = [t for l in letters for t in groups[l]]  # 48, group-major order
    tidx = {t: i for i, t in enumerate(teams)}
    ratings = np.array([elo.get(t) for t in teams], dtype=float)
    team_group = {t: l for l in letters for t in groups[l]}

    # ---- Group stage -------------------------------------------------------
    # Per group: points/GD/GF arrays [n,4] over the four (group-major) teams.
    pts = {l: np.zeros((n, 4), dtype=np.int32) for l in letters}
    gd = {l: np.zeros((n, 4), dtype=np.int32) for l in letters}
    gf = {l: np.zeros((n, 4), dtype=np.int32) for l in letters}
    local = {l: {t: i for i, t in enumerate(groups[l])} for l in letters}

    for m in matches:
        if m.get("stage") != "GROUP":
            continue
        l = m["group"]
        h, a = m["home"], m["away"]
        rh = np.full(n, elo.get(h)); ra = np.full(n, elo.get(a))
        neutral = not is_true_home(h, m.get("venue", ""))
        gh, ga, _ = _play(rng, rh, ra, neutral, draw_allowed=True)
        ih, ia = local[l][h], local[l][a]
        pts[l][:, ih] += np.where(gh > ga, 3, np.where(gh == ga, 1, 0))
        pts[l][:, ia] += np.where(ga > gh, 3, np.where(gh == ga, 1, 0))
        gd[l][:, ih] += gh - ga; gd[l][:, ia] += ga - gh
        gf[l][:, ih] += gh; gf[l][:, ia] += ga

    # Rank each group; map local positions to global team indices.
    g_global = {l: np.array([tidx[t] for t in groups[l]]) for l in letters}
    winners = np.empty((n, 12), dtype=np.int32)
    runners = np.empty((n, 12), dtype=np.int32)
    thirds = np.empty((n, 12), dtype=np.int32)
    thirds_key = np.empty((n, 12), dtype=float)

    for l in letters:
        order = np.argsort(-_rank_key(rng, pts[l], gd[l], gf[l], n, 4), axis=1)  # [n,4]
        gi = gidx[l]
        winners[:, gi] = g_global[l][order[:, 0]]
        runners[:, gi] = g_global[l][order[:, 1]]
        thirds[:, gi] = g_global[l][order[:, 2]]
        third_pos = order[:, 2]
        rows = np.arange(n)
        thirds_key[:, gi] = (pts[l][rows, third_pos] * 1e6
                             + gd[l][rows, third_pos] * 1e3
                             + gf[l][rows, third_pos]
                             + rng.random(n) * 0.5)

    # Best 8 of the 12 third-placed teams qualify.
    top8_groups = np.argsort(-thirds_key, axis=1)[:, :8]  # group indices (0..11)
    qmask = np.zeros((n, 12), dtype=bool)
    np.put_along_axis(qmask, top8_groups, True, axis=1)
    bitmask = (qmask * (1 << np.arange(12))).sum(axis=1)   # [n]

    # ---- Resolve the knockout bracket from fixtures ------------------------
    ko = [m for m in matches if m.get("stage") in ("R32", "R16", "QF", "SF", "FINAL")]
    third_slot_strings = [m["away"] for m in ko if m.get("stage") == "R32" and m["away"].startswith("3")]
    slot_allowed = [[gidx[c] for c in s[1:].split("/")] for s in third_slot_strings]
    alloc = _precompute_third_allocation(slot_allowed)
    third_slot_index = {s: i for i, s in enumerate(third_slot_strings)}

    # Per-sim, which group fills each third-slot (vectorised by distinct bitmask).
    third_group = np.empty((n, len(slot_allowed)), dtype=np.int32)
    for mask in np.unique(bitmask):
        sel = bitmask == mask
        assign = alloc[int(mask)]
        third_group[sel] = np.array(assign)
    rows = np.arange(n)

    def resolve_slot(slot: str) -> np.ndarray:
        """Group-stage R32 slot ('1A', '2B', '3A/B/...') -> team-index array [n]."""
        if slot.startswith("3"):
            si = third_slot_index[slot]
            return thirds[rows, third_group[:, si]]
        pos, letter = slot[0], slot[1]
        table = winners if pos == "1" else runners
        return table[:, gidx[letter]]

    # ---- Simulate the knockout, tallying who reaches each round ------------
    stages = {k: np.zeros(48, dtype=np.int64) for k in ("qualify", "r16", "qf", "sf", "final", "champion")}
    win_group = np.zeros(48, dtype=np.int64)
    for gi, l in enumerate(letters):
        np.add.at(win_group, winners[:, gi], 1)

    reach_round = {"R32": "r16", "R16": "qf", "QF": "sf", "SF": "final", "FINAL": "champion"}
    winners_by_game: dict[int, np.ndarray] = {}
    counted_qualify = False
    qualified_once = np.zeros((n, 0), dtype=np.int32)

    for m in ko:
        stage = m["stage"]

        def team_for(slot: str) -> np.ndarray:
            if slot.startswith("W"):
                return winners_by_game[int(slot[1:])]
            return resolve_slot(slot)

        home = team_for(m["home"])
        away = team_for(m["away"])

        if stage == "R32":
            np.add.at(stages["qualify"], home, 1)
            np.add.at(stages["qualify"], away, 1)

        rh = ratings[home]; ra = ratings[away]
        _, _, home_wins = _play(rng, rh, ra, neutral=True, draw_allowed=False)
        win_team = np.where(home_wins, home, away)
        winners_by_game[int(m["game_no"])] = win_team
        np.add.at(stages[reach_round[stage]], win_team, 1)

    # ---- Assemble output ---------------------------------------------------
    rows_out = []
    for i, t in enumerate(teams):
        rows_out.append({
            "team": t,
            "group": team_group[t],
            "rating": round(float(ratings[i]), 1),
            "win_group": round(win_group[i] / n, 4),
            "qualify": round(stages["qualify"][i] / n, 4),
            "r16": round(stages["r16"][i] / n, 4),
            "qf": round(stages["qf"][i] / n, 4),
            "sf": round(stages["sf"][i] / n, 4),
            "final": round(stages["final"][i] / n, 4),
            "champion": round(stages["champion"][i] / n, 4),
        })
    rows_out.sort(key=lambda r: (-r["champion"], -r["final"], -r["qualify"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_sims": n,
        "seed": seed,
        "teams": rows_out,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Monte-Carlo the World Cup 2026 outrights.")
    ap.add_argument("--sims", type=int, default=20000, help="number of simulations")
    ap.add_argument("--seed", type=int, default=2026, help="RNG seed (reproducible)")
    args = ap.parse_args()

    result = simulate(args.sims, args.seed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(json.dumps(result, indent=2).encode("utf-8"))

    fav = result["teams"][0]
    print(f"Ran {args.sims} simulations (seed {args.seed}) -> {OUT.relative_to(ROOT)}")
    print(f"  favourite: {fav['team']} — champion {fav['champion']*100:.1f}% · "
          f"final {fav['final']*100:.1f}% · qualify {fav['qualify']*100:.1f}%")


if __name__ == "__main__":
    main()
