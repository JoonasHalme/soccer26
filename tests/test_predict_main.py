"""End-to-end test of predict.main()'s tamper-evidence + idempotency (TASK-056).

Runs the real pipeline against a tiny temp fixture/ratings set (paths monkeypatched)
and asserts the load-bearing invariants of the audit trail:
  - the live file's bytes hash == the sidecar == the latest ledger entry,
  - the ledger is a valid prev-hash chain,
  - the written bytes contain NO CRLF (the Windows newline fix), and
  - a no-op re-run rewrites nothing and does not grow the ledger.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

import predict  # noqa: E402


def _setup(tmp_path, monkeypatch):
    out = tmp_path / "data" / "predictions.json"
    out.parent.mkdir(parents=True)
    fixtures = tmp_path / "fixtures.json"
    ratings = tmp_path / "ratings.json"
    ratings.write_text(json.dumps({"Spain": 2000.0, "Malta": 1500.0}))
    fixtures.write_text(json.dumps({"matches": [{
        "id": "m-001", "status": "SCHEDULED", "home": "Spain", "away": "Malta",
        "kickoff": "2026-06-11T19:00:00Z", "venue": "Neutral",
    }]}))
    monkeypatch.setattr(predict, "ROOT", tmp_path)   # for OUT.relative_to(ROOT) prints
    monkeypatch.setattr(predict, "OUT", out)
    monkeypatch.setattr(predict, "FIXTURES", fixtures)
    monkeypatch.setattr(predict, "RATINGS", ratings)
    return out


def _ledger(out):
    return json.loads((out.parent / "predictions_ledger.json").read_text())


def test_main_hash_sidecar_ledger_consistent(tmp_path, monkeypatch):
    out = _setup(tmp_path, monkeypatch)
    predict.main()

    raw = out.read_bytes()
    assert b"\r\n" not in raw                       # Windows CRLF would break the hash
    digest = hashlib.sha256(raw).hexdigest()
    sidecar = json.loads(out.with_suffix(".hash.json").read_text())
    ledger = _ledger(out)
    assert digest == sidecar["sha256"] == ledger[-1]["sha256"]


def test_main_ledger_is_a_valid_prev_hash_chain(tmp_path, monkeypatch):
    out = _setup(tmp_path, monkeypatch)
    predict.main()
    prev = predict.GENESIS_HASH
    for e in _ledger(out):
        assert e["prev"] == prev
        prev = predict.ledger_entry_hash(e)


def test_main_is_idempotent(tmp_path, monkeypatch):
    out = _setup(tmp_path, monkeypatch)
    predict.main()
    raw, n = out.read_bytes(), len(_ledger(out))
    predict.main()                                  # unchanged picks -> no rewrite
    assert out.read_bytes() == raw
    assert len(_ledger(out)) == n


def test_main_archive_holds_blended_forecast(tmp_path, monkeypatch):
    out = _setup(tmp_path, monkeypatch)
    predict.main()
    archive = json.loads((out.parent / "predictions_archive.json").read_text())
    assert "m-001" in archive
    e = archive["m-001"]
    assert abs(e["home"] + e["draw"] + e["away"] - 1.0) < 1e-3
