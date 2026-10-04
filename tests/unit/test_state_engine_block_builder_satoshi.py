"""StateEngine / BlockBuilder / TxBuilder carry and refuse satoshi dual-write."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.tx_builder import TransactionBuilder
from execution.block_builder import BlockBuilder
from execution.state_engine import StateEngine
from runtime.amount import to_satoshi


def test_state_engine_prefers_amount_satoshi_and_refuses_mismatch():
    from execution.state_engine import AccountState

    se = StateEngine(db=None)
    accounts = {"0x" + "a" * 40: AccountState(balance=10_000_000, nonce=0)}
    se._apply_transaction(
        accounts,
        {
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "value": 1.0,
            "amount_satoshi": 1_000_000,
            "fee_satoshi": 1000,
            "nonce": 0,
        },
    )
    assert accounts["0x" + "b" * 40].balance == 1_000_000
    with pytest.raises(ValueError, match="value_satoshi_mismatch"):
        se._apply_transaction(
            {"0x" + "a" * 40: AccountState(balance=10_000_000, nonce=0)},
            {
                "from": "0x" + "a" * 40,
                "to": "0x" + "b" * 40,
                "value": 2.0,
                "amount_satoshi": 1_000_000,
                "fee_satoshi": 1000,
                "nonce": 0,
            },
        )


def test_block_builder_tx_to_dict_carries_amount_satoshi():
    class _MP:
        def get_sorted_transactions(self):
            return []

    class _St:
        def get_balance_satoshi(self, _a):
            return 0

        def get_balance(self, _a):
            return 0

    b = BlockBuilder(_MP(), _St())
    out = b._tx_to_dict(
        {
            "hash": "ab" * 32,
            "from": "0xa",
            "to": "0xb",
            "value": 1.5,
            "amount_satoshi": int(to_satoshi(1.5)),
            "fee_satoshi": 1000,
            "gas": 21000,
            "gasPrice": 1,
            "nonce": 0,
        }
    )
    assert out["amount_satoshi"] == int(to_satoshi(1.5))
    assert out["fee_satoshi"] == 1000


def test_block_builder_affordable_uses_satoshi_not_float():
    class _MP:
        def get_sorted_transactions(self):
            return []

    class _St:
        def get_balance_satoshi(self, _a):
            return 1_001_000

        def get_balance(self, _a):
            return 1  # would wrongly fail if float path used with fee

    b = BlockBuilder(_MP(), _St())
    assert b._tx_affordable_sat(
        {
            "from": "0xa",
            "value": 1.0,
            "amount_satoshi": 1_000_000,
            "fee_satoshi": 1000,
        }
    )
    assert not b._tx_affordable_sat(
        {
            "from": "0xa",
            "value": 2.0,
            "amount_satoshi": 1_000_000,
            "fee_satoshi": 1000,
        }
    )


def test_tx_builder_emits_amount_satoshi():
    tx = TransactionBuilder.create_transaction(
        "0xa", "0xb", 1.0, nonce=0, gas_price=1e-7, gas_limit=21000
    )
    assert tx["amount_satoshi"] == 1_000_000
    with pytest.raises(ValueError, match="value_satoshi_mismatch"):
        TransactionBuilder.create_transaction(
            "0xa",
            "0xb",
            1.0,
            nonce=0,
            gas_price=1e-7,
            gas_limit=21000,
            amount_satoshi=500_000,
        )
