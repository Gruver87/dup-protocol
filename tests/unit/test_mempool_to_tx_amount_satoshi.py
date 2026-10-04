"""Mempool→Transaction conversion must carry amount_satoshi (mining/validate)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blockchain.mempool import Mempool, MempoolTransaction
from blockchain.mempool_wire import mempool_tx_to_wire
from core.blockchain import Transaction
from runtime.amount import to_satoshi


def test_mining_style_conversion_binds_amount_satoshi():
    """Mirror main.py forge conversion path."""
    mp_tx = MempoolTransaction(
        tx_hash="ab" * 32,
        from_addr="0x" + "11" * 20,
        to_addr="0x" + "22" * 20,
        amount=1.5,
        fee=0.001,
        nonce=0,
        gas=21000,
        amount_satoshi=int(to_satoshi(1.5)),
        fee_satoshi=int(to_satoshi(0.001)),
    )
    amt_sat = int(getattr(mp_tx, "amount_satoshi", -1))
    tx = Transaction(
        from_addr=mp_tx.from_addr,
        to_addr=mp_tx.to_addr,
        value=mp_tx.amount,
        nonce=mp_tx.nonce,
        gas=int(mp_tx.gas),
        data=mp_tx.data or "",
        timestamp=int(mp_tx.timestamp or 0),
        tx_hash=mp_tx.tx_hash,
        signature=mp_tx.signature or "",
        public_key=mp_tx.public_key or "",
        amount_satoshi=amt_sat if amt_sat >= 0 else None,
    )
    assert tx.amount_satoshi == int(to_satoshi(1.5))


def test_get_sorted_transactions_includes_amount_satoshi():
    mp = Mempool(min_fee=0.0)
    ok = mp.add_raw(
        MempoolTransaction(
            tx_hash="cd" * 32,
            from_addr="0x" + "33" * 20,
            to_addr="0x" + "44" * 20,
            amount=2.0,
            fee=0.01,
            nonce=0,
            gas=21000,
            amount_satoshi=int(to_satoshi(2.0)),
            fee_satoshi=int(to_satoshi(0.01)),
            signature="aa",
            public_key="bb" * 32,
        )
    )
    if not ok:
        mp.transactions["cd" * 32] = MempoolTransaction(
            tx_hash="cd" * 32,
            from_addr="0x" + "33" * 20,
            to_addr="0x" + "44" * 20,
            amount=2.0,
            fee=0.01,
            nonce=0,
            gas=21000,
            amount_satoshi=int(to_satoshi(2.0)),
            fee_satoshi=int(to_satoshi(0.01)),
        )
    rows = mp.get_sorted_transactions()
    assert rows
    assert "amount_satoshi" in rows[0]
    assert int(rows[0]["amount_satoshi"]) == int(to_satoshi(2.0))
    assert "fee_satoshi" in rows[0]


def test_mempool_orders_by_fee_satoshi_not_float():
    mp = Mempool(min_fee=0.0)
    low = MempoolTransaction(
        tx_hash="11" * 32,
        from_addr="0x" + "11" * 20,
        to_addr="0x" + "22" * 20,
        amount=1.0,
        fee=0.001,
        nonce=0,
        gas=21000,
        fee_satoshi=1000,
    )
    high = MempoolTransaction(
        tx_hash="22" * 32,
        from_addr="0x" + "33" * 20,
        to_addr="0x" + "44" * 20,
        amount=1.0,
        fee=0.002,
        nonce=0,
        gas=21000,
        fee_satoshi=2000,
    )
    assert mp.add_raw(low)
    assert mp.add_raw(high)
    ordered = mp.get(limit=10)
    assert [t.tx_hash for t in ordered] == ["22" * 32, "11" * 32]


def test_wire_dict_keeps_amount_satoshi():
    tx = MempoolTransaction(
        tx_hash="ef" * 32,
        from_addr="0x" + "55" * 20,
        to_addr="0x" + "66" * 20,
        amount=3.0,
        fee=0.0,
        nonce=1,
        gas=21000,
        amount_satoshi=int(to_satoshi(3.0)),
        fee_satoshi=0,
    )
    wire = mempool_tx_to_wire(tx)
    assert int(wire["amount_satoshi"]) == int(to_satoshi(3.0))


def test_source_needles_mempool_fee_satoshi():
    src = (ROOT / "blockchain" / "mempool.py").read_text(encoding="utf-8")
    assert "min_fee_satoshi" in src
    assert "fee_too_low (min_satoshi=" in src
    assert '"amount_satoshi"' in src
    assert "key=lambda x: int(getattr(x, \"fee_satoshi\"" in src or (
        "getattr(x, \"fee_satoshi\"" in src
    )
