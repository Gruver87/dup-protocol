"""Refuse invent gas=21000 on mempool/validator/identity/apply/PBS."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_mempool_source_no_invent_21000():
    src = (ROOT / "blockchain" / "mempool.py").read_text(encoding="utf-8")
    assert "or 21_000" not in src
    assert "or 21000" not in src
    assert "gas_required" in src


def test_tx_validator_no_invent_21000():
    src = (ROOT / "blockchain" / "tx_validator.py").read_text(encoding="utf-8")
    assert 'gas", 21000)' not in src
    assert "gas_required" in src


def test_tx_identity_no_or_21000():
    src = (ROOT / "core" / "tx_identity.py").read_text(encoding="utf-8")
    assert "gas or 21_000" not in src
    assert "_require_positive_gas" in src


def test_state_service_no_invent_gas_used():
    src = (ROOT / "core" / "components" / "state_service.py").read_text(encoding="utf-8")
    assert "tx.gas or 21000" not in src
    assert "gas_required" in src


def test_evm_deploy_call_require_gas_needles():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert 'body.get("gas", getattr(cfg, "evm_gas_limit"' not in src


def test_send_tx_does_not_soft_skip_validator():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "from blockchain.tx_validator import TransactionValidator" in src
    # send_tx must not wrap validator in ImportError-pass.
    chunk = src.split("Extra validation via TransactionValidator")[1].split("mp_tx = MempoolTransaction")[0]
    assert "except ImportError" not in chunk


def test_mempool_add_refuses_zero_gas():
    from blockchain.mempool import Mempool, MempoolTransaction

    mp = Mempool()
    tx = MempoolTransaction(
        tx_hash="ab" * 32,
        from_addr="0x" + "a" * 40,
        to_addr="0x" + "b" * 40,
        amount=1.0,
        fee=0.001,
        nonce=0,
        gas=0,
    )
    assert mp.add(tx) is False


def test_tx_validator_gas_required():
    from blockchain.tx_validator import TransactionValidator

    ok, reason = TransactionValidator.validate(
        {
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount": 1,
            "fee": 0.001,
            "nonce": 0,
        },
        state_manager=MagicMock(),
        require_signature=False,
    )
    assert ok is False
    assert reason == "gas_required"


def test_pbs_and_builder_no_invent():
    main_src = (ROOT / "main.py").read_text(encoding="utf-8")
    bb_src = (ROOT / "execution" / "block_builder.py").read_text(encoding="utf-8")
    chunk = main_src.split("PBS fee-bid simulation")[1].split("run_pbs_auction")[0]
    assert "or 21000" not in chunk
    assert 'gas", 21000)' not in bb_src
    assert (
        'int(tx.get("gas") or tx.get("gas_limit") or 0)' in bb_src
        or 'int(tx.get("gas") or 0)' in bb_src
    )
