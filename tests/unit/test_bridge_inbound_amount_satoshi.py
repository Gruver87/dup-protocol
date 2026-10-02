"""Bridge inbound HTTP prefers amount_satoshi; prod refuses float-only."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.amount import from_satoshi_float, to_satoshi


def test_inbound_envelope_prefers_amount_satoshi():
    from api.http import _inbound_envelope_from_body

    env = _inbound_envelope_from_body(
        {
            "tx_hash": "0xabc",
            "recipient": "0x" + "11" * 20,
            "amount": 99.0,
            "amount_satoshi": 1_000_000,
            "from_chain": "ethereum",
        },
        cfg=SimpleNamespace(deployment_mode="dev"),
    )
    assert env.amount_satoshi == 1_000_000
    assert env.amount == pytest.approx(1.0)


def test_inbound_envelope_prod_refuses_float_only(monkeypatch):
    from api.http import _inbound_envelope_from_body

    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    with pytest.raises(ValueError, match="amount_satoshi required"):
        _inbound_envelope_from_body(
            {
                "tx_hash": "0xabc",
                "recipient": "0x" + "11" * 20,
                "amount": 1.0,
                "from_chain": "ethereum",
            },
            cfg=SimpleNamespace(deployment_mode="prod"),
        )


def test_inbound_envelope_dev_float_derives_satoshi():
    from api.http import _inbound_envelope_from_body

    env = _inbound_envelope_from_body(
        {
            "tx_hash": "0xabc",
            "recipient": "0x" + "11" * 20,
            "amount": 2.5,
            "from_chain": "ethereum",
        },
        cfg=SimpleNamespace(deployment_mode="dev"),
    )
    assert env.amount_satoshi == int(to_satoshi(2.5))
    assert env.amount == pytest.approx(2.5)


def test_canonical_serializer_float_uses_to_satoshi():
    from blockchain.canonical_serializer import CanonicalSerializer
    from runtime.amount import to_satoshi

    out = CanonicalSerializer._canonicalize(0.1)
    assert out == int(to_satoshi(0.1))
