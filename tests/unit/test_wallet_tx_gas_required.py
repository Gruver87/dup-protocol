"""Exp mid-soak: wallet / Transaction / tx_identity require explicit gas."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_wallet_sign_requires_gas_limit():
    from crypto.wallet import Wallet

    w = Wallet.create_new()
    with pytest.raises(ValueError, match="gas_limit_required"):
        w.sign_transaction(to="0x" + "ab" * 20, value=1, nonce=0, chain_id=1)
    signed = w.sign_transaction(
        to="0x" + "ab" * 20, value=1, nonce=0, chain_id=1, gas_limit=21000
    )
    assert signed["gas_limit"] == 21000


def test_transaction_init_requires_gas():
    from core.blockchain import Transaction

    with pytest.raises(ValueError, match="gas_required"):
        Transaction("0xa", "0xb", 1.0, nonce=0)
    tx = Transaction("0xa", "0xb", 1.0, nonce=0, gas=65000)
    assert tx.gas == 65000


def test_tx_identity_requires_gas():
    from core.tx_identity import bind_identity_from_fields, compute_tx_identity_hash

    with pytest.raises(ValueError, match="gas_required"):
        compute_tx_identity_hash(
            from_addr="0x" + "a" * 40,
            to_addr="0x" + "b" * 40,
            value=1,
            nonce=0,
            timestamp=1,
        )
    with pytest.raises(ValueError, match="gas_required"):
        bind_identity_from_fields(
            None,
            from_addr="0x" + "a" * 40,
            to_addr="0x" + "b" * 40,
            value=1,
            nonce=0,
            timestamp=1,
        )


def test_main_mining_source_no_invent_gas_from_base_price():
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    chunk = src.split("MempoolTransaction → Transaction")[1].split(
        "Обновляем miner_address"
    )[0]
    assert "self.config.base_gas_price" not in chunk
    assert "self.config.evm_gas_limit" not in chunk
    assert "gas_required" in chunk


def test_mempool_chain_validate_no_invent_base_gas_price():
    src = (ROOT / "blockchain" / "mempool.py").read_text(encoding="utf-8")
    assert "or self.blockchain.config.base_gas_price" not in src


def test_native_wire_always_binds_gas_limit_21000():
    src = (ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs").read_text(
        encoding="utf-8"
    )
    chunk = src.split("verify_wire_tx_signature_inner")[1].split(
        "validate_mempool_batch_inner"
    )[0]
    assert "if g != 21000" not in chunk
    assert "always bind gas when present" in chunk
