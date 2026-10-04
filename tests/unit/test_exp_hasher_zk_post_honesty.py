"""Exp mid-soak: Hasher no invent gas; POST /zk/prove/range no valid:true paint."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_hasher_requires_gas_limit_no_invent():
    from crypto.hashing import Hasher

    with pytest.raises(ValueError, match="gas_limit required"):
        Hasher.hash_transaction({"from": "a", "to": "b", "value": 1, "nonce": 0})

    h1 = Hasher.hash_transaction(
        {"from": "a", "to": "b", "value": 1, "nonce": 0, "gas_limit": 21000}
    )
    h2 = Hasher.hash_transaction(
        {"from": "a", "to": "b", "value": 1, "nonce": 0, "gas_limit": 21000}
    )
    assert h1 == h2
    assert len(h1) == 64

    # Missing gas_price must not invent default into digest (stable without it).
    h3 = Hasher.hash_transaction(
        {
            "from": "a",
            "to": "b",
            "value": 1,
            "nonce": 0,
            "gas_limit": 21000,
            "gas_price": 1,
        }
    )
    assert h3 != h1


def test_post_zk_range_no_forced_valid_true():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    # Second (POST) handler after create-tx block region uses educational_only.
    parts = src.split('path == "/zk/prove/range"')
    assert len(parts) >= 3  # GET + POST (+ possibly more)
    post_chunk = parts[2].split("elif path")[0]
    assert '"valid": True' not in post_chunk
    assert "educational_only" in post_chunk


def test_zk_create_tx_requires_amount_keys():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/zk/create-tx"')[1].split("elif path")[0]
    assert "amount or amount_satoshi required" in chunk
    assert 'amount", 1)' not in chunk
    assert "_http_amount_abs" in chunk


def test_hasher_source_no_default_21000():
    src = (ROOT / "crypto" / "hashing.py").read_text(encoding="utf-8")
    assert 'gas_limit", 21000)' not in src
    assert 'gas_price", 1)' not in src
