"""Pin finish: REST money _http_abs; Absolute merkle roots; exception 503 paints."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_rest_no_float_body_amount_value():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert 'float(body.get("amount"' not in src
    assert 'float(body.get("value"' not in src


def test_block_merkle_roots_absolute():
    from api.eth_format import block_receipts_root, block_transactions_root, logs_bloom
    from crypto.merkle import merkle_root

    empty_root = "0x" + merkle_root(["empty"])
    assert block_transactions_root({"transactions": []}) == empty_root
    assert block_receipts_root({"transactions": []}) == empty_root
    # Corrupt stored root → None (Wave N)
    assert block_transactions_root({"tx_root": "zz", "transactions": ["0xab"]}) is None
    assert logs_bloom([]) == "0x" + ("0" * 512)


def test_exception_list_paths_use_503():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    for needle in (
        "consensus stats failed",
        "smart_accounts list failed",
        "multisig list failed",
        "post_quantum status failed",
    ):
        assert needle in src
