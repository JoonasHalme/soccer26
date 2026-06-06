"""Train the Elo table on historical international results.

Expects a CSV at model/data/internationals.csv with columns:
    date,home_team,away_team,home_score,away_score,neutral

A good free source is the Mart/Jurgen `international football results` dataset on
Kaggle (`results.csv`). Drop it in as `model/data/internationals.csv`.

Usage:
    python model/train_ratings.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from elo import EloTable, match_importance


ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "model" / "data" / "internationals.csv"
OUT = ROOT / "model" / "data" / "ratings.json"


def main() -> None:
    if not CSV.exists():
        raise SystemExit(
            f"Missing {CSV}. See module docstring for the dataset to download."
        )
    df = pd.read_csv(CSV, parse_dates=["date"]).sort_values("date")
    df = df[df["date"] >= "2020-01-01"]
    df = df.dropna(subset=["home_score", "away_score"])

    def _is_neutral(val) -> bool:
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in {"true", "1", "yes", "t"}

    elo = EloTable()
    for row in df.itertuples(index=False):
        elo.update(
            home=row.home_team,
            away=row.away_team,
            gh=int(row.home_score),
            ga=int(row.away_score),
            neutral=_is_neutral(row.neutral),
            importance=match_importance(getattr(row, "tournament", "")),
        )
    elo.save(OUT)
    print(f"Trained on {len(df)} matches; wrote {len(elo.ratings)} team ratings to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
