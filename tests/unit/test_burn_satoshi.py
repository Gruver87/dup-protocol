"""Burn ledger dual-write burned_amount_satoshi / total_burned_satoshi."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.amount import to_satoshi
from storage.database import Database


def _db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    db.initialize()
    return db, path


def test_record_burn_writes_satoshi():
    db, path = _db()
    try:
        db.record_burn(1, 1.5)
        db.record_burn(2, 0.5)
        assert db.get_total_burned() == 2.0
        stats = db.get_burn_stats()
        assert stats["total_burned_satoshi"] == int(to_satoshi(2.0))
        assert stats["blocks_with_burn"] == 2
        row = db.conn.execute(
            "SELECT burned_amount_satoshi, total_burned_satoshi "
            "FROM burn_stats WHERE block_height=2"
        ).fetchone()
        assert int(row["burned_amount_satoshi"]) == int(to_satoshi(0.5))
        assert int(row["total_burned_satoshi"]) == int(to_satoshi(2.0))
    finally:
        db.close()
        os.remove(path)


def test_block_and_proposer_audit_total_burned_satoshi():
    db, path = _db()
    try:
        db.save_block(
            {
                "height": 1,
                "hash": "h1",
                "parent_hash": "0" * 64,
                "timestamp": 100,
                "miner": "0xminer",
                "tx_count": 0,
                "gas_used": 0,
                "total_burned": 1.25,
                "extra_data": "",
                "transactions": [],
            }
        )
        row = db.conn.execute(
            "SELECT total_burned, total_burned_satoshi FROM blocks WHERE height=1"
        ).fetchone()
        assert int(row["total_burned_satoshi"]) == int(to_satoshi(1.25))
        block = db.get_block(1)
        assert block is not None
        assert int(block["total_burned_satoshi"]) == int(to_satoshi(1.25))
        audit = db.get_proposer_audit_log(limit=1)[0]
        assert audit["total_burned_satoshi"] == int(to_satoshi(1.25))
        metrics = db.get_chain_metrics(window=8)
        assert metrics["burn_last_window_satoshi"] == int(to_satoshi(1.25))
        stats = db.get_proposer_stats(limit=5)
        assert stats[0]["total_burned_satoshi"] == int(to_satoshi(1.25))
        detail = db.get_proposer_detail("0xminer")
        assert detail["total_burned_satoshi"] == int(to_satoshi(1.25))
    finally:
        db.close()
        os.remove(path)


def test_burn_satoshi_backfill_from_legacy_float():
    db, path = _db()
    try:
        db.conn.execute(
            "INSERT INTO burn_stats (block_height, burned_amount, burned_amount_satoshi, "
            "total_burned, total_burned_satoshi) VALUES (10, 3.25, NULL, 3.25, NULL)"
        )
        db.conn.commit()
        db._backfill_burn_satoshi()
        row = db.conn.execute(
            "SELECT burned_amount_satoshi, total_burned_satoshi "
            "FROM burn_stats WHERE block_height=10"
        ).fetchone()
        assert int(row["burned_amount_satoshi"]) == int(to_satoshi(3.25))
        assert int(row["total_burned_satoshi"]) == int(to_satoshi(3.25))
    finally:
        db.close()
        os.remove(path)


def test_source_needles_burn_satoshi():
    db_py = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    assert "_backfill_burn_satoshi" in db_py
    assert '("burn_stats", "burned_amount_satoshi"' in db_py
    assert '("blocks", "total_burned_satoshi"' in db_py
    assert '("block_proposer_audit", "total_burned_satoshi"' in db_py
    assert "burn_last_window_satoshi" in db_py
    assert "SUM(total_burned_satoshi)" in db_py
    rocks = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert "burned_amount_satoshi" in rocks
    assert "total_burned_satoshi" in rocks
    assert "burn_last_window_satoshi" in rocks
    assert "def get_proposer_stats" in rocks
    hybrid = (ROOT / "storage" / "hybrid_database.py").read_text(encoding="utf-8")
    assert "def get_proposer_stats" in hybrid
