"""Exp mid-soak: P2P/tx_builder/SQLite no invent gas=21000 defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_p2p_source_no_invent_gas_21000_assign():
    src = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    chunk = src.split("raw_gas = data.get", 1)[1].split("signature = data.get", 1)[0]
    assert "gas = 21_000" not in chunk
    assert "gas = 21000" not in chunk
    assert "never invent gas=21000" in src


def test_tx_builder_requires_gas_fields():
    from core.tx_builder import TransactionBuilder

    with pytest.raises(ValueError, match="gas_price_required"):
        TransactionBuilder.create_transaction("a", "b", 1, nonce=0)
    with pytest.raises(ValueError, match="gas_limit_required"):
        TransactionBuilder.create_transaction("a", "b", 1, nonce=0, gas_price=1.0)
    tx = TransactionBuilder.create_transaction(
        "a", "b", 1, nonce=0, gas_price=1.0, gas_limit=65000
    )
    assert tx["gas"] == 65000
    assert tx["gasPrice"] == 1.0


def test_create_transaction_requires_gas_price():
    from execution.mempool import create_transaction

    with pytest.raises(ValueError, match="gas_price_required"):
        create_transaction("alice", "bob", 1)
    t = create_transaction("alice", "bob", 1, gas_price=0.001)
    assert t.gas_price == 0.001


def test_sqlite_schema_source_no_default_21000():
    src = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    assert "gas          INTEGER NOT NULL DEFAULT 21000" not in src
    assert "gas_used     INTEGER NOT NULL DEFAULT 21000" not in src
    assert 'DEFAULT 21000"),' not in src.split("gas_used")[1][:80]
