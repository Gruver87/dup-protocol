"""Sync status + native secp probe honesty (Exp→pin Wave P)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_p2p_fallback_sync_not_enabled():
    from api.http import _build_sync_status

    status = _build_sync_status(None, None, None, None)
    assert status["enabled"] is False
    assert status["sync_engine_missing"] is True
    assert status["source"] == "p2p_fallback"
    assert status["wire_probe_ok"] is False


def test_native_secp_probe_failure_is_none():
    import crypto.native as native

    fake = MagicMock()
    fake.verify_secp256k1_sha256.side_effect = RuntimeError("probe down")
    fake.verify_secp256k1_sha256_batch.side_effect = RuntimeError("batch down")
    with patch.object(native, "_native", fake):
        assert native.verify_secp256k1_sha256(b"m", b"s", b"p") is None
        assert native.verify_secp256k1_sha256_batch([(b"m", b"s", b"p")]) is None


def test_tx_validator_probe_failure_not_invalid_signature():
    from blockchain.tx_validator import TransactionValidator

    with patch.object(
        TransactionValidator,
        "_verify_signature",
        side_effect=RuntimeError("signature verify unavailable: probe"),
    ):
        tx = {
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount": 1,
            "fee": 1,
            "nonce": 0,
            "gas": 21_000,
            "signature": "ab" * 32,
            "public_key": "cd" * 33,
        }

        class _SM:
            def get_account(self, _a):
                return type("A", (), {"nonce": 0})()

            def get_balance_satoshi(self, _a):
                return 10_000_000_000

        ok, reason = TransactionValidator.validate(tx, _SM(), require_signature=True)
        assert ok is False
        assert reason == "signature verify unavailable: probe"
        assert reason != "Invalid signature"
