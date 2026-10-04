"""Experimental: list endpoints 503 on failure; /wallet/create no hash-demo address."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_wallet_create_no_invented_address():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/wallet/create"')[1].split("elif path")[0]
    assert "ecdsa not available" not in chunk
    assert "wallet create unavailable" in chunk
    assert "sha256_hex(str(_t.time())" not in chunk


def test_list_exception_paths_use_503():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    for needle in (
        "consensus stats failed",
        "smart_accounts list failed",
        "multisig list failed",
    ):
        assert needle in src


def test_zk_not_implemented_is_501_not_valid_false():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    # Refused educational ZK must not paint JSON valid:false with enabled:true.
    assert '"enabled": True,\n                                "valid": False' not in src
    assert "zk prove unavailable" in src
    # GET /zk/prove/range NotImplemented → 501
    chunk = src.split('path == "/zk/prove/range"')[1].split("elif path")[0]
    assert "_error(501" in chunk
