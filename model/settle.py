"""Settle bets in bets/bets.json against final scores in fixtures/fixtures.json.

Single source of truth for scores is `match.score = {home, away}` (the same
field the group-standings feature reads). A match is considered SETTLED when its
status is FINISHED or both score legs are non-null.

For each bet whose match has a final score, this grades the bet:
  - sets `result`  -> WIN | LOSS | PUSH | VOID
  - sets `pnl`     -> profit/loss in the accounting currency
  - sets `settled_at`

P/L convention (matches schema.json):
  WIN  -> (odds_decimal - 1) * stake
  LOSS -> -stake
  PUSH -> 0      (stake returned)
  VOID -> 0      (match abandoned / not gradable)

Asian-handicap supports half-lines so a bet can half-win or half-lose: those
return a fractional pnl ( +(odds-1)*stake/2 / -stake/2 ) and a result of WIN/LOSS
(the half is reflected in the pnl, not a separate enum value).

IDEMPOTENT: re-running does not double-count. An already-settled bet is left
untouched UNLESS the underlying score changed (e.g. a correction), in which case
it is re-graded. Bets on matches with no final score are left OPEN (result null).

Usage:
    python model/settle.py            # settle and write bets.json back
    python model/settle.py --dry-run  # print what would change, write nothing
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BETS = ROOT / "bets" / "bets.json"
FIXTURES = ROOT / "fixtures" / "fixtures.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, text: str) -> None:
    """Write atomically via a temp file + os.replace so a crash can't truncate
    the source-of-truth bet log."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def match_is_final(match: dict) -> bool:
    """Whether a match can be graded for settlement.

    Requires a complete score AND a non-in-progress status. fetch_results.py writes
    a {home, away} score with status='LIVE' for matches still being played (e.g.
    1-0 at half-time); grading those would settle bets — and feed CLV — off a
    half-played score, corrupting the source-of-truth bet log until full-time. So a
    score alone is NOT enough: we explicitly refuse LIVE/SCHEDULED and accept
    FINISHED (or a manually-entered final that carries no live status)."""
    score = match.get("score") or {}
    has_score = score.get("home") is not None and score.get("away") is not None
    return has_score and match.get("status") not in ("LIVE", "SCHEDULED")


def _ah_line(selection: str) -> tuple[str, float] | None:
    """Parse an Asian-handicap selection like 'AHC_-1.5_HOME' or 'AHC_+0.25_AWAY'.

    Returns (side, line) where side is 'HOME'/'AWAY' and line is the handicap
    applied to that side (negative = giving goals). Returns None if unparseable.
    """
    parts = selection.upper().replace("AHC_", "").split("_")
    if len(parts) != 2:
        return None
    raw_line, side = parts
    if side not in ("HOME", "AWAY"):
        # also accept 'AHC_HOME_-1.5'
        raw_line, side = parts[1], parts[0]
        if side not in ("HOME", "AWAY"):
            return None
    try:
        line = float(raw_line.replace("+", ""))
    except ValueError:
        return None
    return side, line


def _grade_outcome(market: str, selection: str, hs: int, as_: int) -> str | None:
    """Return 'WIN' | 'LOSS' | 'PUSH' | 'HALF_WIN' | 'HALF_LOSS' for a settled
    score, or None if the market/selection is not gradable here (-> VOID upstream).

    HALF_WIN / HALF_LOSS only arise for quarter-line Asian handicaps; everything
    else collapses to WIN/LOSS/PUSH.
    """
    sel = selection.upper()
    total = hs + as_

    if market == "1X2":
        winner = "HOME" if hs > as_ else "AWAY" if as_ > hs else "DRAW"
        # accept MONEYLINE synonyms too
        sel_norm = {"1": "HOME", "X": "DRAW", "2": "AWAY"}.get(sel, sel)
        return "WIN" if sel_norm == winner else "LOSS"

    if market == "OVER_UNDER":
        # selection like OVER_2_5 / UNDER_2_5 ; parse the line.
        line = _ou_line(sel)
        if line is None:
            return None
        if "OVER" in sel:
            return "WIN" if total > line else ("PUSH" if total == line else "LOSS")
        if "UNDER" in sel:
            return "WIN" if total < line else ("PUSH" if total == line else "LOSS")
        return None

    if market == "BTTS":
        both = hs > 0 and as_ > 0
        if sel in ("YES", "BTTS_YES"):
            return "WIN" if both else "LOSS"
        if sel in ("NO", "BTTS_NO"):
            return "WIN" if not both else "LOSS"
        return None

    if market == "ASIAN_HANDICAP":
        parsed = _ah_line(sel)
        if parsed is None:
            return None
        side, line = parsed
        # Margin from the perspective of the BET side, plus the handicap.
        margin = (hs - as_) if side == "HOME" else (as_ - hs)
        adj = margin + line
        # Quarter lines (x.25 / x.75) split the stake across two neighbouring
        # half-lines; adj will be a multiple of 0.25 and never exactly 0 for a
        # quarter line, so a |adj| == 0.25 is the canonical half outcome.
        if abs(adj % 0.5) > 1e-9:  # quarter line -> possible half result
            if adj > 0:
                return "WIN" if adj >= 0.5 else "HALF_WIN"
            else:
                return "LOSS" if adj <= -0.5 else "HALF_LOSS"
        if adj > 0:
            return "WIN"
        if adj < 0:
            return "LOSS"
        return "PUSH"

    # CORRECT_SCORE / OUTRIGHT / OTHER are not auto-gradable from a single score.
    return None


def _ou_line(selection: str) -> float | None:
    """OVER_2_5 -> 2.5 ; UNDER_3 -> 3.0 ; OVER_2_25 -> 2.25."""
    digits = selection.upper().replace("OVER", "").replace("UNDER", "").strip("_")
    if not digits:
        return None
    # '2_5' -> '2.5', '2_25' -> '2.25'
    parts = digits.split("_")
    try:
        if len(parts) == 1:
            return float(parts[0])
        return float(f"{parts[0]}.{parts[1]}")
    except ValueError:
        return None


def grade_bet(bet: dict, match: dict) -> dict:
    """Compute {result, pnl} for a bet against a FINAL match. Pure function."""
    score = match.get("score") or {}
    hs, as_ = score.get("home"), score.get("away")
    stake = bet.get("stake", 0) or 0
    odds = bet.get("odds_decimal", 0) or 0
    win_profit = (odds - 1) * stake

    outcome = _grade_outcome(bet.get("market", ""), bet.get("selection", ""), hs, as_)

    if outcome is None:
        # Not auto-gradable (e.g. CORRECT_SCORE/OUTRIGHT) -> leave for manual grading.
        return {"result": "VOID", "pnl": 0.0}
    if outcome == "WIN":
        return {"result": "WIN", "pnl": round(win_profit, 4)}
    if outcome == "LOSS":
        return {"result": "LOSS", "pnl": round(-stake, 4)}
    if outcome == "PUSH":
        return {"result": "PUSH", "pnl": 0.0}
    if outcome == "HALF_WIN":
        # Half stake wins at full odds, half stake is returned.
        return {"result": "WIN", "pnl": round(win_profit / 2.0, 4)}
    if outcome == "HALF_LOSS":
        # Half stake lost, half returned.
        return {"result": "LOSS", "pnl": round(-stake / 2.0, 4)}
    return {"result": "VOID", "pnl": 0.0}


def settle_all(data: dict, fixtures: dict) -> tuple[dict, list[dict]]:
    """Grade every gradable bet in-place. Returns (data, list-of-changes).

    Idempotent: a bet already settled is re-graded only if its computed
    (result, pnl) differs from what's stored (i.e. the score changed). Bets on
    matches without a final score are left as-is.
    """
    by_id = {m["id"]: m for m in fixtures.get("matches", [])}
    changes: list[dict] = []

    for bet in data.get("bets", []):
        match = by_id.get(bet.get("match_id"))
        if not match or not match_is_final(match):
            continue  # no result yet -> leave OPEN (or its prior manual state)

        graded = grade_bet(bet, match)
        already = bet.get("result")
        same = (already == graded["result"]
                and _close(bet.get("pnl"), graded["pnl"]))
        if same:
            continue  # idempotent no-op

        before = {"result": already, "pnl": bet.get("pnl")}
        bet["result"] = graded["result"]
        bet["pnl"] = graded["pnl"]
        bet["settled_at"] = _now_iso()
        changes.append({"id": bet.get("id"), "before": before, "after": graded})

    return data, changes


def _close(a, b, tol: float = 1e-6) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) <= tol


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print changes without writing bets.json")
    args = parser.parse_args()

    data = json.loads(BETS.read_text(encoding="utf-8"))
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))

    bets = data.get("bets", [])
    if not bets:
        print("No bets logged yet - nothing to settle (bets/bets.json is empty).")
        return 0

    data, changes = settle_all(data, fixtures)

    finished = sum(1 for m in fixtures.get("matches", []) if match_is_final(m))
    print(f"{finished} match(es) have final scores; {len(bets)} bet(s) in the log.")

    if not changes:
        print("No bets to (re)settle - all settled bets are already up to date.")
        return 0

    for c in changes:
        b, a = c["before"], c["after"]
        print(f"  {c['id']}: {b['result']}/{b['pnl']} -> {a['result']}/{a['pnl']}")

    if args.dry_run:
        print(f"[dry-run] would settle {len(changes)} bet(s); no file written.")
        return 0

    _atomic_write(BETS, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Settled {len(changes)} bet(s); wrote {BETS.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
