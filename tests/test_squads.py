"""Tests for the Wikipedia squad parser (model/fetch_squads.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from fetch_squads import parse_squads  # noqa: E402

WIKITEXT = """
==Group A==
===Germany===
Coach: [[Julian Nagelsmann]]

{{nat fs g start}}
{{nat fs g player|no=1|pos=GK|name=[[Manuel Neuer]]|age={{birth date and age2|2026|6|11|1986|3|27}}|caps=124|goals=0|club=[[FC Bayern Munich|Bayern Munich]]|clubnat=GER}}
{{nat fs g player|no=7|pos=FW|name=[[Kai Havertz]]|age={{birth date and age2|2026|6|11|1999|6|11}}|caps=57|goals=20|club=[[Arsenal F.C.|Arsenal]]|clubnat=ENG}}
{{nat fs g player|no=6|pos=DF|name=[[Joshua Kimmich]]|caps=109|goals=8|club=[[FC Bayern Munich|Bayern Munich]]|clubnat=GER}}
{{nat fs g end}}

===Atlantis===
Coach: [[Nobody]]
{{nat fs g start}}
{{nat fs g player|no=9|pos=FW|name=[[Aquaman]]|caps=1|club=[[Sea FC]]}}
{{nat fs g end}}
"""


def test_parses_only_known_teams_and_fields():
    squads = parse_squads(WIKITEXT, {"Germany"})          # Atlantis not in our team set
    assert set(squads) == {"Germany"}
    g = squads["Germany"]
    assert g["coach"] == "Julian Nagelsmann"
    assert len(g["players"]) == 3
    neuer = next(p for p in g["players"] if p["name"] == "Manuel Neuer")
    assert neuer["no"] == 1 and neuer["pos"] == "GK" and neuer["caps"] == 124
    assert neuer["club"] == "Bayern Munich"               # uses the [[link|display]] text
    assert neuer["age"] == 40                             # age at 2026-06-11


def test_sorted_by_position_then_number():
    g = parse_squads(WIKITEXT, {"Germany"})["Germany"]
    # GK first, then DF, then FW (Kimmich DF before Havertz FW despite higher number)
    assert [p["pos"] for p in g["players"]] == ["GK", "DF", "FW"]


def test_name_mapping_for_aliased_country():
    wt = "===United States===\n{{nat fs g player|no=1|pos=GK|name=[[Matt Turner]]|caps=50|club=[[Crystal Palace]]}}\n"
    squads = parse_squads(wt, {"USA"})                    # WP 'United States' -> our 'USA'
    assert "USA" in squads and squads["USA"]["players"][0]["name"] == "Matt Turner"
