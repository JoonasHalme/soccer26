"""Pull the 2026 World Cup schedule and build fixtures/fixtures.json end-to-end.

Source is the openfootball/world-cup repo on GitHub, which publishes plain-text
schedules under a permissive license. We download BOTH source files the parser
needs — `cup.txt` (groups) and `cup_finals.txt` (knockouts) — and then invoke
`parse_fixtures.py` so a single command produces a usable fixtures.json.

Usage:
    python model/fetch_fixtures.py            # download + parse
    python model/fetch_fixtures.py --no-parse # download only
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

import parse_fixtures


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "model" / "data"
BASE_URL = "https://raw.githubusercontent.com/openfootball/world-cup/master/2026--usa"
SOURCES = {
    "cup.txt": f"{BASE_URL}/cup.txt",            # group stage
    "cup_finals.txt": f"{BASE_URL}/cup_finals.txt",  # knockout stage
}


def _download(name: str, url: str) -> None:
    print(f"Fetching {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    out = DATA / name
    out.write_text(resp.text, encoding="utf-8")
    print(f"  Saved {out.relative_to(ROOT)} ({len(resp.text)} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-parse", action="store_true",
                    help="Download the raw schedule files but skip the parse step.")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        _download(name, url)

    if args.no_parse:
        print("Downloaded only (--no-parse). Run `python model/parse_fixtures.py` to build fixtures.json.")
        return

    print("Parsing into fixtures/fixtures.json ...")
    parse_fixtures.main()


if __name__ == "__main__":
    main()
