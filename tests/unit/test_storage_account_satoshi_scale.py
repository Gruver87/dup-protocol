"""AccountRecord must use protocol 1e6 satoshi — never Bitcoin 1e8."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.amount import SATOSHI_MULTIPLIER, to_satoshi
from storage.types import SATOSHI_PER_COIN, AccountRecord


def test_satoshi_per_coin_matches_protocol_multiplier():
    assert SATOSHI_PER_COIN == SATOSHI_MULTIPLIER == 1_000_000
    assert SATOSHI_PER_COIN != 100_000_000


def test_from_mapping_float_balance_uses_1e6():
    rec = AccountRecord.from_mapping("0xabc", {"balance": 1.5, "nonce": 0})
    assert rec.balance_satoshi == int(to_satoshi(1.5))
    assert rec.balance_satoshi == 1_500_000


def test_from_mapping_prefers_balance_satoshi():
    rec = AccountRecord.from_mapping(
        "0xabc", {"balance": 99.0, "balance_satoshi": 42, "nonce": 1}
    )
    assert rec.balance_satoshi == 42
