"""Tests for the betting-model math changed in the HIGH-priority audit fixes.

Run from the repo root:
    python -m pytest tests/ -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "model"
sys.path.insert(0, str(MODEL))

import elo  # noqa: E402
import predict  # noqa: E402


# --------------------------------------------------------------------------- #
# H1 — de-vig normalisation
# --------------------------------------------------------------------------- #

def test_devig_1x2_sums_to_one():
    """Fair probabilities of a fully-priced 1X2 market must sum to exactly 1."""
    odds = {"home": 1.42, "draw": 4.4, "away": 8.5}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    assert fair  # non-empty
    assert pytest.approx(sum(fair.values()), abs=1e-9) == 1.0


def test_devig_over_under_sums_to_one():
    odds = {"over_2_5": 2.05, "under_2_5": 1.71}
    fair = predict.devig_market(odds, ["over_2_5", "under_2_5"])
    assert pytest.approx(sum(fair.values()), abs=1e-9) == 1.0


def test_devig_is_lower_than_raw_implied():
    """De-vigging removes the overround, so each fair prob is <= raw 1/odds
    (the raw set sums to >1, the fair set to exactly 1)."""
    odds = {"home": 1.42, "draw": 4.4, "away": 8.5}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    for k in odds:
        assert fair[k] <= predict.raw_implied(odds[k]) + 1e-12


def test_devig_incomplete_market_returns_empty():
    """A market that isn't fully priced has no recoverable overround."""
    assert predict.devig_market({"home": 2.0, "draw": 3.5}, ["home", "draw", "away"]) == {}
    assert predict.devig_market({"over_2_5": 2.0}, ["over_2_5", "under_2_5"]) == {}


def test_power_devig_sums_to_one():
    """The power method must also produce a fair set summing to exactly 1."""
    odds = {"home": 1.42, "draw": 4.4, "away": 8.5}
    fair = predict.devig_market(odds, ["home", "draw", "away"], method="power")
    assert pytest.approx(sum(fair.values()), abs=1e-9) == 1.0


def test_power_devig_shrinks_longshots_more_than_multiplicative():
    """Favourite-longshot correction: vs proportional de-vig, the power method
    assigns LESS fair probability to the longshot and MORE to the favourite."""
    odds = {"home": 1.42, "draw": 4.4, "away": 8.5}  # away is the longshot
    power = predict.devig_market(odds, ["home", "draw", "away"], method="power")
    mult = predict.devig_market(odds, ["home", "draw", "away"], method="multiplicative")
    assert power["away"] < mult["away"]      # longshot shrunk
    assert power["home"] > mult["home"]      # favourite lifted


def test_power_devig_is_the_default():
    """devig_market with no method arg uses the power method (DEVIG_METHOD)."""
    assert predict.DEVIG_METHOD == "power"
    odds = {"home": 1.42, "draw": 4.4, "away": 8.5}
    default = predict.devig_market(odds, ["home", "draw", "away"])
    power = predict.devig_market(odds, ["home", "draw", "away"], method="power")
    assert default == power


def test_power_devig_no_vig_is_identity():
    """A market with no overround (fair book) should pass through unchanged:
    k solves to 1, so the powered probs equal the raw implied probs."""
    odds = {"home": 2.0, "away": 2.0}  # 1/2 + 1/2 = 1.0, zero margin
    fair = predict.devig_market(odds, ["home", "away"], method="power")
    assert fair["home"] == pytest.approx(0.5, abs=1e-6)
    assert fair["away"] == pytest.approx(0.5, abs=1e-6)


def test_find_edges_records_raw_gap_when_given_model_raw():
    """With model_raw passed, each edge carries the pre-blend gap, and the staked
    edge is a shrunk version of it (TASK quant-A1: edge_pct = w · raw_edge_pct)."""
    odds = {"home": 2.0, "draw": 3.6, "away": 4.0}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    # A realistic raw model that sums to 1 with a +17pt home disagreement (and the
    # rest spread so HOME is the dominant gap, surviving the confidence blend).
    raw = _flat_prob(home=fair["home"] + 0.17,
                     draw=fair["draw"] - 0.085, away=fair["away"] - 0.085)
    forecast, _, _ = predict.blend_forecast(raw, odds)
    edges = predict.find_edges(forecast, odds, model_raw=raw)
    home = next(e for e in edges if e["selection"] == "HOME")
    assert home["model_raw_prob"] == pytest.approx(round(raw["home"], 4))
    assert home["raw_edge_pct"] == pytest.approx(17.0, abs=0.5)   # raw gap preserved
    assert home["edge_pct"] < home["raw_edge_pct"]               # staked < raw (blend shrank it)


def test_find_edges_uses_fair_not_raw():
    """The reported implied_prob is the de-vigged one; edge is model - fair."""
    odds = {"home": 1.42, "draw": 4.4, "away": 8.5}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    # Pick a model that beats the fair home prob by >5%.
    prob = {k: 0.0 for k in
            ("home", "draw", "away", "over_2_5", "under_2_5", "btts_yes", "btts_no")}
    prob["home"] = fair["home"] + 0.10
    edges = predict.find_edges(prob, odds)
    home_edge = next(e for e in edges if e["selection"] == "HOME")
    assert home_edge["implied_prob"] == pytest.approx(round(fair["home"], 4))
    assert home_edge["edge_pct"] == pytest.approx(10.0, abs=0.5)


# --------------------------------------------------------------------------- #
# TASK-003 — best-book price / line-shopping
# --------------------------------------------------------------------------- #

def test_best_price_picks_highest_odds_and_book():
    books = [
        {"title": "Pinnacle", "h2h": {"home": 2.05, "draw": 3.4, "away": 3.8}, "totals": {}},
        {"title": "Bet365", "h2h": {"home": 2.15, "draw": 3.3, "away": 3.7}, "totals": {}},
        {"title": "Bwin", "h2h": {"home": 2.10, "draw": 3.5, "away": 3.6}, "totals": {}},
    ]
    odds, book = predict.best_price(books, "home")
    assert odds == 2.15 and book == "Bet365"
    assert predict.best_price(books, "btts_yes") == (None, None)  # never book-priced
    assert predict.best_price([], "home") == (None, None)


def test_best_price_edge_beats_consensus_when_book_is_sharper():
    """A surfaced edge enriched with a best book that beats the de-vigged
    consensus price yields a realisable best-edge >= the consensus edge."""
    odds = {"home": 2.0, "draw": 3.6, "away": 4.0}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    prob = {k: 0.0 for k in
            ("home", "draw", "away", "over_2_5", "under_2_5", "btts_yes", "btts_no")}
    prob["home"] = fair["home"] + 0.10
    # A book offering 2.30 on home clearly beats the de-vigged fair price (1/2.30
    # = 0.435 < fair home ~0.47), so shopping adds value on top of the edge.
    books = [{"title": "SharpBook", "h2h": {"home": 2.30, "draw": 3.6, "away": 4.0}, "totals": {}}]
    edges = predict.find_edges(prob, odds, books)
    home = next(e for e in edges if e["selection"] == "HOME")
    assert home["best_odds"] == 2.30 and home["best_book"] == "SharpBook"
    assert home["best_edge_pct"] >= home["edge_pct"]
    assert home["ev_pct"] == pytest.approx((prob["home"] * 2.30 - 1) * 100, abs=0.1)


def test_find_edges_without_books_omits_best_price():
    odds = {"home": 1.42, "draw": 4.4, "away": 8.5}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    prob = {k: 0.0 for k in
            ("home", "draw", "away", "over_2_5", "under_2_5", "btts_yes", "btts_no")}
    prob["home"] = fair["home"] + 0.10
    edges = predict.find_edges(prob, odds)  # no books arg
    home = next(e for e in edges if e["selection"] == "HOME")
    assert "best_odds" not in home and "ev_pct" not in home


# --------------------------------------------------------------------------- #
# predict.py gap coverage
# --------------------------------------------------------------------------- #

def _flat_prob(**over):
    p = {k: 0.0 for k in
         ("home", "draw", "away", "over_2_5", "under_2_5", "btts_yes", "btts_no")}
    p.update(over)
    return p


def test_partially_priced_market_surfaces_no_edge_but_complete_one_does():
    """A market priced only on home+draw (no away) must surface no edge for it,
    while a fully-priced O/U market in the SAME fixture still does."""
    # 1X2 incomplete (away missing) -> not de-viggable.
    # O/U complete -> de-viggable, and the model crushes OVER.
    odds = {"home": 2.0, "draw": 3.5, "over_2_5": 2.0, "under_2_5": 2.0}
    fair_ou = predict.devig_market(odds, ["over_2_5", "under_2_5"])
    prob = _flat_prob(home=0.99, over_2_5=fair_ou["over_2_5"] + 0.20)
    edges = predict.find_edges(prob, odds)
    markets = {e["market"] for e in edges}
    assert "1X2" not in markets       # incomplete -> no edge for that market
    assert "OVER_UNDER" in markets    # complete -> edge still surfaced
    over = next(e for e in edges if e["selection"] == "OVER_2_5")
    assert over["edge_pct"] == pytest.approx(20.0, abs=0.5)


def test_best_price_skips_book_with_missing_price():
    """best_price ignores a book that doesn't quote the outcome (None/missing)
    and picks the valid book."""
    books = [
        {"title": "NoHomeBook", "h2h": {"draw": 3.4, "away": 3.8}, "totals": {}},
        {"title": "NullHomeBook", "h2h": {"home": None, "draw": 3.3}, "totals": {}},
        {"title": "GoodBook", "h2h": {"home": 2.20, "draw": 3.5}, "totals": {}},
    ]
    odds, book = predict.best_price(books, "home")
    assert odds == 2.20 and book == "GoodBook"


def test_raw_implied_guards_zero_and_none():
    assert predict.raw_implied(0) == 0.0
    assert predict.raw_implied(None) == 0.0
    assert predict.raw_implied(2.0) == pytest.approx(0.5)


def test_devig_hand_computed_exact_half():
    """Fully hand-computed de-vig: odds {2.0, 4.0, 4.0} -> raws {0.5, 0.25, 0.25},
    overround 1.0, so the fair HOME prob is EXACTLY 0.5. Asserting the literal 0.5
    (not a value derived the same way as the code) catches a normalisation bug
    that would otherwise co-drift through both sides of the comparison."""
    odds = {"home": 2.0, "draw": 4.0, "away": 4.0}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    assert fair["home"] == pytest.approx(0.5, abs=1e-12)
    assert fair["draw"] == pytest.approx(0.25, abs=1e-12)
    assert fair["away"] == pytest.approx(0.25, abs=1e-12)
    # And find_edges reports that exact fair prob as implied_prob.
    prob = _flat_prob(home=0.60)  # 10% over fair -> surfaces
    edges = predict.find_edges(prob, odds)
    home = next(e for e in edges if e["selection"] == "HOME")
    assert home["implied_prob"] == pytest.approx(0.5, abs=1e-9)
    assert home["edge_pct"] == pytest.approx(10.0, abs=0.01)


# --------------------------------------------------------------------------- #
# TASK-045 — divergence tracker (signed model-vs-fair gaps, both directions)
# --------------------------------------------------------------------------- #

def test_divergences_keep_both_signs_and_all_outcomes():
    """Unlike find_edges, find_divergences keeps every priced outcome including
    negative gaps (market rates it MORE likely than the model)."""
    odds = {"home": 2.0, "draw": 4.0, "away": 4.0}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    # Model is below fair on home, above on away — opposite-signed deltas.
    prob = _flat_prob(home=fair["home"] - 0.10, draw=fair["draw"],
                      away=fair["away"] + 0.10)
    div = predict.find_divergences(prob, odds)
    by_sel = {d["selection"]: d for d in div}
    assert by_sel["HOME"]["delta"] == pytest.approx(-0.10, abs=1e-6)  # kept, negative
    assert by_sel["AWAY"]["delta"] == pytest.approx(0.10, abs=1e-6)   # kept, positive
    # All three 1X2 outcomes present (no threshold filtering).
    assert {"HOME", "DRAW", "AWAY"} <= set(by_sel)


def test_divergence_fair_matches_devig():
    """The fair baseline reported is exactly the de-vigged probability."""
    odds = {"home": 2.0, "draw": 4.0, "away": 4.0}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    div = predict.find_divergences(_flat_prob(home=0.5), odds)
    home = next(d for d in div if d["selection"] == "HOME")
    assert home["fair_prob"] == pytest.approx(round(fair["home"], 4), abs=1e-9)
    assert home["delta"] == pytest.approx(round(0.5 - fair["home"], 4), abs=1e-9)


def test_divergences_empty_without_odds():
    assert predict.find_divergences(_flat_prob(home=0.5), None) == []


def test_divergences_skip_incomplete_market():
    """A half-priced market contributes no divergence rows (can't de-vig it)."""
    odds = {"home": 2.0, "draw": 3.5, "over_2_5": 2.0, "under_2_5": 2.0}
    div = predict.find_divergences(_flat_prob(home=0.5, over_2_5=0.6), odds)
    markets = {d["market"] for d in div}
    assert "1X2" not in markets        # away missing -> incomplete
    assert "OVER_UNDER" in markets     # fully priced


# --------------------------------------------------------------------------- #
# TASK-050 — prev-hash chained ledger (tamper-evident across history)
# --------------------------------------------------------------------------- #

def _chain(entries):
    """Link a list of bare entries into a prev-hash chain like predict.main does."""
    prev = predict.GENESIS_HASH
    out = []
    for e in entries:
        linked = {**e, "prev": prev}
        out.append(linked)
        prev = predict.ledger_entry_hash(linked)
    return out


def _chain_valid(ledger):
    prev = predict.GENESIS_HASH
    for e in ledger:
        if e.get("prev") != prev:
            return False
        prev = predict.ledger_entry_hash(e)
    return True


def test_ledger_chain_links_and_validates():
    led = _chain([{"sha256": "a", "n": 1}, {"sha256": "b", "n": 2}, {"sha256": "c", "n": 3}])
    assert led[0]["prev"] == predict.GENESIS_HASH
    assert led[1]["prev"] == predict.ledger_entry_hash(led[0])
    assert _chain_valid(led)


def test_ledger_chain_detects_history_tampering():
    """Silently altering a PAST entry must break the chain from that point."""
    led = _chain([{"sha256": "a"}, {"sha256": "b"}, {"sha256": "c"}])
    assert _chain_valid(led)
    led[0]["sha256"] = "TAMPERED"  # rewrite entry 0 without re-linking
    assert not _chain_valid(led)   # entry 1's prev no longer matches


def test_ledger_entry_hash_is_order_independent():
    """The hash is over sorted keys, so field insertion order doesn't change it."""
    a = {"sha256": "x", "n": 1, "prev": "0"}
    b = {"prev": "0", "n": 1, "sha256": "x"}
    assert predict.ledger_entry_hash(a) == predict.ledger_entry_hash(b)


# --------------------------------------------------------------------------- #
# TASK-046 — market-blend prior (shrink model toward de-vigged market)
# --------------------------------------------------------------------------- #

def _expected_weff(model, fair, keys):
    d = max(abs(model[k] - fair[k]) for k in keys)
    return predict.MARKET_BLEND_BASE_WEIGHT / (1 + (d / predict.BLEND_DISAGREEMENT_HALF) ** 2)


def test_blend_is_disagreement_weighted_average():
    """forecast = w*model + (1-w)*fair, where w is the disagreement-aware weight."""
    odds = {"home": 1.40, "draw": 4.55, "away": 7.80}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    model = _flat_prob(home=0.34, draw=0.28, away=0.38)
    w = _expected_weff(model, fair, ["home", "draw", "away"])
    fc, blended, w_1x2 = predict.blend_forecast(model, odds)
    assert blended
    assert w_1x2 == pytest.approx(w, abs=1e-4)
    for k in ("home", "draw", "away"):
        assert fc[k] == pytest.approx(w * model[k] + (1 - w) * fair[k], abs=1e-4)


def test_bigger_disagreement_gets_less_model_weight():
    """The more the model disagrees with the market, the lower its effective weight
    (the core of the confidence-aware blend)."""
    odds = {"home": 1.40, "draw": 4.55, "away": 7.80}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    near = _flat_prob(home=fair["home"] - 0.03, draw=fair["draw"], away=fair["away"] + 0.03)
    far = _flat_prob(home=fair["home"] - 0.30, draw=fair["draw"], away=fair["away"] + 0.30)
    _, _, w_near = predict.blend_forecast(near, odds)
    _, _, w_far = predict.blend_forecast(far, odds)
    assert w_far < w_near <= predict.MARKET_BLEND_BASE_WEIGHT


def test_blend_pulls_toward_market_and_sums_to_one():
    """A model that rates the favourite far below the market gets pulled up; the
    1X2 forecast still sums to 1."""
    odds = {"home": 1.40, "draw": 4.55, "away": 7.80}  # market home ~0.69 fair
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    model = _flat_prob(home=0.34, draw=0.28, away=0.38)
    fc, _, _ = predict.blend_forecast(model, odds)
    assert model["home"] < fc["home"] < fair["home"]      # pulled toward market
    assert fc["home"] + fc["draw"] + fc["away"] == pytest.approx(1.0, abs=1e-3)


def test_huge_disagreement_collapses_to_market_no_edge():
    """A 30pt pure-model disagreement (the confederation-skew signature) collapses
    the model's weight so far that the blended forecast surfaces NO edge."""
    odds = {"home": 1.40, "draw": 4.55, "away": 7.80}
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    model = _flat_prob(home=fair["home"] - 0.30, draw=fair["draw"], away=fair["away"] + 0.30)
    fc, _, _ = predict.blend_forecast(model, odds)
    assert predict.find_edges(fc, odds) == []                # killed
    assert abs(fc["away"] - fair["away"]) < 0.05             # forecast ~ market


def test_blend_without_odds_is_identity():
    """No odds (knockout fixture) -> forecast is the pure model, blended False."""
    model = _flat_prob(home=0.5, draw=0.3, away=0.2)
    fc, blended, w_1x2 = predict.blend_forecast(model, None)
    assert blended is False and w_1x2 is None
    assert fc["home"] == 0.5 and fc["draw"] == 0.3 and fc["away"] == 0.2


def test_market_snapshot_matches_devig():
    odds = {"home": 1.40, "draw": 4.55, "away": 7.80, "over_2_5": 1.83, "under_2_5": 1.89}
    snap = predict.market_snapshot(odds)
    fair = predict.devig_market(odds, ["home", "draw", "away"])
    assert snap["home"] == pytest.approx(round(fair["home"], 4), abs=1e-9)
    assert "over_2_5" in snap and "under_2_5" in snap
    assert predict.market_snapshot(None) is None


# --------------------------------------------------------------------------- #
# H2 — expected goals now varies across matchups
# --------------------------------------------------------------------------- #

def test_expected_total_goals_varies_by_matchup():
    """The whole point of the fix: total expected goals is no longer constant."""
    totals = {
        round(sum(elo.expected_goals(rh, ra, neutral=True)), 3)
        for rh, ra in [
            (1500, 1500), (1850, 1820), (1850, 1300),
            (1300, 1280), (1700, 1500), (1600, 1600),
        ]
    }
    assert len(totals) >= 4, f"totals barely vary: {totals}"


def test_total_goals_roughly_independent_of_absolute_strength():
    """Total goals should NOT depend much on absolute pair strength. Calibrating
    GOALS_STRENGTH_COEF to walk-forward O/U log-loss (TASK-048) drove it to ~0 —
    absolute strength predicts the WINNER, not the goal count. The old model used a
    positive coef and ran systematically hot on the strong WC field. Holding the
    rating gap equal, two strong sides and two weak sides should total within a
    narrow band."""
    strong = sum(elo.expected_goals(1850, 1800, neutral=True))
    weak = sum(elo.expected_goals(1350, 1300, neutral=True))
    assert abs(strong - weak) < 0.15, f"strength still moves totals too much: {strong:.3f} vs {weak:.3f}"


def test_bigger_mismatch_raises_total():
    """A lopsided game totals more than an even one at the same pair-mean."""
    even = sum(elo.expected_goals(1700, 1700, neutral=True))
    lopsided = sum(elo.expected_goals(1900, 1500, neutral=True))  # same mean 1700
    assert lopsided > even


def test_totals_level_is_calibrated_to_realised_rate():
    """Characterisation guard for TASK-048: a typical WC-strength match (pair-mean
    and gap at the centring refs) must predict P(over2.5) near the realised
    international over-rate (~0.49), NOT the old hot ~0.55. Catches a regression in
    GOALS_BASELINE / the totals shape that would re-introduce the over-bias."""
    rh = elo.GOALS_STRENGTH_REF + elo.GOALS_MISMATCH_REF / 2.0
    ra = elo.GOALS_STRENGTH_REF - elo.GOALS_MISMATCH_REF / 2.0   # mean=ref, gap=ref
    p_over = elo.match_probabilities(*elo.expected_goals(rh, ra, neutral=True))["over_2_5"]
    assert 0.44 <= p_over <= 0.52, f"totals level drifted: P(over2.5)={p_over:.3f} (target ~0.49)"


def test_total_goals_bounded():
    """Even extreme inputs stay in a realistic football range."""
    for rh, ra in [(3000, 1000), (1000, 3000), (1000, 1000), (2000, 2000)]:
        total = elo.expected_total_goals(rh, ra)
        assert elo.GOALS_TOTAL_MIN <= total <= elo.GOALS_TOTAL_MAX


def test_home_advantage_shifts_split_not_total():
    """Home advantage redistributes goals between sides but doesn't inflate the
    total (it isn't a goal-creating term)."""
    total_neutral = sum(elo.expected_goals(1700, 1600, neutral=True))
    total_home = sum(elo.expected_goals(1700, 1600, neutral=False))
    assert total_neutral == pytest.approx(total_home, abs=1e-9)
    lam_h_n, _ = elo.expected_goals(1700, 1600, neutral=True)
    lam_h_h, _ = elo.expected_goals(1700, 1600, neutral=False)
    assert lam_h_h > lam_h_n  # home side expected to score more with the bump


# --------------------------------------------------------------------------- #
# elo.py sanity checks
# --------------------------------------------------------------------------- #

def test_probabilities_sum_to_one():
    probs = elo.match_probabilities(1.6, 1.1)
    assert pytest.approx(probs["home"] + probs["draw"] + probs["away"], abs=1e-6) == 1.0
    assert pytest.approx(probs["over_2_5"] + probs["under_2_5"], abs=1e-6) == 1.0
    assert pytest.approx(probs["btts_yes"] + probs["btts_no"], abs=1e-6) == 1.0


def test_stronger_home_team_has_higher_win_prob():
    lam_h, lam_a = elo.expected_goals(1900, 1400, neutral=True)
    probs = elo.match_probabilities(lam_h, lam_a)
    assert probs["home"] > probs["away"]


def test_expected_score_monotonic_in_rating():
    e = elo.EloTable(ratings={"Strong": 1800, "Weak": 1200})
    assert e.expected_score("Strong", "Weak", neutral=True) > 0.5
    assert e.expected_score("Weak", "Strong", neutral=True) < 0.5


def test_dixon_coles_raises_draw_vs_independent():
    """The DC low-score correction should not lower the draw probability relative
    to pure independent Poisson (rho<0 lifts 0-0/1-1)."""
    lam_h, lam_a = 1.4, 1.3
    dc = elo.match_probabilities(lam_h, lam_a, rho=elo.DIXON_COLES_RHO)
    indep = elo.match_probabilities(lam_h, lam_a, rho=0.0)
    assert dc["draw"] >= indep["draw"]


def test_update_writes_canonical_key():
    """L1 regression: an aliased name must accumulate under its canonical key."""
    alias = next(iter(elo.NAME_ALIASES))  # e.g. 'USA'
    canon = elo.NAME_ALIASES[alias]
    e = elo.EloTable()
    e.update(home=alias, away="Nowhere", gh=3, ga=0, neutral=True)
    assert canon in e.ratings
    assert alias not in e.ratings  # not split across the raw spelling
