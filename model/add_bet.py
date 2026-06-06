"""Quick, low-friction bet logging from a model edge.

The project's whole point is an auditable bet log, but hand-editing bets.json is
error-prone (wrong match_id, forgotten edge field, edge_pct in the wrong units).
This pre-fills a schema-valid entry straight from predictions.json so capturing a
bet is one command — which is what makes the track record actually get kept.

Usage:
    # reference an edge as <match_id>:<SELECTION>
    python model/add_bet.py --edge m-007:HOME --odds 2.15
    python model/add_bet.py --edge m-013:OVER_2_5 --odds 1.95 --stake 3 --source Pinnacle
    python model/add_bet.py --edge m-007:HOME --odds 2.15 --dry-run

The stake defaults to the fractional-Kelly suggestion (staking.py) off the
current bankroll (starting_bankroll + realised P/L). Edge probability/edge are
copied from the model; odds_decimal is the price YOU actually took (--odds).
Exits non-zero if the edge id doesn't resolve or the resulting bet is invalid.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import staking
from validate_bets import validate_discipline, validate_match_id, validate_schema

ROOT = Path(__file__).resolve().parent.parent
BETS = ROOT / "bets" / "bets.json"
SCHEMA = ROOT / "bets" / "schema.json"
FIXTURES = ROOT / "fixtures" / "fixtures.json"
PREDICTIONS = ROOT / "site" / "public" / "data" / "predictions.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path: Path, text: str) -> None:
    """Write `text` to `path` atomically: write a sibling temp file then
    os.replace() it into place. A crash mid-write can't truncate the
    source-of-truth bet log — the original file stays intact until the rename."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def find_edge(predictions: list[dict], match_id: str, selection: str) -> dict | None:
    for p in predictions:
        if p["match_id"] == match_id:
            for e in p.get("edges", []):
                if e["selection"].upper() == selection.upper():
                    return e
            # match found but selection not among its edges
            avail = ", ".join(e["selection"] for e in p.get("edges", [])) or "(none)"
            raise SystemExit(
                f"No edge '{selection}' on {match_id}. Surfaced edges: {avail}"
            )
    return None


def next_bet_id(bets: list[dict]) -> str:
    nums = [int(b["id"].split("-")[-1]) for b in bets
            if isinstance(b.get("id"), str) and b["id"].split("-")[-1].isdigit()]
    return f"b-{(max(nums) + 1) if nums else 1:04d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edge", required=True,
                    help="Edge reference as <match_id>:<SELECTION>, e.g. m-007:HOME")
    ap.add_argument("--odds", required=True, type=float,
                    help="Decimal price you actually took for this selection")
    ap.add_argument("--stake", type=float, default=None,
                    help="Stake; defaults to the fractional-Kelly suggestion")
    ap.add_argument("--source", default=None,
                    help="Sportsbook; defaults to the edge's best book or 'unknown'")
    ap.add_argument("--rationale", default=None, help="Optional free-text reasoning")
    ap.add_argument("--dry-run", action="store_true", help="Print the bet, don't write")
    args = ap.parse_args()

    if ":" not in args.edge:
        raise SystemExit("--edge must be <match_id>:<SELECTION>, e.g. m-007:HOME")
    match_id, selection = args.edge.split(":", 1)

    if not PREDICTIONS.exists():
        raise SystemExit(f"{PREDICTIONS} not found - run model/predict.py first.")
    predictions = _load(PREDICTIONS).get("predictions", [])
    edge = find_edge(predictions, match_id, selection)
    if edge is None:
        raise SystemExit(f"match_id '{match_id}' not found in predictions.json")

    data = _load(BETS)
    bets = data.get("bets", [])
    bankroll = data.get("starting_bankroll", 0) + sum(
        b["pnl"] for b in bets if isinstance(b.get("pnl"), (int, float))
    )

    if args.stake is not None:
        stake = round(args.stake, 2)
    else:
        sug = staking.kelly_stake(
            edge["model_prob"], args.odds, bankroll,
            fraction=data.get("kelly_fraction", 0.25),
            cap_pct=data.get("kelly_cap_pct", 5),
        )
        stake = sug["stake"]
        if stake <= 0:
            raise SystemExit(
                f"Kelly stake is 0 (no +EV at odds {args.odds}); pass --stake to override."
            )

    source = args.source or edge.get("best_book") or "unknown"
    bet = {
        "id": next_bet_id(bets),
        "placed_at": datetime.now(timezone.utc).isoformat(),
        "match_id": match_id,
        "market": edge["market"],
        "selection": edge["selection"],
        "odds_decimal": round(args.odds, 3),
        "stake": stake,
        "source": source,
        # schema stores model_edge_pct as a DECIMAL (0.05 = 5%); predict.py's
        # edge_pct is a percentage, so divide by 100.
        "model_edge_pct": round(edge["edge_pct"] / 100.0, 4),
        "model_prob": edge["model_prob"],
        "result": None,
        "pnl": None,
        "settled_at": None,
    }
    if args.rationale:
        bet["rationale"] = args.rationale

    # Never write an invalid bet: validate the candidate before persisting.
    schema = _load(SCHEMA)
    fixture_ids = {m["id"] for m in _load(FIXTURES).get("matches", [])}
    errors = (validate_schema(bet, schema)
              + validate_discipline(bet)
              + validate_match_id(bet, fixture_ids))
    if errors:
        print("Refusing to log - candidate bet is invalid:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(json.dumps(bet, indent=2))
    if args.dry_run:
        print("\n(dry run - nothing written)")
        return 0

    bets.append(bet)
    data["bets"] = bets
    _atomic_write(BETS, json.dumps(data, indent=2) + "\n")
    try:
        where = BETS.relative_to(ROOT)
    except ValueError:
        where = BETS
    print(f"\nLogged {bet['id']} -> {where} "
          f"({bet['selection']} @ {bet['odds_decimal']}, stake {stake}, {source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
