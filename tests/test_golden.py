"""Python side of the Python<->TS golden cross-check (TASK-056).

`tests/golden/staking_clv_golden.json` is a shared contract: the SAME cases are
asserted here (against model/staking.py + model/clv.py) and in
`site/src/lib/data.golden.test.ts` (against the TS mirrors in data.ts). If either
implementation drifts from the golden, its suite fails — which is exactly the
"duplicated Kelly / t-table / de-vig" drift the audit flagged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from staking import kelly_stake  # noqa: E402
from clv import mean_ci  # noqa: E402

GOLDEN = json.loads((ROOT / "tests" / "golden" / "staking_clv_golden.json").read_text())


@pytest.mark.parametrize("c", GOLDEN["kelly"])
def test_kelly_matches_golden(c):
    r = kelly_stake(c["p"], c["odds"], c["bankroll"], c["fraction"], c["cap_pct"])
    assert r["stake"] == pytest.approx(c["stake"], abs=1e-9)
    assert r["capped"] == c["capped"]
    assert r["full_kelly"] == pytest.approx(c["full_kelly"], abs=1e-3)


@pytest.mark.parametrize("c", GOLDEN["mean_ci"])
def test_mean_ci_matches_golden(c):
    r = mean_ci(c["values"])
    assert r is not None
    for k in ("mean", "margin", "low", "high"):
        assert r[k] == pytest.approx(c[k], abs=1e-9)
