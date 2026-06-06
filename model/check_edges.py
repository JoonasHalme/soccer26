"""Edge-change / price-cross alerting.

Diffs the CURRENT value edges (site/public/data/predictions.json) against the last
saved snapshot and reports which edges APPEARED, DISAPPEARED, or MOVED materially —
so after a fresh `fetch_odds.py` + `predict.py` you can see exactly what the market
move changed, without eyeballing the whole edges page. No API calls; pure local diff.

Usage:
    python model/check_edges.py             # report changes, then update the snapshot
    python model/check_edges.py --dry-run   # report only; don't update the snapshot
    python model/check_edges.py --move 3    # flag edge moves >= 3 percentage points
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRED = ROOT / "site" / "public" / "data" / "predictions.json"
SNAP = ROOT / "model" / "data" / "edges_snapshot.json"


def current_edges(predictions: list[dict]) -> dict[str, dict]:
    """Flatten every surfaced edge to a stable identity → entry map.

    Identity is (match_id, market, selection) — one bet. The entry keeps the edge %
    and best price so we can report moves and re-priced lines."""
    out: dict[str, dict] = {}
    for p in predictions:
        for e in p.get("edges", []):
            key = f"{p['match_id']}|{e['market']}|{e['selection']}"
            out[key] = {
                "match": f"{p['home']} vs {p['away']}",
                "market": e["market"],
                "selection": e["selection"],
                "edge_pct": e.get("edge_pct"),
                "best_odds": e.get("best_odds"),
            }
    return out


def diff_edges(prev: dict[str, dict], curr: dict[str, dict], move: float) -> dict:
    """Pure diff. Returns appeared / disappeared / moved lists (no side effects)."""
    appeared = [curr[k] for k in curr if k not in prev]
    disappeared = [prev[k] for k in prev if k not in curr]
    moved = []
    for k in curr:
        if k not in prev:
            continue
        old, new = prev[k].get("edge_pct"), curr[k].get("edge_pct")
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) and abs(new - old) >= move:
            moved.append({**curr[k], "from_pct": old, "to_pct": new, "delta": round(new - old, 2)})
    appeared.sort(key=lambda e: e.get("edge_pct") or 0, reverse=True)
    disappeared.sort(key=lambda e: e.get("edge_pct") or 0, reverse=True)
    moved.sort(key=lambda e: abs(e["delta"]), reverse=True)
    return {"appeared": appeared, "disappeared": disappeared, "moved": moved}


def _fmt(e: dict) -> str:
    price = f" @ {e['best_odds']:.2f}" if e.get("best_odds") else ""
    return f"{e['match']} — {e['selection']} ({e['market']}) +{e.get('edge_pct')}%{price}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Edge-change / price-cross alerting")
    ap.add_argument("--move", type=float, default=2.0,
                    help="flag edges whose % moved at least this many points")
    ap.add_argument("--dry-run", action="store_true", help="report only; don't update the snapshot")
    args = ap.parse_args()

    if not PRED.exists():
        raise SystemExit(f"Missing {PRED.relative_to(ROOT)} — run python model/predict.py first.")
    predictions = json.loads(PRED.read_text()).get("predictions", [])
    curr = current_edges(predictions)

    try:
        prev = json.loads(SNAP.read_text()) if SNAP.exists() else {}
        if not isinstance(prev, dict):
            prev = {}
    except (json.JSONDecodeError, OSError):
        prev = {}

    if not prev:
        print(f"No previous snapshot — recording {len(curr)} edges as the baseline.")
    else:
        d = diff_edges(prev, curr, args.move)
        if not (d["appeared"] or d["disappeared"] or d["moved"]):
            print(f"No edge changes since the last snapshot ({len(curr)} edges).")
        else:
            if d["appeared"]:
                print(f"\n▲ {len(d['appeared'])} NEW edge(s):")
                for e in d["appeared"]:
                    print("    " + _fmt(e))
            if d["disappeared"]:
                print(f"\n▼ {len(d['disappeared'])} GONE (no longer over threshold):")
                for e in d["disappeared"]:
                    print("    " + _fmt(e))
            if d["moved"]:
                print(f"\n± {len(d['moved'])} MOVED (>= {args.move:g}pp):")
                for e in d["moved"]:
                    print(f"    {e['match']} — {e['selection']} ({e['market']}): "
                          f"{e['from_pct']}% → {e['to_pct']}% ({e['delta']:+}pp)")

    if args.dry_run:
        print("\n--dry-run: snapshot NOT updated.")
        return
    SNAP.write_text(json.dumps(curr, indent=2, sort_keys=True))
    print(f"\nSnapshot updated ({len(curr)} edges) -> {SNAP.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
