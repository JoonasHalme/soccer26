"""Parse openfootball's cup.txt and cup_finals.txt into fixtures/fixtures.json.

Run AFTER fetch_fixtures.py. Idempotent: regenerates the file from scratch.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CUP = ROOT / "model" / "data" / "cup.txt"
FINALS = ROOT / "model" / "data" / "cup_finals.txt"
OUT = ROOT / "fixtures" / "fixtures.json"

YEAR = 2026
MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "June": 6,
    "Jul": 7, "July": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _strip_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_kickoff(date_str: str, time_str: str, tz_str: str) -> str:
    """Combine date 'Thu Jun 11', time '13:00', offset 'UTC-6' → ISO UTC."""
    parts = date_str.replace(",", "").split()
    month_name, day = None, None
    for token in parts:
        if token in MONTHS:
            month_name = token
        elif token.isdigit():
            day = int(token)
    if month_name is None or day is None:
        raise ValueError(f"Cannot parse date: {date_str!r}")
    hour, minute = (int(x) for x in time_str.split(":"))
    offset_match = re.match(r"UTC([+-]\d+)", tz_str)
    if not offset_match:
        raise ValueError(f"Cannot parse tz: {tz_str!r}")
    offset_hours = int(offset_match.group(1))
    tz = timezone(timedelta(hours=offset_hours))
    local = datetime(YEAR, MONTHS[month_name], day, hour, minute, tzinfo=tz)
    return local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


GROUP_ROSTER_RE = re.compile(r"^Group ([A-L])\s*\|\s*(.+)$")
GROUP_HEADER_RE = re.compile(r"^▪\s*Group\s+([A-L])\s*$")
DATE_LINE_RE = re.compile(r"^([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,3}\s+\d{1,2})\s*$")
MATCH_LINE_RE = re.compile(
    r"^\s*(?:\((\d+)\)\s+)?(\d{1,2}:\d{2})\s+(UTC[+-]\d+)\s+(.+?)\s+v\s+(.+?)\s+@\s+(.+?)\s*$"
)
KO_HEADER_RE = re.compile(r"^▪\s*(Round of 32|Round of 16|Quarter-final|Semi-final|Match for third place|Final)\s*$")

KO_STAGE_MAP = {
    "Round of 32": "R32",
    "Round of 16": "R16",
    "Quarter-final": "QF",
    "Semi-final": "SF",
    "Match for third place": "3RD",
    "Final": "FINAL",
}


def _split_group_teams(rest: str) -> list[str]:
    """The roster line uses whitespace runs as separators. Multi-word names like
    'Bosnia & Herzegovina', 'Cape Verde', 'DR Congo', 'Ivory Coast', 'New Zealand',
    'Czech Republic', 'Saudi Arabia', 'South Africa', 'South Korea' all need to
    stay intact, so we split on 2+ spaces."""
    return [_strip_ws(p) for p in re.split(r"\s{2,}", rest.strip()) if p.strip()]


def parse_groups(text: str) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for line in text.splitlines():
        m = GROUP_ROSTER_RE.match(line.strip())
        if m:
            letter = m.group(1)
            teams = _split_group_teams(m.group(2))
            groups[letter] = teams
    return groups


def parse_group_matches(text: str) -> list[dict]:
    matches: list[dict] = []
    current_group: str | None = None
    current_date: str | None = None
    seq = 1
    for line in text.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        hdr = GROUP_HEADER_RE.match(s.strip())
        if hdr:
            current_group = hdr.group(1)
            current_date = None
            continue
        if current_group is None:
            continue
        date_m = DATE_LINE_RE.match(s.strip())
        if date_m:
            current_date = date_m.group(1)
            continue
        match_m = MATCH_LINE_RE.match(s)
        if match_m and current_date:
            _, t, tz, home, away, venue = match_m.groups()
            matches.append({
                "id": f"m-{seq:03d}",
                "stage": "GROUP",
                "group": current_group,
                "kickoff": _parse_kickoff(current_date, t, tz),
                "venue": _strip_ws(venue),
                "home": _strip_ws(home),
                "away": _strip_ws(away),
                "score": {"home": None, "away": None},
                "status": "SCHEDULED",
            })
            seq += 1
    return matches


def parse_knockouts(text: str, start_seq: int) -> list[dict]:
    matches: list[dict] = []
    current_stage: str | None = None
    current_date: str | None = None
    seq = start_seq
    for line in text.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        ko = KO_HEADER_RE.match(s.strip())
        if ko:
            current_stage = KO_STAGE_MAP[ko.group(1)]
            current_date = None
            continue
        date_m = DATE_LINE_RE.match(s.strip())
        if date_m:
            current_date = date_m.group(1)
            continue
        match_m = MATCH_LINE_RE.match(s)
        if match_m and current_stage and current_date:
            game_no, t, tz, home, away, venue = match_m.groups()
            matches.append({
                "id": f"m-{seq:03d}",
                "game_no": int(game_no) if game_no else None,
                "stage": current_stage,
                "kickoff": _parse_kickoff(current_date, t, tz),
                "venue": _strip_ws(venue),
                "home": _strip_ws(home),
                "away": _strip_ws(away),
                "score": {"home": None, "away": None},
                "status": "SCHEDULED",
            })
            seq += 1
    return matches


def _load_existing_odds() -> dict[tuple[str, str, str], dict]:
    """Map (date, home, away) -> odds dict from the current fixtures.json, so a
    re-parse doesn't silently discard odds already fetched via fetch_odds.py.
    Keyed on kickoff-day + teams because match ids may renumber between parses."""
    if not OUT.exists():
        return {}
    try:
        existing = json.loads(OUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[tuple[str, str, str], dict] = {}
    for m in existing.get("matches", []):
        if m.get("odds"):
            out[(m.get("kickoff", "")[:10], m.get("home"), m.get("away"))] = m["odds"]
    return out


def main() -> None:
    cup_text = CUP.read_text(encoding="utf-8")
    finals_text = FINALS.read_text(encoding="utf-8")

    groups = parse_groups(cup_text)
    group_matches = parse_group_matches(cup_text)
    knockouts = parse_knockouts(finals_text, start_seq=len(group_matches) + 1)
    matches = group_matches + knockouts

    # Preserve any previously-merged odds so re-parsing is non-destructive.
    prior_odds = _load_existing_odds()
    if prior_odds:
        carried = 0
        for m in matches:
            key = (m.get("kickoff", "")[:10], m.get("home"), m.get("away"))
            if key in prior_odds:
                m["odds"] = prior_odds[key]
                carried += 1
        if carried:
            print(f"Carried forward odds for {carried} fixtures from existing fixtures.json")

    fixtures = {
        "tournament": "FIFA World Cup 2026",
        "hosts": ["USA", "Canada", "Mexico"],
        "format": {
            "teams": 48,
            "groups": 12,
            "group_size": 4,
            "knockout_rounds": ["R32", "R16", "QF", "SF", "3RD", "FINAL"],
            "total_matches": 104,
        },
        "groups": {letter: groups.get(letter, []) for letter in "ABCDEFGHIJKL"},
        "matches": matches,
    }

    OUT.write_text(json.dumps(fixtures, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = {"GROUP": 0, "R32": 0, "R16": 0, "QF": 0, "SF": 0, "3RD": 0, "FINAL": 0}
    for m in matches:
        counts[m["stage"]] = counts.get(m["stage"], 0) + 1
    print(f"Wrote {len(matches)} matches to {OUT.relative_to(ROOT)}")
    for stage, n in counts.items():
        print(f"  {stage}: {n}")
    print(f"Groups: {sum(len(v) for v in groups.values())} teams across {len(groups)} groups")


if __name__ == "__main__":
    main()
