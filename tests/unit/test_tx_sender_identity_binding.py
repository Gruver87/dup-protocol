#!/usr/bin/env python3
"""P0: transaction signature must bind public_key to tx['from']."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto.wallet import Wallet, verify_transaction_signature, verify_transaction_signatures_batch


def test_own_key_own_from_accepts():
    w = Wallet.create_new()
    tx = w.sign_transaction(to="0x" + "ab" * 20, value=1, nonce=0, chain_id=778888, gas_limit=21000)
    assert verify_transaction_signature(tx) is True


def test_attacker_key_victim_from_refused():
    victim = Wallet.create_new()
    attacker = Wallet.create_new()
    # Attacker signs a payload that claims victim as sender.
    forged = attacker.sign_transaction(
        to=attacker.address, value=1, nonce=0, chain_id=778888, gas_limit=21000
    )
    forged["from"] = victim.address
    assert forged["public_key"] == attacker.public_key
    assert forged["from"].lower() != attacker.address.lower()
    assert verify_transaction_signature(forged) is False


def test_batch_forged_sender_element_fails():
    honest = Wallet.create_new()
    victim = Wallet.create_new()
    attacker = Wallet.create_new()
    good = honest.sign_transaction(to="0x" + "cd" * 20, value=1, nonce=0, chain_id=778888, gas_limit=21000)
    forged = attacker.sign_transaction(
        to=attacker.address, value=2, nonce=0, chain_id=778888, gas_limit=21000
    )
    forged["from"] = victim.address
    results = verify_transaction_signatures_batch([good, forged])
    assert results == [True, False]


def test_missing_from_refused():
    w = Wallet.create_new()
    tx = w.sign_transaction(to="0x" + "ef" * 20, value=1, nonce=0, chain_id=778888, gas_limit=21000)
    bad = dict(tx)
    bad.pop("from", None)
    assert verify_transaction_signature(bad) is False


def test_malformed_public_key_refused():
    w = Wallet.create_new()
    tx = w.sign_transaction(to="0x" + "11" * 20, value=1, nonce=0, chain_id=778888, gas_limit=21000)
    bad = dict(tx)
    bad["public_key"] = "not-hex"
    assert verify_transaction_signature(bad) is False


def test_tamper_to_after_sign_refused():
    w = Wallet.create_new()
    tx = w.sign_transaction(to="0x" + "22" * 20, value=1, nonce=0, chain_id=778888, gas_limit=21000)
    bad = dict(tx)
    bad["to"] = "0x" + "33" * 20
    assert verify_transaction_signature(bad) is False


def test_tamper_value_after_sign_refused():
    w = Wallet.create_new()
    tx = w.sign_transaction(to="0x" + "22" * 20, value=1, nonce=0, chain_id=778888, gas_limit=21000)
    bad = dict(tx)
    bad["value"] = 999
    assert verify_transaction_signature(bad) is False


def test_tamper_data_after_sign_refused():
    w = Wallet.create_new()
    tx = w.sign_transaction(
        to="0x" + "22" * 20, value=0, nonce=0, chain_id=778888, data="0xdead", gas_limit=21000
    )
    bad = dict(tx)
    bad["data"] = "0xbeef"
    assert verify_transaction_signature(bad) is False


def test_wrong_chain_id_refused():
    w = Wallet.create_new()
    tx = w.sign_transaction(to="0x" + "22" * 20, value=1, nonce=0, chain_id=778888, gas_limit=21000)
    bad = dict(tx)
    bad["chain_id"] = 1
    assert verify_transaction_signature(bad) is False
