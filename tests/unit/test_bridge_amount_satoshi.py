"""Bridge lock/credit dual-write amount_satoshi."""

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


def test_save_bridge_lock_writes_amount_satoshi():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db.initialize()
        db.save_bridge_lock("0xfrom", "ethereum", "0xto", 5.0, "0xlock1")
        locks = db.get_bridge_locks()
        assert len(locks) == 1
        assert locks[0]["amount"] == 5.0
        assert locks[0]["amount_satoshi"] == int(to_satoshi(5.0))
    finally:
        try:
            db.close()
        except Exception:
            pass
        os.remove(path)


def test_bridge_credit_and_claim_use_amount_satoshi():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db.initialize()
        recipient = "0x" + "11" * 20
        db.set_balance(recipient, 0)
        key = db.save_bridge_credit("0xevt", recipient, 2.5, "ethereum", log_index=1)
        assert key
        # claim another event
        out = db.claim_and_credit_bridge_event(
            "ethereum", "0xevt2", recipient, 1.0, log_index=0
        )
        assert out["credited"] is True
        assert db.get_balance_satoshi(recipient) == int(to_satoshi(1.0))
        cols = {
            r[1]
            for r in db.conn.execute("PRAGMA table_info(bridge_credits)").fetchall()
        }
        assert "amount_satoshi" in cols
        row = db.conn.execute(
            "SELECT amount_satoshi FROM bridge_credits WHERE credit_key=?",
            (out["credit_key"],),
        ).fetchone()
        assert int(row["amount_satoshi"]) == int(to_satoshi(1.0))
    finally:
        try:
            db.close()
        except Exception:
            pass
        os.remove(path)


def test_refund_pending_bridge_lock_credits_satoshi():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db.initialize()
        sender = "0x" + "22" * 20
        db.set_balance(sender, 10.0)
        db.debit_and_create_bridge_lock(
            from_addr=sender,
            amount=3.0,
            burn_address="0xburn",
            burn_amount=0.1,
            to_chain="ethereum",
            to_addr="0xto",
            net_amount=2.9,
            tx_hash="0xpendinglock",
        )
        before = db.get_balance_satoshi(sender)
        out = db.refund_pending_bridge_lock("0xpendinglock")
        assert out["refunded"] is True
        assert out["amount_satoshi"] == int(to_satoshi(2.9))
        assert db.get_balance_satoshi(sender) == before + int(to_satoshi(2.9))
    finally:
        try:
            db.close()
        except Exception:
            pass
        os.remove(path)


def test_source_needles_bridge_amount_satoshi():
    db_py = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    rocks_py = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert "_backfill_bridge_amount_satoshi" in db_py
    assert '("bridge_locks", "amount_satoshi"' in db_py
    assert "amount_satoshi" in rocks_py
    assert "balance_delta_satoshi(recipient" in db_py
