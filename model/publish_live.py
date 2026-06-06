"""Publish a lightweight live-results feed for client-side matchday updates.

The site is static (built once, ahead of the tournament), so to reflect LIVE/FINISHED
scores WITHOUT rebuilding we emit a small `site/public/data/live.json` that the
dashboard polls. Run it alongside `fetch_results.py` on a cadence during matchdays
(see docs/closing-odds-runbook.md). Reads `fixtures.json` — the source of truth
`fetch_results.py` writes scores/status into. No API calls of its own.

Usage:
    python model/publish_live.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures" / "fixtures.json"
OUT = ROOT / "site" / "public" / "data" / "live.json"


def build_live(matches: list[dict]) -> dict[str, dict]:
    """Compact map of match_id -> {status, home, away} for matches that have a LIVE
    or FINISHED score. Scheduled matches are omitted (nothing to show yet)."""
    live: dict[str, dict] = {}
    for m in matches:
        status = m.get("status")
        score = m.get("score") or {}
        h, a = score.get("home"), score.get("away")
        if status in ("LIVE", "FINISHED") and h is not None and a is not None:
            live[m["id"]] = {"status": status, "home": h, "away": a}
    return live


def main() -> None:
    fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
    live = build_live(fx.get("matches", []))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "matches": live,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    n_live = sum(1 for v in live.values() if v["status"] == "LIVE")
    print(f"Wrote live.json: {len(live)} match(es) with scores ({n_live} live) "
          f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
