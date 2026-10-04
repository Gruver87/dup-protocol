"""SQLite tx/burn satoshi dual-write (Exp→pin)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sqlite_insert_tx_dual_writes_satoshi():
    from storage.database import Database
    from runtime.amount import to_satoshi

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db._insert_transaction(
            {
                "hash": "0x" + "ab" * 32,
                "from": "0x" + "11" * 20,
                "to": "0x" + "22" * 20,
                "value": 2.5,
                "fee": 0.001,
                "burned": 0.1,
                "gas": 21000,
                "nonce": 1,
                "status": 1,
                "timestamp": 10,
                "block_height": 3,
            }
        )
        db.conn.commit()
        row = dict(
            db.conn.execute(
                "SELECT * FROM transactions WHERE hash=?",
                ("0x" + "ab" * 32,),
            ).fetchone()
        )
        assert int(row["value_satoshi"]) == int(to_satoshi(2.5))
        assert int(row["fee_satoshi"]) == int(to_satoshi(0.001))
        assert int(row["burned_satoshi"]) == int(to_satoshi(0.1))
        ser = db._serialize_tx_row(row)
        assert ser["value_satoshi"] == int(row["value_satoshi"])
    finally:
        try:
            db.conn.close()
        except Exception:
            pass
        os.unlink(path)


def test_sqlite_burn_and_block_satoshi():
    from storage.database import Database
    from runtime.amount import to_satoshi

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db._insert_block(
            {
                "height": 1,
                "hash": "0x" + "cd" * 32,
                "parent_hash": "0x" + "00" * 32,
                "timestamp": 1,
                "miner": "0x" + "11" * 20,
                "transactions": [],
                "total_burned": 0.5,
            }
        )
        db._insert_burn_record(1, 0.25)
        db.conn.commit()
        blk = dict(db.conn.execute("SELECT * FROM blocks WHERE height=1").fetchone())
        assert int(blk["total_burned_satoshi"]) == int(to_satoshi(0.5))
        burn = dict(
            db.conn.execute(
                "SELECT * FROM burn_stats WHERE block_height=1"
            ).fetchone()
        )
        assert int(burn["burned_amount_satoshi"]) == int(to_satoshi(0.25))
        stats = db.get_burn_stats()
        assert int(stats["total_burned_satoshi"]) > 0
    finally:
        try:
            db.conn.close()
        except Exception:
            pass
        os.unlink(path)


def test_sqlite_source_no_invent_tx_value_default():
    src = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    chunk = src.split("def _insert_transaction")[1].split("def _insert_tx_receipt")[0]
    assert "tx_money_satoshi" in chunk
    assert 'tx.get("value", tx.get("amount", 0.0))' not in chunk
    assert "def _backfill_tx_money_satoshi" in src
    assert "def _backfill_burn_satoshi" in src
