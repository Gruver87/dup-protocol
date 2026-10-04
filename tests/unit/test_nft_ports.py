#!/usr/bin/env python3
"""NftMarketplacePort fail-closed + adapter smoke (ADR 0016)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.nft_ports import NftMarketplaceAdapter, NullNftMarketplacePort


def test_null_nft_port_fail_closed() -> None:
    port = NullNftMarketplacePort()
    assert port.mint("tid", "0xcreator", "n")["error"] == "nft_disabled"
    assert port.buy("t", "b")["success"] is False
    assert port.get_token("t") is None
    assert port.list_tokens() == []
    assert port.get_stats()["enabled"] is False
    assert port.get_listings() == []
    assert port.cancel_offer("o", "b")["success"] is False


def test_adapter_wraps_real_marketplace_mint() -> None:
    import tempfile
    from features.nft import NFTMarketplace
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(f"{tmp}/nft_port.db")
    db.initialize()
    creator = "0x" + "a" * 40
    db.set_balance(creator, 1000.0)
    m = NFTMarketplace(db=db)
    m.tokens.clear()
    port = NftMarketplaceAdapter(m)
    out = port.mint("p1", creator, "PortMint", "d", "img", price=1.0)
    assert out.get("success") is True
    assert port.get_token("p1")["owner"] == creator
    st = port.get_stats()
    assert st.get("enabled") is True
    assert st.get("offers_escrow") is True
    assert st.get("auction_escrow") is True
    null = NullNftMarketplacePort()
    assert null.cancel_auction("a", "s")["error"] == "nft_disabled"
    assert port.cancel_auction("missing", creator)["success"] is False

def test_adapter_wraps_simple_marketplace() -> None:
    class _Tok:
        def to_dict(self):
            return {"token_id": "1", "owner": "alice"}

    class _M:
        tokens = {"1": _Tok()}

        def get_stats(self):
            return {"tokens": 1, "enabled": False, "execution_bound": False}

        def get_token(self, token_id):
            return self.tokens.get(token_id)

        def get_by_owner(self, owner):
            return [self.tokens["1"].to_dict()] if owner == "alice" else []

    port = NftMarketplaceAdapter(_M())
    assert port.get_token("1")["owner"] == "alice"
    assert port.get_stats()["adr"] == "0016"
    assert port.get_stats()["enabled"] is False  # never invent over False
    assert port.list_tokens("alice")[0]["token_id"] == "1"
