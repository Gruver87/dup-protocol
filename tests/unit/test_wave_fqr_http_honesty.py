"""Wave F/Q/R: input validators fail-closed; /tx/sign fee; tx_signer verify."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_http_source_refuses_identity_sanitize_stub():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "def sanitize_input(x): return x" not in src
    assert "require_input_validators" in src
    assert "input validators not available" in src


def test_require_input_validators_prod_raises_when_missing(monkeypatch):
    from api import http as http_mod

    monkeypatch.setattr(http_mod, "_INPUT_VALIDATORS_AVAILABLE", False)
    monkeypatch.setattr(http_mod, "sanitize_input", None)
    with pytest.raises(RuntimeError, match="input validators required"):
        http_mod.require_input_validators(SimpleNamespace(deployment_mode="prod"))


def test_tx_sign_requires_fee_no_invent():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/tx/sign"')[1].split("elif path")[0]
    assert "fee or fee_satoshi required" in chunk
    assert 'fee", 0.001)' not in chunk


def test_tx_signer_hash_refuses_invented_fee():
    from crypto.tx_signer import TransactionSigner

    with pytest.raises(ValueError, match="fee"):
        TransactionSigner.hash_transaction(
            {"from": "a", "to": "b", "amount": 1, "nonce": 0}
        )


def test_tx_signer_verify_ecdsa_missing_raises():
    from crypto import tx_signer

    with patch.object(tx_signer, "CRYPTO_AVAILABLE", False):
        with pytest.raises(RuntimeError, match="unavailable"):
            tx_signer.TransactionSigner.verify_signature(
                {"from": "a", "to": "b", "amount": 1, "nonce": 0, "fee": 0.001},
                "ab",
                "0x1",
            )


def test_tx_verify_path_null_on_unavailable():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/tx/verify"')[1].split("elif path")[0]
    assert '"valid": None' in chunk or '"valid":None' in chunk
    assert "unavailable" in chunk
