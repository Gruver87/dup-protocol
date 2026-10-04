"""Exp mid-soak: SQLite no invent gas=21000; AI/slashing stake no invent defaults."""

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
    assert used == 0  # unobserved, not invented 21000

    gas2, used2 = Database._tx_gas_fields({"gas": 50000, "gas_used": 21000})
    assert gas2 == 50000
    assert used2 == 21000

    # gas_used-only rows (legacy tests) bind without inventing a separate limit.
    gas3, used3 = Database._tx_gas_fields({"gas_used": 21000})
    assert gas3 == 21000
    assert used3 == 21000


def test_database_source_no_insert_invent_21000():
    src = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    assert 'tx.get("gas", 21000)' not in src
    assert 'tx.get("gas_used", tx.get("gas", 21000))' not in src
    assert "_tx_gas_fields" in src


def test_ai_slashing_stake_no_default_invent():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    ai = src.split('path == "/ai/register-validator"')[1].split("elif path")[0]
    assert "_http_stake_abs" in ai
    assert 'stake", 100)' not in ai
    slash = src.split('path == "/slashing/add-validator"')[1].split("elif path")[0]
    assert "_http_stake_abs" in slash
    assert 'stake", 32.0)' not in slash


def test_slashing_register_refuses_zero_stake():
    from consensus.slashing import SlashingEngine

    se = SlashingEngine()
    with pytest.raises(ValueError, match="stake_required"):
        se.register_validator("0xval", 0)
    se.register_validator("0xval", 1_000_000)
    assert se._stakes["0xval"] == 1_000_000
