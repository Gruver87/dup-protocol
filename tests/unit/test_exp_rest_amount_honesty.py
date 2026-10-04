"""Exp mid-soak: REST money paths prefer satoshi / refuse invent defaults."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _chunk(src: str, marker: str) -> str:
    return src.split(marker)[1].split("elif path")[0]


def test_nft_list_uses_http_amount_abs_no_price_invent():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    # Canonical POST /nft/list (first handler)
    assert 'path == "/nft/list"' in src
    first = src.split('path == "/nft/list"')[1].split("elif path")[0]
    assert "_http_amount_abs" in first
    assert 'price", 1.0)' not in first
    assert "price_satoshi" in first


def test_nft_bid_and_l2_bridge_ai_use_amount_abs():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    for marker in (
        'path == "/nft/bid"',
        'path == "/lightning/htlc/add"',
        'path == "/lightning/route"',
        'path == "/ai-agent/trade"',
        'path == "/bridge2/transfer"',
        'path == "/bridge/lock"',
        'path == "/devnet/faucet"',
    ):
        chunk = _chunk(src, marker)
        assert "_http_amount_abs" in chunk, marker


def test_faucet_no_default_100_invent():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = _chunk(src, 'path == "/devnet/faucet"')
    assert 'amount", 100)' not in chunk
    assert "_http_amount_abs" in chunk


def test_pool_spend_uses_http_amount_abs():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split("def _handle_devnet_pool_spend")[1].split("\ndef ")[0]
    assert "_http_amount_abs" in chunk
    assert '_http_abs(body.get("amount", 0))' not in chunk
    assert "amount_satoshi" in chunk


def test_no_invent_price_1_defaults():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert 'price", 1.0)' not in src
    assert 'start_price", 1.0)' not in src
    assert "/nft/list-legacy" in src or src.count('path == "/nft/list"') == 1


def test_nft_mint_auction_offer_use_amount_abs():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    for marker in (
        'path == "/nft/mint"',
        'path == "/nft/auction"',
        'path == "/nft/offer"',
    ):
        chunk = _chunk(src, marker)
        assert "_http_amount_abs" in chunk, marker
    assert src.count('path == "/nft/mint"') == 1
