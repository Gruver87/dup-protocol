"""Wave Q/I: sharding balance satoshi, MEV money, PQ status fail-closed."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_pq_status_exception_not_enabled():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/pq/status"')[1].split("elif path")[0]
    assert "post_quantum status failed" in chunk
    assert "except Exception as e:" in chunk
    # Exception branch must 503, not paint enabled True with error string.
    except_part = chunk.split("except Exception")[1]
    assert "enabled\": True" not in except_part
    assert "_error(503" in except_part


def test_sharding_balance_satoshi_needle():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path.startswith("/sharding/balance/")')[1].split("elif path")[0]
    assert "balance_satoshi" in chunk
    assert "float(bc.get_balance" not in chunk
    assert "float(sh.get_shard_balance" not in chunk


def test_mev_no_float_value_or_fee_times_1e9():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "value=float(tx.amount)" not in src
    assert 'value=float(t.get("value"' not in src
    assert "tx.fee * 1e9" not in src


def test_validator_keys_derive_failure_unavailable():
    from crypto.validator_keys import ValidatorKeys

    mgr = ValidatorKeys.__new__(ValidatorKeys)
    att = {
        "validator": "0x" + "a" * 40,
        "signature": "ab" * 32,
        "public_key": "cd" * 33,
    }
    with patch("crypto.keys.KeyGenerator.derive_address", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="unavailable"):
            mgr.verify_attestation(att)
