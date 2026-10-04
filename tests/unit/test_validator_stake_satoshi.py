"""Validator stake dual-write: stake_satoshi integer column/field."""

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


def test_save_validator_writes_stake_satoshi():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db.initialize()
        addr = "0x" + "ab" * 20
        db.save_validator(addr, 1000.0)
        rows = db.get_validators()
        assert len(rows) == 1
        assert rows[0]["stake"] == 1000.0
        assert rows[0]["stake_satoshi"] == int(to_satoshi(1000.0))
        cols = {
            r[1] for r in db.conn.execute("PRAGMA table_info(validators)").fetchall()
        }
        assert "stake_satoshi" in cols
    finally:
        try:
            db.close()
        except Exception:
            pass
        os.remove(path)


def test_validator_stake_satoshi_backfill_from_legacy_float():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db.initialize()
        addr = "0x" + "cd" * 20
        # Simulate legacy row without stake_satoshi populated.
        db.conn.execute(
            "INSERT INTO validators (address, stake, stake_satoshi, joined_at) "
            "VALUES (?,?,NULL,?)",
            (addr, 2500.0, 1),
        )
        db.conn.commit()
        db._backfill_validator_stake_satoshi()
        row = db.conn.execute(
            "SELECT stake, stake_satoshi FROM validators WHERE address=?", (addr,)
        ).fetchone()
        assert int(row["stake_satoshi"]) == int(to_satoshi(2500.0))
    finally:
        try:
            db.close()
        except Exception:
            pass
        os.remove(path)


def test_source_needles_stake_satoshi():
    db_py = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    rocks_py = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert "stake_satoshi" in db_py
    assert "_backfill_validator_stake_satoshi" in db_py
    assert "stake_satoshi" in rocks_py
