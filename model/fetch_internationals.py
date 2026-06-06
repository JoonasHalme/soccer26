"""Refresh model/data/internationals.csv from the public martj42 dataset.

The results CSV is the source the ratings train on and the form / Road-to-the-WC
predictions are built from. It's a community dataset (martj42/international_results)
updated within a day or two of matches finishing — so re-running this in the
pre-tournament window pulls in the latest warm-up friendlies (and later, WC group
results) for free, no API key. The FROZEN ratings.json is NOT retrained here; this
only refreshes the results feed that build_form.py reads.

Run: python model/fetch_internationals.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "model" / "data" / "internationals.csv"
SRC = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
EXPECTED_HEADER = "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral"


def _max_date(text: str) -> str:
    rows = [ln for ln in text.splitlines()[1:] if ln]
    return max((ln.split(",", 1)[0] for ln in rows), default="?")


def main() -> None:
    prev = CSV.read_text(encoding="utf-8") if CSV.exists() else ""
    prev_n = max(0, len(prev.splitlines()) - 1)
    prev_max = _max_date(prev) if prev else "?"

    req = urllib.request.Request(SRC, headers={"User-Agent": "soccer26/1.0 (+results refresh)"})
    text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")

    # Sanity-check before overwriting: right shape, plausible size.
    head = text.splitlines()[0].strip()
    if head != EXPECTED_HEADER:
        sys.exit(f"Unexpected header, refusing to overwrite:\n  got: {head}")
    n = len(text.splitlines()) - 1
    if n < 40000:
        sys.exit(f"Only {n} rows downloaded (<40000) — looks truncated; not writing.")

    CSV.write_text(text, encoding="utf-8")
    new_max = _max_date(text)
    print(f"Wrote {CSV.relative_to(ROOT)} — {n} rows (was {prev_n}, +{n - prev_n}).")
    print(f"  latest match date: {prev_max} -> {new_max}")


if __name__ == "__main__":
    main()
