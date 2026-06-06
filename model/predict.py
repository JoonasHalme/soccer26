"""Generate predictions for every SCHEDULED match in fixtures.json.

Outputs `site/public/data/predictions.json`. The site reads this file as a
static artifact — no runtime dependencies on Python.

Usage:
    python model/predict.py
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from elo import (
    EloTable, expected_goals, match_probabilities, asian_probabilities,
    derived_markets,
)

VENUE_COUNTRY = {
    "Mexico City": "Mexico",
    "Guadalajara (Zapopan)": "Mexico",
    "Monterrey (Guadalupe)": "Mexico",
    "Toronto": "Canada",
    "Vancouver": "Canada",
    "Atlanta": "USA", "Boston (Foxborough)": "USA", "Dallas (Arlington)": "USA",
    "Houston": "USA", "Kansas City": "USA", "Los Angeles (Inglewood)": "USA",
    "Miami (Miami Gardens)": "USA", "New York/New Jersey (East Rutherford)": "USA",
    "Philadelphia": "USA", "San Francisco Bay Area (Santa Clara)": "USA", "Seattle": "USA",
}


def is_true_home(home_team: str, venue: str) -> bool:
    """Home advantage applies only when the listed home team is the host
    nation AND the venue is inside that nation."""
    return VENUE_COUNTRY.get(venue) == home_team


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures" / "fixtures.json"
RATINGS = ROOT / "model" / "data" / "ratings.json"
OUT = ROOT / "site" / "public" / "data" / "predictions.json"


EDGE_THRESHOLD = 0.05  # only surface selections whose edge exceeds 5%

# Each market's selections must be de-vigged TOGETHER, because the bookmaker
# overround (the "vig") is baked into the full set of mutually-exclusive,
# exhaustive outcomes for that market. 1/odds for each outcome sums to >1; the
# excess IS the margin. We can only recover a fair probability by normalising the
# whole set to sum to 1. Comparing the model to a single raw 1/odds (as the old
# code did) leaves the vig in and overstates every edge by roughly the margin.
MARKETS: dict[str, list[tuple[str, str]]] = {
    "1X2": [("HOME", "home"), ("DRAW", "draw"), ("AWAY", "away")],
    "OVER_UNDER": [("OVER_2_5", "over_2_5"), ("UNDER_2_5", "under_2_5")],
    "BTTS": [("BTTS_YES", "btts_yes"), ("BTTS_NO", "btts_no")],
}


def raw_implied(odds_decimal: float) -> float:
    return 1.0 / odds_decimal if odds_decimal and odds_decimal > 0 else 0.0


# How to strip the bookmaker overround from a fully-priced market.
#
# "multiplicative" (proportional): divide every 1/odds by the book sum. Simple,
# but it removes the SAME PROPORTION of margin from every outcome, which is known
# to be wrong: bookmakers load relatively more margin onto longshots (the
# favourite-longshot bias). Proportional de-vig therefore leaves longshots with
# too much fair probability and favourites with too little — so spurious "edges"
# pile up on draws and weak away sides.
#
# "power": find the single exponent k with  sum_i (1/odds_i)**k == 1, then take
# (1/odds_i)**k as the fair probability. Because each raw implied prob is < 1,
# raising to k>1 shrinks small (longshot) probs proportionally MORE than large
# (favourite) ones — which is exactly the correction the favourite-longshot bias
# calls for. It's the cheap, parameter-free cousin of Shin's model and the
# standard general-purpose choice. We default to it for the fair baseline that
# edges are measured against.
DEVIG_METHOD = "power"


def _power_devig(raws: dict[str, float]) -> dict[str, float]:
    """Fit the exponent k so the powered implied probs sum to 1, via bisection.

    f(k) = sum(p**k) is continuous and strictly decreasing in k for p in (0,1);
    f(1) = overround > 1 and f(k) -> 0 as k -> inf, so a unique root k > 1 exists.
    """
    lo, hi = 1.0, 100.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if sum(p ** mid for p in raws.values()) > 1.0:
            lo = mid
        else:
            hi = mid
    k = (lo + hi) / 2.0
    powered = {key: p ** k for key, p in raws.items()}
    # Renormalise away the tiny bisection residual so the set sums to exactly 1.
    total = sum(powered.values())
    return {key: v / total for key, v in powered.items()}


def devig_market(odds: dict, prob_keys: list[str], method: str = DEVIG_METHOD) -> dict[str, float]:
    """Return fair (vig-free) implied probabilities for one market.

    Both methods normalise the market's 1/odds to sum to 1 (see DEVIG_METHOD for
    why the default is "power", not "multiplicative"). Returns {} if the market
    isn't fully priced — we only de-vig a complete set, since a half-priced market
    has no recoverable overround.
    """
    raws = {k: raw_implied(odds.get(k)) for k in prob_keys}
    if any(v <= 0 for v in raws.values()):
        return {}
    if method == "power":
        return _power_devig(raws)
    overround = sum(raws.values())  # > 1 by the bookmaker margin
    return {k: v / overround for k, v in raws.items()}


# Which per-book field carries a given outcome's price. The books[] entries
# written by fetch_odds.py keep h2h (home/draw/away) and totals (over/under)
# separate; BTTS is unpriced by the World Cup odds endpoint, so it has no book.
_BOOK_FIELD = {
    "home": "h2h", "draw": "h2h", "away": "h2h",
    "over_2_5": "totals", "under_2_5": "totals",
}


def best_price(books: list[dict] | None, prob_key: str) -> tuple[float | None, str | None]:
    """Highest decimal odds for one outcome across all sportsbooks, and which book.

    This is the line-shopping price — the best you could actually take. Returns
    (None, None) when no book quotes the outcome (e.g. BTTS, or a thin market).
    """
    field = _BOOK_FIELD.get(prob_key)
    if not field:
        return None, None
    best_odds: float | None = None
    best_book: str | None = None
    for book in books or []:
        price = (book.get(field) or {}).get(prob_key)
        if price and (best_odds is None or price > best_odds):
            best_odds, best_book = price, book.get("title") or book.get("key")
    return best_odds, best_book


def find_edges(prob: dict, odds: dict | None, books: list[dict] | None = None,
               model_raw: dict | None = None) -> list[dict]:
    """Surface bets where the model probability beats the DE-VIGGED (fair) bookie
    probability by more than EDGE_THRESHOLD.

    Each surfaced edge is enriched with the best available book price. Note the
    deliberate asymmetry: the *surfacing* test uses the de-vigged CONSENSUS price
    (is this a genuine disagreement with the market's fair assessment?), but the
    best-price value is measured RAW — `model_prob - 1/best_odds` and the EV
    `model_prob*best_odds - 1`. We must NOT de-vig the best line: de-vigging
    normalises a market's prices back to sum-to-1, which would cancel out exactly
    the margin you capture by line-shopping. The raw figure is what you actually
    realise at the price you can take.
    """
    if not odds:
        return []
    edges = []
    for market, selections in MARKETS.items():
        prob_keys = [pk for _, pk in selections]
        fair = devig_market(odds, prob_keys)
        if not fair:
            continue  # market not fully priced for this fixture
        for selection, prob_key in selections:
            fair_prob = fair[prob_key]
            edge = prob[prob_key] - fair_prob   # `prob` is the BLENDED forecast (our call)
            if edge > EDGE_THRESHOLD:
                entry = {
                    "market": market,
                    "selection": selection,
                    "model_prob": round(prob[prob_key], 4),       # our published (blended) call
                    "implied_prob": round(fair_prob, 4),          # fair, vig-free
                    "devig_method": DEVIG_METHOD,                  # how the vig was stripped
                    "raw_implied_prob": round(raw_implied(odds.get(prob_key)), 4),
                    "odds_decimal": odds.get(prob_key),           # consensus price
                    "edge_pct": round(edge * 100, 2),             # STAKED edge: forecast − fair = w·(raw gap)
                }
                if model_raw is not None and prob_key in model_raw:
                    # The pre-blend (anchored-model) probability and its RAW gap vs the
                    # market. The staked edge above is this gap shrunk by the blend
                    # weight (edge = w · raw_gap) — surfacing both keeps "edge" honest.
                    entry["model_raw_prob"] = round(model_raw[prob_key], 4)
                    entry["raw_edge_pct"] = round((model_raw[prob_key] - fair_prob) * 100, 2)
                b_odds, b_book = best_price(books, prob_key)
                if b_odds:
                    entry["best_odds"] = b_odds
                    entry["best_book"] = b_book
                    # Realisable edge & EV at the best obtainable price (raw — see
                    # docstring). best_edge_pct compares the model to the price's
                    # own break-even (1/odds); ev_pct is expected return per unit.
                    entry["best_edge_pct"] = round((prob[prob_key] - 1.0 / b_odds) * 100, 2)
                    entry["ev_pct"] = round((prob[prob_key] * b_odds - 1.0) * 100, 2)
                edges.append(entry)
    return sorted(edges, key=lambda e: e["edge_pct"], reverse=True)


# Market-blend prior. Our Elo can't see squad quality and is mis-scaled ACROSS
# confederations (no anchor between e.g. CAF/AFC and UEFA, which rarely interplay),
# so on cross-confederation mismatches it disagrees wildly with a deep multi-book
# market that prices exactly those things. We shrink the published forecast toward
# the market where odds exist.
#
# The weight is DISAGREEMENT-AWARE, not flat. The empirical finding (see
# docs/backlog.md TASK-047) is decisive: the model disagrees with a 29-book market
# by a median 15 points, and the BIGGEST disagreements are precisely the broken
# (confederation-skew) games — a flat weight high enough to keep the model
# meaningful re-surfaces exactly those. So we trust the model LESS the more it
# disagrees: per market group, w = BASE / (1 + (D/HALF)^2) where D is the group's
# max |model - market| gap. Small disagreement -> ~BASE; a large gap collapses the
# weight toward 0 (defer to the market). This keeps only moderate, plausible
# disagreements as edges and kills the structural-error ones. Pure Elo is still
# kept as `probabilities` (the instrument reading) and drives the score-shape
# markets and the knockout/outright sims, which have no odds to blend against.
MARKET_BLEND_BASE_WEIGHT = 0.6     # model weight when it AGREES with the market
BLEND_DISAGREEMENT_HALF = 0.17     # group gap at which the model's weight halves

# The market groups we can blend / snapshot (everything the books price for us).
_BLENDABLE = (["home", "draw", "away"], ["over_2_5", "under_2_5"])


def _group_weight(prob: dict, fair: dict, keys: list[str]) -> float:
    """Disagreement-aware model weight for one market group: BASE shrunk by how far
    the model's probabilities sit from the de-vigged market over that group."""
    d = max(abs(prob[k] - fair[k]) for k in keys)
    return MARKET_BLEND_BASE_WEIGHT / (1.0 + (d / BLEND_DISAGREEMENT_HALF) ** 2)


def market_snapshot(odds: dict | None) -> dict | None:
    """De-vigged (power-method) fair probabilities for every priced market, flat.
    Returns None if nothing is fully priced. Used for the 'vs market' display and
    as the blend target."""
    out: dict[str, float] = {}
    for keys in _BLENDABLE:
        fair = devig_market(odds or {}, keys)
        for k, v in fair.items():
            out[k] = round(v, 4)
    return out or None


def blend_forecast(prob: dict, odds: dict | None) -> tuple[dict, bool, float | None]:
    """Shrink the pure-model probabilities toward the de-vigged market.

    Returns (forecast, blended, w_1x2). Each priced market group is replaced by
    `w*model + (1-w)*fair` with a DISAGREEMENT-AWARE w per group (see
    _group_weight); a blend of two sum-to-1 distributions over the same outcomes is
    itself sum-to-1, so no renormalisation is needed. Unpriced groups (BTTS,
    expected_goals, and everything in a knockout fixture) pass through at the
    pure-model value, `blended` is False when no group could be blended, and w_1x2
    is the effective 1X2 weight (for display) or None when 1X2 wasn't priced.
    """
    forecast = dict(prob)
    blended = False
    w_1x2: float | None = None
    for keys in _BLENDABLE:
        fair = devig_market(odds or {}, keys)
        if not fair:
            continue  # group not fully priced -> leave pure-model
        w = _group_weight(prob, fair, keys)
        if keys[0] == "home":
            w_1x2 = w
        for k in keys:
            forecast[k] = round(w * prob[k] + (1.0 - w) * fair[k], 4)
        blended = True
    return forecast, blended, w_1x2


def find_divergences(prob: dict, odds: dict | None, books: list[dict] | None = None) -> list[dict]:
    """Every priced outcome's SIGNED model-vs-fair gap — no edge threshold, both
    directions. Powers the /divergence tracker ("where does the model most
    disagree with the market?").

    Distinct from find_edges in two ways: (1) no EDGE_THRESHOLD filter, so small
    and zero gaps are kept; (2) it keeps NEGATIVE deltas too — outcomes the market
    rates MORE likely than the model — which find_edges drops because they're not
    value bets. The fair baseline is the SAME de-vigged (power-method) probability,
    so the two views never tell different stories about the same price.
    """
    if not odds:
        return []
    out = []
    for market, selections in MARKETS.items():
        prob_keys = [pk for _, pk in selections]
        fair = devig_market(odds, prob_keys)
        if not fair:
            continue  # market not fully priced
        for selection, prob_key in selections:
            entry = {
                "market": market,
                "selection": selection,
                "model_prob": round(prob[prob_key], 4),
                "fair_prob": round(fair[prob_key], 4),
                "delta": round(prob[prob_key] - fair[prob_key], 4),  # model − fair, signed
            }
            b_odds, b_book = best_price(books, prob_key)
            if b_odds:
                entry["best_odds"] = b_odds
                entry["best_book"] = b_book
            out.append(entry)
    return out


# Hash-chain genesis: the `prev` of the very first ledger entry.
GENESIS_HASH = "0" * 64


def ledger_entry_hash(entry: dict) -> str:
    """SHA-256 over an entry's canonical JSON (sorted keys). Each new ledger entry
    stores the hash of the PREVIOUS entry in its `prev` field, so the entries form a
    tamper-evident chain: silently altering any historical entry changes its hash and
    breaks the `prev` link of every entry after it. (This makes mid-history rewrites
    detectable; it does NOT by itself prove the publisher didn't rewrite the WHOLE
    chain — that needs an external anchor, which is a documented limitation.)"""
    return hashlib.sha256(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()


def main() -> None:
    fixtures = json.loads(FIXTURES.read_text())
    elo = EloTable.load(RATINGS)
    # Anchor the ratings across confederations (the source fix for the Elo
    # mis-scaling; see model/anchor.py). No-op if offsets haven't been fitted.
    from anchor import apply_offsets
    apply_offsets(elo)
    predictions = []

    for match in fixtures.get("matches", []):
        if match.get("status") != "SCHEDULED":
            continue
        home, away = match.get("home"), match.get("away")
        if not home or not away or any(t.startswith(("W", "L")) and t[1:].isdigit() for t in (home, away)):
            continue
        if any(re.match(r"^[123]", t) for t in (home, away)):
            continue
        neutral = not is_true_home(home, match.get("venue", ""))
        lam_home, lam_away = expected_goals(elo.get(home), elo.get(away), neutral=neutral)
        probs = match_probabilities(lam_home, lam_away)
        odds = match.get("odds")
        books = match.get("books")
        # Market-blended forecast: the PUBLISHED, actionable call. Pure `probabilities`
        # stays the raw instrument reading (drives score-shape markets + sims); the
        # blend anchors 1X2/O-U toward the market so edges aren't manufactured by the
        # model's cross-confederation mis-scaling. See blend_forecast() for the why.
        forecast, blended, w_1x2 = blend_forecast(probs, odds)
        predictions.append({
            "match_id": match["id"],
            "home": home,
            "away": away,
            "kickoff": match.get("kickoff"),
            "ratings": {"home": round(elo.get(home), 1), "away": round(elo.get(away), 1)},
            "probabilities": {k: round(v, 4) if isinstance(v, float) else v for k, v in probs.items()},
            # De-vigged market snapshot (what the books fairly imply) + the blended
            # forecast we actually publish. `weight` is the model's share of the blend.
            "market": market_snapshot(odds),
            "forecast": {
                **{k: round(v, 4) if isinstance(v, float) else v for k, v in forecast.items()},
                "blended": blended,
                # The effective 1X2 model weight for THIS match (confidence-adjusted —
                # lower where the model disagreed more with the market). Drives the
                # "Model vs market" panel's "X% model / Y% market" caption.
                "weight": round(w_1x2, 4) if w_1x2 is not None else MARKET_BLEND_BASE_WEIGHT,
            },
            # Asian handicap + Asian totals from the same score matrix (display only —
            # no AH odds are sourced yet, so no AH edges are surfaced).
            "asian": asian_probabilities(lam_home, lam_away),
            # Double-chance / Draw-No-Bet / top correct scores from the same matrix
            # (display only — no odds sourced for these, so no edges surfaced).
            "derived": derived_markets(lam_home, lam_away),
            # Edges compare the BLENDED forecast (our real call) to the market, so a
            # huge pure-model disagreement no longer surfaces as a full-size "edge".
            "edges": find_edges(forecast, odds, books, model_raw=probs),
            # Divergences keep the RAW model vs market (the diagnostic the blend
            # corrects) — that's the point of the /divergence transparency view.
            "divergences": find_divergences(probs, odds, books),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Append-only prediction ARCHIVE (per match_id). predictions.json only ever holds
    # the currently-SCHEDULED matches, so a match's prediction vanishes once it kicks
    # off — but the post-match "we said X" card and the live-calibration scorecard need
    # the PRE-KICKOFF prediction preserved. We refresh each scheduled match's entry here
    # (so it tracks the latest pre-kickoff number) and never touch finished matches
    # (they're no longer in `predictions`), freezing their last pre-kickoff prediction.
    ARCHIVE = OUT.parent / "predictions_archive.json"
    try:
        archive = json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {}
        if not isinstance(archive, dict):
            archive = {}
    except (json.JSONDecodeError, OSError):
        archive = {}
    archive_ts = datetime.now(timezone.utc).isoformat()
    for p in predictions:
        # Archive the PUBLISHED forecast (blended where priced), not the raw model —
        # the live calibration scorecard should grade the numbers we actually showed.
        pr = p["forecast"]
        archive[p["match_id"]] = {
            "home": pr["home"], "draw": pr["draw"], "away": pr["away"],
            "blended": pr.get("blended", False),
            "locked_at": archive_ts,
        }
    ARCHIVE.write_bytes(json.dumps(archive, indent=2, sort_keys=True).encode("utf-8"))

    # Idempotent provenance. `generated_at` would change the file bytes on every
    # run, so a naive write breaks the tamper-evidence promise: the published
    # file's hash would stop matching the last ledger line on a no-op re-run. We
    # instead key off a timestamp-free content hash of the picks themselves and
    # ONLY rewrite predictions.json / its hash sidecar / the ledger when the picks
    # actually change. That keeps the live file <-> hash sidecar <-> latest ledger
    # entry perfectly in sync, so "re-hash the live file and it matches the ledger"
    # always holds, and identical re-runs leave everything untouched.
    content_digest = hashlib.sha256(
        json.dumps(predictions, sort_keys=True).encode("utf-8")
    ).hexdigest()
    LEDGER = OUT.parent / "predictions_ledger.json"
    try:
        ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
        if not isinstance(ledger, list):
            ledger = []
    except (json.JSONDecodeError, OSError):
        ledger = []

    if ledger and ledger[-1].get("content_sha256") == content_digest and OUT.exists():
        print(f"Predictions unchanged since ledger entry #{len(ledger)} "
              f"({ledger[-1]['generated_at'][:16]}Z) — nothing rewritten.")
        return

    generated_at = datetime.now(timezone.utc).isoformat()
    payload = json.dumps({
        "generated_at": generated_at,
        "predictions": predictions,
    }, indent=2)
    # write_bytes (not write_text): on Windows write_text translates \n -> \r\n,
    # which would make the on-disk bytes differ from the bytes we hash below and
    # silently break "re-hash the live file and it matches the ledger". Writing the
    # exact UTF-8 bytes keeps the file byte-identical to what `digest` covers.
    OUT.write_bytes(payload.encode("utf-8"))

    # SHA-256 of the EXACT bytes just written (timestamp included), in a sibling
    # file. Any later edit to predictions.json changes this digest, so a published
    # set can be proven to predate a kickoff.
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    HASH_OUT = OUT.with_suffix(".hash.json")
    HASH_OUT.write_text(json.dumps({
        "file": OUT.name,
        "generated_at": generated_at,
        "algorithm": "sha256",
        "sha256": digest,
    }, indent=2))
    print(f"Wrote {len(predictions)} predictions to {OUT.relative_to(ROOT)}")
    print(f"  sha256={digest[:16]}... recorded in {HASH_OUT.name}")

    # Append-only HASH-CHAINED ledger: each distinct prediction set leaves an
    # immutable line so the public record can't be silently cherry-picked. Every
    # entry carries `prev` = the hash of the entry before it, so altering any past
    # entry breaks the chain from that point on (see ledger_entry_hash). We only
    # reach here when the picks changed, so every line is a real new set.
    prev = ledger_entry_hash(ledger[-1]) if ledger else GENESIS_HASH
    ledger.append({
        "generated_at": generated_at,
        "algorithm": "sha256",
        "sha256": digest,
        "content_sha256": content_digest,
        "prev": prev,
        "n_predictions": len(predictions),
        "file": OUT.name,
    })
    LEDGER.write_text(json.dumps(ledger, indent=2))
    print(f"  ledger: appended entry #{len(ledger)} (prev={prev[:12]}…) -> {LEDGER.name}")


if __name__ == "__main__":
    main()
