#!/usr/bin/env python3
"""Wallet signature digest must not diverge on int vs whole-number float value."""

from __future__ import annotations

from crypto.wallet import Wallet, verify_transaction_signature
from runtime.amount import from_satoshi_float, to_satoshi


def test_canonical_value_int_and_float_match():
    w = Wallet.create_new()
    signed = w.sign_transaction(
        "0x" + "ab" * 20,
        1,
        0,
        chain_id=778888,
        gas_limit=21_000,
    )
    assert signed["value"] == 1
    assert verify_transaction_signature({**signed, "gas": 21_000}) is True

    # Simulate prod HTTP: amount_satoshi → from_satoshi_float before verify.
    resolved = from_satoshi_float(int(to_satoshi(1)))
    assert isinstance(resolved, float)
    body = {**signed, "gas": 21_000, "value": resolved}
    assert verify_transaction_signature(body) is True
    c_int = Wallet._canonical_tx_for_hash(signed)
    c_float = Wallet._canonical_tx_for_hash(body)
    assert c_int["value"] == c_float["value"] == 1


def test_normalize_sign_value_needles():
    assert Wallet._normalize_sign_value(1) == 1
    assert Wallet._normalize_sign_value(1.0) == 1
    assert Wallet._normalize_sign_value(1.5) == 1.5
