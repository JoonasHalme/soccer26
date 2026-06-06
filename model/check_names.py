"""Diagnostic: list teams in fixtures.json that are missing from the trained ratings."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures" / "fixtures.json"
RATINGS = ROOT / "model" / "data" / "ratings.json"


def main() -> None:
    fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
    ratings = json.loads(RATINGS.read_text(encoding="utf-8"))
    rated = set(ratings.keys())

    fixture_teams: set[str] = set()
    for teams in fx["groups"].values():
        fixture_teams.update(teams)

    placeholder_prefixes = ("1", "2", "3", "W", "L")
    missing = sorted(t for t in fixture_teams if t not in rated)
    print(f"{len(fixture_teams)} unique teams in fixtures, {len(missing)} missing from ratings:")
    for t in missing:
        print(f"  - {t!r}")
    print("\nSample of CSV team names (first 30 of 261):")
    for name in sorted(rated)[:30]:
        print(f"  - {name!r}")


if __name__ == "__main__":
    main()
