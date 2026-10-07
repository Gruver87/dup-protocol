"""Plasma block persist prefers total_amount_satoshi (ADR 0021)."""

from __future__ import annotations

from features.plasma import PlasmaBlock
from runtime.amount import to_satoshi


def test_plasma_block_to_db_emits_total_amount_satoshi():
    txs = [
        {"from": "0x" + "a" * 40, "to": "0x" + "b" * 40, "amount": 10.0},
        {"from": "0x" + "b" * 40, "to": "0x" + "c" * 40, "amount": 2.5},
    ]
    blk = PlasmaBlock(block_id=1, parent_hash="cd" * 32, transactions=txs, created_at=1)
    row = blk.to_db()
    assert float(row["total_amount"]) == 12.5
    assert int(row["total_amount_satoshi"]) == int(to_satoshi(12.5))
    assert row["tx_root"] == row["merkle_root"]
