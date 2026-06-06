"""Fetch the 2026 World Cup squads from Wikipedia into site/public/data/squads.json.

Source: the public "2026 FIFA World Cup squads" article (CC BY-SA — attributed on
/policy). Squads are fixed for the tournament, so this is a one-off / occasional run.
Parses the {{nat fs g player|...}} rows per country heading; maps Wikipedia country
names to our fixtures.json team names; keeps only the 48 WC teams.

Usage:
    python model/fetch_squads.py            # write squads.json
    python model/fetch_squads.py --dry-run  # report counts, write nothing
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFEDS = ROOT / "model" / "data" / "confederations.json"
OUT = ROOT / "site" / "public" / "data" / "squads.json"
WIKI = "https://en.wikipedia.org/w/api.php"
PAGE = "2026 FIFA World Cup squads"
TOURNAMENT_START = date(2026, 6, 11)

# Wikipedia heading -> our fixtures.json team name (only the mismatches).
WP_TO_TEAM = {
    "United States": "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Cabo Verde": "Cape Verde",
    "Côte d'Ivoire": "Ivory Coast",
    "DR Congo": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
}
POS_ORDER = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}


def _wikilink(s: str) -> str:
    """[[Link|Display]] / [[Name]] -> the display text; otherwise the trimmed text."""
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", s)
    return (m.group(2) or m.group(1)).strip() if m else s.strip()


def _param(block: str, key: str) -> str:
    m = re.search(rf"\b{key}=\s*(\[\[[^\]]*\]\]|[^|}}\n]*)", block)
    return m.group(1).strip() if m else ""


def _age(block: str) -> int | None:
    m = re.search(r"birth date and age2\|\d+\|\d+\|\d+\|(\d+)\|(\d+)\|(\d+)", block)
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    try:
        dob = date(y, mo, d)
    except ValueError:
        return None
    a = TOURNAMENT_START.year - dob.year - ((TOURNAMENT_START.month, TOURNAMENT_START.day) < (dob.month, dob.day))
    return a


def _int(s: str) -> int | None:
    m = re.search(r"\d+", s or "")
    return int(m.group()) if m else None


def parse_squads(wikitext: str, teams: set[str]) -> dict:
    """Split the article into per-country blocks and parse each player row."""
    # Indices of the team headings (=== Country ===).
    heads = [(m.group(1).strip(), m.end()) for m in re.finditer(r"^===\s*([^=].*?)\s*===\s*$", wikitext, re.M)]
    squads: dict[str, dict] = {}
    for i, (heading, start) in enumerate(heads):
        end = heads[i + 1][1] if i + 1 < len(heads) else len(wikitext)
        block = wikitext[start:end]
        team = WP_TO_TEAM.get(heading, heading)
        if team not in teams:
            continue
        coach = _wikilink(cm.group(1)) if (cm := re.search(r"Coach:\s*(\[\[[^\]]*\]\][^\n]*)", block)) else None
        # Each player row starts at "{{nat fs g player"; take up to the next row/end.
        rows = re.split(r"\{\{\s*nat fs g (?:player|end)", block)[1:]
        players = []
        for r in rows:
            name = _wikilink(_param(r, "name"))
            if not name:
                continue
            players.append({
                "no": _int(_param(r, "no")),
                "pos": (_param(r, "pos") or "").upper()[:2],
                "name": name,
                "club": _wikilink(_param(r, "club")) or None,
                "caps": _int(_param(r, "caps")),
                "goals": _int(_param(r, "goals")),
                "age": _age(r),
            })
        if players:
            players.sort(key=lambda p: (POS_ORDER.get(p["pos"], 9), p["no"] if p["no"] is not None else 99))
            squads[team] = {"coach": coach, "players": players}
    return squads


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch WC2026 squads from Wikipedia")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    teams = {k for k in json.loads(CONFEDS.read_text(encoding="utf-8")) if not k.startswith("_")}
    resp = requests.get(WIKI, params={"action": "parse", "page": PAGE, "prop": "wikitext",
                                      "format": "json", "formatversion": "2"},
                        timeout=30, headers={"User-Agent": "soccer26/1.0 (squads)"})
    resp.raise_for_status()
    wikitext = resp.json()["parse"]["wikitext"]
    squads = parse_squads(wikitext, teams)

    total = sum(len(s["players"]) for s in squads.values())
    print(f"Parsed {len(squads)}/{len(teams)} teams, {total} players.")
    missing = sorted(teams - set(squads))
    if missing:
        print(f"  No squad parsed for: {', '.join(missing)}")

    if args.dry_run:
        print("  --dry-run: squads.json NOT written.")
        return
    payload = {
        "source": "Wikipedia — 2026 FIFA World Cup squads (CC BY-SA)",
        "updated": date.today().isoformat(),
        "teams": squads,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
