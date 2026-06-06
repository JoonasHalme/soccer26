"""Bridge recent FINISHED friendlies from ESPN into internationals.csv.

The martj42 results dataset (fetch_internationals.py) ingests games ~a day late,
so the model-graded "Road to the World Cup" feed would otherwise lag a day behind.
This pulls finished friendlies from ESPN's free, no-key scoreboard for the last few
days and appends any that are NEWER than the dataset's latest played match — so a
result (and the model's pre-match call on it) shows within minutes instead of
tomorrow.

Self-healing: only games after the CSV's max *played* date are added, so once
martj42 catches up these stop being appended (no duplication). A ±1-day name-pair
dedup guards the midnight-UTC case where ESPN and martj42 disagree on the date.

Run AFTER fetch_internationals.py, BEFORE build_form.py.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "model" / "data" / "internationals.csv"
SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.friendly/scoreboard?dates={}"
DAYS_BACK = 3

# ESPN displayName -> the spelling used in martj42/internationals.csv, so ratings
# and the WC-team feed match. Anything not listed passes through unchanged
# (Germany, Belgium, Portugal, Chile, United States, … already agree).
ESPN_TO_CSV = {
    "Türkiye": "Turkey", "Turkiye": "Turkey",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Korea DPR": "North Korea",
    "Côte d'Ivoire": "Ivory Coast", "Cote d'Ivoire": "Ivory Coast",
    "Cabo Verde": "Cape Verde",
    "Czechia": "Czech Republic",
    "China PR": "China",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Congo DR": "DR Congo",
}


def _fetch(yyyymmdd: str) -> dict:
    req = urllib.request.Request(SCOREBOARD.format(yyyymmdd), headers={"User-Agent": "soccer26/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


def _name(espn: str) -> str:
    return ESPN_TO_CSV.get(espn, espn)


def main() -> None:
    rows = list(csv.reader(CSV.open(encoding="utf-8")))
    body = rows[1:]

    def _scored(v: str) -> bool:                        # a real score, not ""/NA (future fixtures)
        return v.strip().lstrip("-").isdigit()

    played = [r for r in body if len(r) >= 5 and _scored(r[3]) and _scored(r[4])]
    max_played = max((r[0] for r in played), default="0000-00-00")

    # (home, away) -> set of dates already in the CSV, for the ±1-day dedup.
    existing: dict[tuple, set] = {}
    for r in body:
        if len(r) >= 3:
            existing.setdefault((r[1], r[2]), set()).add(r[0])

    today = dt.datetime.now(dt.timezone.utc).date()
    new_rows, seen = [], set()
    for i in range(DAYS_BACK + 1):
        d = today - dt.timedelta(days=i)
        try:
            data = _fetch(d.strftime("%Y%m%d"))
        except Exception:
            continue
        for e in data.get("events", []):
            st = (e.get("status") or {}).get("type") or {}
            if not st.get("completed"):
                continue
            desc = ((st.get("description") or "") + (st.get("shortDetail") or "")).lower()
            if any(w in desc for w in ("cancel", "postpon", "abandon", "await")):
                continue
            comp = (e.get("competitions") or [{}])[0]
            cs = comp.get("competitors") or []
            home = next((c for c in cs if c.get("homeAway") == "home"), None)
            away = next((c for c in cs if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            hs, as_ = home.get("score"), away.get("score")
            if hs in (None, "") or as_ in (None, ""):
                continue
            date = e["date"][:10]                       # UTC date of kickoff
            if date <= max_played:                      # martj42 already covers this
                continue
            h, a = _name(home["team"]["displayName"]), _name(away["team"]["displayName"])
            if (date, h, a) in seen:
                continue
            seen.add((date, h, a))
            prior = existing.get((h, a), set())
            if any(abs((dt.date.fromisoformat(date) - dt.date.fromisoformat(p)).days) <= 1 for p in prior):
                continue                                # same pairing within a day already present
            try:
                hg, ag = str(int(hs)), str(int(as_))
            except (TypeError, ValueError):
                continue
            neutral = "TRUE" if comp.get("neutralSite") else "FALSE"
            new_rows.append([date, h, a, hg, ag, "Friendly", "", "", neutral])

    if not new_rows:
        print(f"No new finished friendlies after {max_played} — nothing to bridge.")
        return
    new_rows.sort(key=lambda r: r[0])
    with CSV.open("a", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(new_rows)
    print(f"Appended {len(new_rows)} finished friendlies (> {max_played}) from ESPN:")
    for r in new_rows:
        print(f"  {r[0]}  {r[1]} {r[3]}-{r[4]} {r[2]}")


if __name__ == "__main__":
    main()
