"""Pull football RSS headlines and match them to World Cup 2026 teams.

FREE v1 news feed: no API key, no quota. Reads three public RSS feeds
(BBC Sport football, The Guardian football, ESPN soccer), tags each headline
with the tournament national teams it mentions (via an alias map built from
fixtures/fixtures.json), dedupes, sorts newest-first and writes
site/public/data/news.json. The static Astro site reads that JSON at build time.

Resilient by design: if a feed times out or fails, it is skipped and the others
still produce output. Parsing uses only the Python standard library
(xml.etree.ElementTree) so there is no new dependency (the repo already ships
`requests`).

Usage:
    python model/fetch_news.py                 # default: keep last 14 days, 80 items
    python model/fetch_news.py --max-age-days 10 --limit 60
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree as ET

import requests


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures" / "fixtures.json"
ENV_FILE = ROOT / ".env"
OUT_FILE = ROOT / "site" / "public" / "data" / "news.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; Soccer26-NewsBot/1.0; "
    "+personal World Cup 2026 dashboard)"
)

FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian", "https://www.theguardian.com/football/rss"),
    ("ESPN", "https://www.espn.com/espn/rss/soccer/news"),
]

# Words that bias a headline toward genuine team news (injuries, lineups,
# suspensions, fitness) rather than transfer gossip. Used only to flag items.
INJURY_KEYWORDS = [
    "injur", "injure", "suspend", "suspension", "ban", "banned", "squad",
    "line-up", "lineup", "line up", "doubt", "ruled out", "rule out",
    "withdraw", "withdrew", "fitness", "fit ", "return", "recover",
    "knock", "strain", "hamstring", "knee", "ankle", "call-up", "call up",
    "named", "miss ", "absence", "out of",
]


def _load_env() -> None:
    """Tiny .env loader so we don't pull in python-dotenv (parity with fetch_odds)."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def tournament_teams() -> list[str]:
    """The ~48 canonical national-team names from fixtures.json's groups."""
    fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
    teams: list[str] = []
    for members in fx.get("groups", {}).values():
        teams.extend(members)
    # de-dup while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in teams:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


# Extra aliases per canonical fixtures.json name. The canonical name itself is
# always added automatically, so only list *variants* here.
TEAM_ALIASES: dict[str, list[str]] = {
    "USA": ["United States", "US men", "USMNT", "US national", "United States of America"],
    "South Korea": ["Korea Republic", "Korea"],
    "South Africa": ["Bafana Bafana"],
    "Czech Republic": ["Czechia"],
    "Bosnia & Herzegovina": ["Bosnia and Herzegovina", "Bosnia"],
    "Ivory Coast": ["Cote d'Ivoire", "Côte d'Ivoire", "Côte d’Ivoire"],
    "Cape Verde": ["Cabo Verde"],
    "DR Congo": ["Congo DR", "DR Congo", "DRC", "Democratic Republic of Congo",
                 "Democratic Republic of the Congo"],
    "Curaçao": ["Curacao"],
    "Netherlands": ["Holland", "Dutch", "the Netherlands"],
    "Turkey": ["Türkiye", "Turkiye"],
    "Iran": ["IR Iran"],
    "Saudi Arabia": ["Saudi"],
    "New Zealand": ["All Whites"],
    "Qatar": [],
    "Uzbekistan": [],
}

# Demonyms/adjective forms that are safe (won't collide across teams) and that
# appear constantly in football copy. Kept conservative to avoid false hits.
TEAM_DEMONYMS: dict[str, list[str]] = {
    "England": ["English"],
    "Scotland": ["Scottish", "Scots"],
    "Spain": ["Spanish", "Spaniard"],
    "France": ["French"],
    "Germany": ["German"],
    "Brazil": ["Brazilian"],
    "Argentina": ["Argentine", "Argentinian"],
    "Portugal": ["Portuguese"],
    "Belgium": ["Belgian"],
    "Croatia": ["Croatian"],
    "Morocco": ["Moroccan"],
    "Senegal": ["Senegalese"],
    "Japan": ["Japanese"],
    "Mexico": ["Mexican"],
    "Uruguay": ["Uruguayan"],
    "Colombia": ["Colombian"],
    "Switzerland": ["Swiss"],
    "Sweden": ["Swedish"],
    "Norway": ["Norwegian"],
    "Egypt": ["Egyptian"],
    "Ghana": ["Ghanaian"],
    "Australia": ["Australian", "Socceroos"],
}


def build_alias_index(teams: list[str]) -> dict[str, list[re.Pattern[str]]]:
    """canonical team -> list of compiled word-boundary regexes for its aliases."""
    index: dict[str, list[re.Pattern[str]]] = {}
    for team in teams:
        names = {team}
        names.update(TEAM_ALIASES.get(team, []))
        names.update(TEAM_DEMONYMS.get(team, []))
        patterns: list[re.Pattern[str]] = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            # Word-boundary match, case-insensitive. \b works around the ASCII
            # letters in every alias here; accented variants are matched too
            # because we escape the literal text.
            patterns.append(re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.IGNORECASE))
        index[team] = patterns
    return index


def match_teams(text: str, index: dict[str, list[re.Pattern[str]]]) -> list[str]:
    matched: list[str] = []
    for team, patterns in index.items():
        if any(p.search(text) for p in patterns):
            matched.append(team)
    return matched


def is_injury_related(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in INJURY_KEYWORDS)


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _norm_url(url: str) -> str:
    """Drop query string / fragment (utm noise) for dedup + cleaner links, and
    REJECT any non-http(s) scheme.

    These URLs come from third-party RSS feeds. A `javascript:`/`data:text/html`
    URL would otherwise flow into an `<a href>` (NewsItem.astro) or the RSS feed and
    become a one-click stored-XSS vector — Astro escapes attribute *values* but does
    not block dangerous URL schemes. Returns '' for an unsafe/unparseable URL so the
    caller drops the item."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return ""
    if parts.scheme.lower() not in ("http", "https"):
        return ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    # Most RSS feeds use RFC-822 (pubDate); some Atom-ish ones use ISO-8601.
    try:
        d = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc).isoformat()


def _findtext(item: ET.Element, *names: str) -> str | None:
    """Find the first matching child text, ignoring XML namespaces on the tag."""
    for child in item:
        tag = child.tag.split("}")[-1]  # strip namespace
        if tag in names and child.text:
            return child.text
    return None


def fetch_feed(source: str, url: str) -> list[dict]:
    """GET + parse one RSS feed into a list of raw item dicts. Never raises."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  ! {source}: fetch failed ({exc}); skipping")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        print(f"  ! {source}: parse failed ({exc}); skipping")
        return []

    items: list[dict] = []
    # RSS 2.0: channel/item ; Atom: feed/entry. Handle both.
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        title = _findtext(el, "title")
        if not title:
            continue
        link = _findtext(el, "link")
        if not link:
            # Atom uses <link href="...">
            for child in el:
                if child.tag.split("}")[-1] == "link" and child.get("href"):
                    link = child.get("href")
                    break
        if not link:
            continue
        url = _norm_url(link)
        if not url:
            continue  # unsafe (non-http) or unparseable URL — drop the item
        summary = _findtext(el, "description", "summary", "content") or ""
        published = _findtext(el, "pubDate", "published", "updated", "date")
        items.append({
            "title": _strip_html(title),
            "url": url,
            "source": source,
            "published_at": _parse_date(published),
            "summary": _strip_html(summary),
        })
    print(f"  + {source}: {len(items)} items")
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-age-days", type=int, default=14,
                        help="Drop items older than this many days (default 14)")
    parser.add_argument("--limit", type=int, default=80,
                        help="Cap on number of kept items (default 80)")
    args = parser.parse_args()

    _load_env()  # not needed for RSS, kept for v2 (API-Football) parity

    teams = tournament_teams()
    index = build_alias_index(teams)
    print(f"Matching against {len(teams)} tournament teams.")

    raw: list[dict] = []
    fetched_sources: list[str] = []
    for source, url in FEEDS:
        items = fetch_feed(source, url)
        if items:
            fetched_sources.append(source)
        raw.extend(items)

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.max_age_days)

    seen_keys: set[str] = set()
    kept: list[dict] = []
    for it in raw:
        text = f"{it['title']} {it['summary']}"
        matched = match_teams(text, index)
        if not matched:
            continue

        # Recency filter (items without a date are kept — better to show than drop).
        if it["published_at"]:
            try:
                when = dt.datetime.fromisoformat(it["published_at"])
                if when < cutoff:
                    continue
            except ValueError:
                pass

        title_key = re.sub(r"\W+", "", it["title"].lower())
        dedup_key = it["url"] or title_key
        if dedup_key in seen_keys or title_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        seen_keys.add(title_key)

        kept.append({
            "id": hashlib.sha1((it["url"] or it["title"]).encode("utf-8")).hexdigest()[:12],
            "title": it["title"],
            "url": it["url"],
            "source": it["source"],
            "published_at": it["published_at"],
            "summary": it["summary"][:280],
            "teams": matched,
            "is_injury_related": is_injury_related(text),
        })

    # Sort newest-first; undated items sink to the bottom.
    kept.sort(key=lambda x: x["published_at"] or "", reverse=True)
    kept = kept[: args.limit]

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sources": fetched_sources,
        "items": kept,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    team_hits = sorted({t for it in kept for t in it["teams"]})
    print(
        f"\nFeeds fetched: {', '.join(fetched_sources) or 'none'}\n"
        f"Items kept (team-matched): {len(kept)}\n"
        f"Teams with news: {len(team_hits)} ({', '.join(team_hits) or '—'})\n"
        f"Wrote {OUT_FILE.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
