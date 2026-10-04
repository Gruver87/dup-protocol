"""SQLite transactions/tx_receipts dual-write value/fee/burned satoshi."""

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


def test_tx_and_receipt_write_satoshi():
    db, path = _db()
    try:
        db._persist_block_locked(
            {
                "height": 1,
                "hash": "0xabc",
                "parent_hash": "0",
                "timestamp": 100,
                "miner": "0xm",
                "tx_count": 1,
                "gas_used": 0,
                "total_burned": 0.02,
                "extra_data": "",
            },
            [
                {
                    "hash": "0xtx1",
                    "block_height": 1,
                    "from_addr": "0xa",
                    "to_addr": "0xb",
                    "value": 2.5,
                    "fee": 0.01,
                    "burned": 0.02,
                    "gas_used": 21000,
                    "status": 1,
                    "timestamp": 100,
                }
            ],
        )
        db.conn.commit()
        tx = db.conn.execute(
            "SELECT value_satoshi, fee_satoshi, burned_satoshi "
            "FROM transactions WHERE hash=?",
            ("0xtx1",),
        ).fetchone()
        assert int(tx["value_satoshi"]) == int(to_satoshi(2.5))
        assert int(tx["fee_satoshi"]) == int(to_satoshi(0.01))
        assert int(tx["burned_satoshi"]) == int(to_satoshi(0.02))
        rcpt = db.get_tx_receipt("0xtx1")
        assert rcpt is not None
        assert rcpt["value_satoshi"] == int(to_satoshi(2.5))
        assert rcpt["fee_satoshi"] == int(to_satoshi(0.01))
        assert rcpt["burned_satoshi"] == int(to_satoshi(0.02))
        listed = db.get_transactions_by_address("0xa", direction="sent")
        assert listed[0]["value_satoshi"] == int(to_satoshi(2.5))
    finally:
        db.close()
        os.remove(path)


def test_tx_money_satoshi_backfill():
    db, path = _db()
    try:
        db.conn.execute(
            "INSERT INTO transactions "
            "(hash, block_height, from_addr, to_addr, value, fee, burned, "
            "value_satoshi, fee_satoshi, burned_satoshi, nonce, status, timestamp, gas, gas_used) "
            "VALUES ('0xlegacy', 1, '0xa', '0xb', 3.0, 0.1, 0.05, NULL, NULL, NULL, 0, 1, 1, 21000, 21000)"
        )
        db.conn.execute(
            "INSERT INTO tx_receipts "
            "(tx_hash, block_height, block_hash, from_addr, to_addr, value, fee, burned, "
            "value_satoshi, fee_satoshi, burned_satoshi, gas_used, status, created_at) "
            "VALUES ('0xlegacy', 1, '0xh', '0xa', '0xb', 3.0, 0.1, 0.05, NULL, NULL, NULL, 21000, 1, 1)"
        )
        db.conn.commit()
        db._backfill_tx_money_satoshi()
        tx = db.conn.execute(
            "SELECT value_satoshi, fee_satoshi, burned_satoshi "
            "FROM transactions WHERE hash='0xlegacy'"
        ).fetchone()
        assert int(tx["value_satoshi"]) == int(to_satoshi(3.0))
        assert int(tx["fee_satoshi"]) == int(to_satoshi(0.1))
        assert int(tx["burned_satoshi"]) == int(to_satoshi(0.05))
        rc = db.conn.execute(
            "SELECT value_satoshi FROM tx_receipts WHERE tx_hash='0xlegacy'"
        ).fetchone()
        assert int(rc["value_satoshi"]) == int(to_satoshi(3.0))
    finally:
        db.close()
        os.remove(path)


def test_source_needles_tx_money_satoshi():
    db_py = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    assert "_backfill_tx_money_satoshi" in db_py
    assert '("transactions", "value_satoshi"' in db_py
    assert '("tx_receipts", "fee_satoshi"' in db_py
    rocks = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert "value_satoshi" in rocks
    assert "burned_satoshi" in rocks
