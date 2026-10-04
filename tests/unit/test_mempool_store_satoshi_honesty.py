"""Mempool store dict satoshi roundtrip (Exp→pin Wave R helpers)."""

from __future__ import annotations

from blockchain.mempool import MempoolTransaction, _tx_from_store_dict, _tx_to_store_dict
from runtime.amount import to_satoshi


def test_mempool_store_roundtrip_prefers_satoshi():
    tx = MempoolTransaction(
        tx_hash="0x" + "ab" * 32,
        from_addr="0x" + "11" * 20,
        to_addr="0x" + "22" * 20,
        amount=1.5,
        fee=0.001,
        nonce=7,
        gas=21000,
        amount_satoshi=int(to_satoshi(1.5)),
        fee_satoshi=int(to_satoshi(0.001)),
    )
    raw = _tx_to_store_dict(tx)
    assert raw["amount_satoshi"] == int(to_satoshi(1.5))
    assert raw["fee_satoshi"] == int(to_satoshi(0.001))
    # Corrupt ABS floats — satoshi twin must win on reload.
    raw["amount"] = 99.0
    raw["fee"] = 99.0
    back = _tx_from_store_dict(raw)
    assert back.amount_satoshi == int(to_satoshi(1.5))
    assert back.fee_satoshi == int(to_satoshi(0.001))
    assert back.gas == 21000


def test_mempool_store_missing_gas_is_zero_not_21000():
    back = _tx_from_store_dict(
        {
            "tx_hash": "0xh",
            "from_addr": "0xa",
            "to_addr": "0xb",
            "amount_satoshi": 1,
            "fee_satoshi": 1,
        }
    )
    assert back.gas == 0
