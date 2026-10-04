"""Lab helper create_signed_transaction must not invent gas."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto.keys import KeyGenerator
from crypto.signing import create_signed_transaction


def test_create_signed_transaction_requires_gas():
    kp = KeyGenerator.generate_keypair()
    with pytest.raises(ValueError, match="gas_limit_required"):
        create_signed_transaction(
            "0x" + "a" * 40,
            "0x" + "b" * 40,
            1,
            0,
            kp.private_key,
        )


def test_create_signed_transaction_with_explicit_gas():
    kp = KeyGenerator.generate_keypair()
    tx = create_signed_transaction(
        "0x" + "a" * 40,
        "0x" + "b" * 40,
        1,
        0,
        kp.private_key,
        gas_limit=21000,
        gas_price=1,
    )
    assert tx["gas_limit"] == 21000
    assert tx["gas_price"] == 1
    assert tx.get("signature")
