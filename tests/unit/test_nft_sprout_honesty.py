"""NFT sprout GET honesty — feature_nft=false must not paint enabled."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_nft_sprout_helpers_fail_closed_when_flag_off():
    from api.http import _nft_disabled_payload, _nft_sprout_enabled

    cfg = SimpleNamespace(feature_nft=False, is_production=True)
    enabled, loaded = _nft_sprout_enabled(cfg, object())
    assert enabled is False
    assert loaded is True

    cfg2 = SimpleNamespace(feature_nft=True, is_production=False)
    enabled2, loaded2 = _nft_sprout_enabled(cfg2, object())
    assert enabled2 is True
    assert loaded2 is True

    payload = _nft_disabled_payload(loaded=True)
    assert payload["enabled"] is False
    assert payload["loaded"] is True
    assert payload["consensus_wired"] is False
    assert "honesty" in payload


def test_nft_get_stats_enabled_follows_balance_backend():
    from features.nft import HONESTY, NFTMarketplace

    nft = NFTMarketplace(db=None)
    st = nft.get_stats()
    assert st["enabled"] is False
    assert st["honesty"] == HONESTY
    assert st["consensus_wired"] is False


def test_nft_sprout_http_source_needles():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "def _nft_sprout_enabled" in src
    assert "def _nft_disabled_payload" in src
    for path in (
        '"/nft/listings"',
        '"/nft/auctions"',
        '"/nft/offers"',
        '"/nft/sales"',
        '"/nft/marketplace"',
        '"/nft/stats"',
    ):
        chunk = src.split(f"path == {path}")[1].split("elif path ==")[0]
        assert "_nft_sprout_enabled" in chunk, path
        assert "_nft_disabled_payload" in chunk, path
