"""SQLite/Rocks persist must not invent gas=21000."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_database_tx_gas_fields_refuse_invent():
    from storage.database import Database

    with pytest.raises(ValueError, match="gas_required"):
        Database._tx_gas_fields({"hash": "ab" * 32, "from": "0xa", "to": "0xb"})

    gas, used = Database._tx_gas_fields({"gas": 21000})
    assert gas == 21000
    assert used == 0

    gas2, used2 = Database._tx_gas_fields({"gas": 50000, "gas_used": 21000})
    assert gas2 == 50000
    assert used2 == 21000

    gas3, used3 = Database._tx_gas_fields({"gas_used": 21000})
    assert gas3 == 21000
    assert used3 == 21000


def test_database_source_no_insert_invent_21000():
    src = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    assert 'tx.get("gas", 21000)' not in src
    assert 'tx.get("gas_used", tx.get("gas", 21000))' not in src
    assert "_tx_gas_fields" in src


def test_rocks_source_no_insert_invent_21000():
    src = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert 'tx.get("gas", 21000)' not in src
    assert 'tx.get("gas_used", tx.get("gas", 21000))' not in src
    assert "observed_optional_int" in src


def test_hasher_hash_transaction_refuses_missing_gas():
    from crypto.hashing import Hasher

    with pytest.raises(ValueError, match="gas_limit required"):
        Hasher.hash_transaction({"from": "0xa", "to": "0xb", "value": 1, "nonce": 0})
    digest = Hasher.hash_transaction(
        {"from": "0xa", "to": "0xb", "value": 1, "nonce": 0, "gas": 21000}
    )
    assert isinstance(digest, str) and len(digest) == 64
