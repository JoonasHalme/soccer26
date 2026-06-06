"""Validate bets/bets.json against the schema AND the betting discipline.

The README states the discipline plainly: only log a bet when the model shows a
real edge (model_edge_pct > 5%) OR you write down an explicit rationale for
overriding the model. schema.json encodes the shape but nothing enforced the
discipline — this script does, and is meant to run in the documented workflow / CI.

It also reports model-vs-manual head-to-head accuracy and P/L over any SETTLED
bets (those with a non-null `result`), so the "did the model beat my gut?"
question becomes answerable as results come in.

Exit code is non-zero if any bet violates the schema or the discipline, so it can
gate a commit/CI step.

Usage:
    python model/validate_bets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BETS = ROOT / "bets" / "bets.json"
SCHEMA = ROOT / "bets" / "schema.json"
FIXTURES = ROOT / "fixtures" / "fixtures.json"

EDGE_THRESHOLD = 0.05  # README discipline: model_edge_pct expressed as a decimal


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(bet: dict, schema: dict) -> list[str]:
    """Minimal, dependency-free check of the required fields, types and enums in
    bets/schema.json. (We avoid pulling in jsonschema for one small file.)"""
    errors: list[str] = []
    props = schema.get("properties", {})
    for field in schema.get("required", []):
        if field not in bet or bet[field] is None:
            errors.append(f"missing required field '{field}'")

    type_map = {
        "string": str, "number": (int, float), "boolean": bool,
        "object": dict, "array": list,
    }
    for key, value in bet.items():
        spec = props.get(key)
        if not spec:
            continue
        allowed = spec.get("type")
        if allowed is not None:
            allowed_list = allowed if isinstance(allowed, list) else [allowed]
            ok = any(
                (t == "null" and value is None)
                or (t in type_map and isinstance(value, type_map[t]) and not (t == "number" and isinstance(value, bool)))
                for t in allowed_list
            )
            if not ok:
                errors.append(f"field '{key}'={value!r} not one of types {allowed_list}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"field '{key}'={value!r} not in enum {spec['enum']}")
        if "minimum" in spec and isinstance(value, (int, float)) and value < spec["minimum"]:
            errors.append(f"field '{key}'={value} below minimum {spec['minimum']}")
    return errors


def validate_discipline(bet: dict) -> list[str]:
    """Enforce the README rule: edge > 5% OR a non-empty written rationale."""
    errors: list[str] = []
    edge = bet.get("model_edge_pct")
    rationale = (bet.get("rationale") or "").strip()
    has_edge = isinstance(edge, (int, float)) and edge >= EDGE_THRESHOLD
    if not has_edge and not rationale:
        errors.append(
            f"discipline: model_edge_pct ({edge}) < {EDGE_THRESHOLD} and no "
            f"written rationale - bet violates the >=5%-edge-or-rationale rule"
        )
    return errors


def validate_match_id(bet: dict, fixture_ids: set[str]) -> list[str]:
    mid = bet.get("match_id")
    if mid and fixture_ids and mid not in fixture_ids:
        return [f"match_id '{mid}' not found in fixtures.json"]
    return []


def head_to_head(bets: list[dict]) -> dict:
    """Split settled bets into model-driven vs manual and report hit-rate / P/L.

    A bet counts as 'model' if it carried a model edge over threshold; otherwise
    'manual' (a rationale-driven override). Only bets with a non-null result
    (WIN/LOSS) count toward accuracy; PUSH/VOID are excluded from hit-rate."""
    buckets = {"model": [], "manual": []}
    for b in bets:
        edge = b.get("model_edge_pct")
        is_model = isinstance(edge, (int, float)) and edge >= EDGE_THRESHOLD
        buckets["model" if is_model else "manual"].append(b)

    report = {}
    for name, group in buckets.items():
        decided = [b for b in group if b.get("result") in ("WIN", "LOSS")]
        wins = sum(1 for b in decided if b["result"] == "WIN")
        pnl = sum(b["pnl"] for b in group if isinstance(b.get("pnl"), (int, float)))
        staked = sum(b["stake"] for b in group if isinstance(b.get("stake"), (int, float)))
        report[name] = {
            "bets": len(group),
            "decided": len(decided),
            "wins": wins,
            "hit_rate": round(wins / len(decided), 3) if decided else None,
            "pnl": round(pnl, 2),
            "roi": round(pnl / staked, 3) if staked else None,
        }
    return report


def main() -> int:
    data = _load_json(BETS)
    schema = _load_json(SCHEMA)
    fixture_ids = {m["id"] for m in _load_json(FIXTURES).get("matches", [])} if FIXTURES.exists() else set()

    bets = data.get("bets", [])
    total_errors = 0
    for bet in bets:
        bet_id = bet.get("id", "<no-id>")
        errors = (
            validate_schema(bet, schema)
            + validate_discipline(bet)
            + validate_match_id(bet, fixture_ids)
        )
        if errors:
            total_errors += len(errors)
            print(f"[FAIL] bet {bet_id}:")
            for e in errors:
                print(f"         - {e}")

    if not bets:
        print("No bets logged yet - nothing to validate (bets/bets.json is empty).")
    elif total_errors == 0:
        print(f"All {len(bets)} bets pass schema + discipline checks.")

    h2h = head_to_head(bets)
    print("\nModel vs manual (settled bets only):")
    for name, stats in h2h.items():
        print(f"  {name:7s} bets={stats['bets']} decided={stats['decided']} "
              f"hit_rate={stats['hit_rate']} pnl={stats['pnl']} roi={stats['roi']}")

    if total_errors:
        print(f"\n{total_errors} validation error(s).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
