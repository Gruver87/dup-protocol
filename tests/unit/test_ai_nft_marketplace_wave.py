"""AI/NFT marketplace honesty — settle rollback, offer/auction guards, ops classifier."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_nft_settle_raises_on_royalty_fail_rolls_back_balances():
    from features.nft import NFTMarketplace
    from runtime.amount import to_satoshi
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(f"{tmp}/nft_royalty.db")
    db.initialize()
    seller = "0x" + "a" * 40
    buyer = "0x" + "b" * 40
    creator = "0x" + "c" * 40
    db.set_balance(seller, 1000.0)
    db.set_balance(buyer, 1000.0)
    db.set_balance(creator, 1.0)

    m = NFTMarketplace(db=db)
    m.tokens.clear()
    assert m.mint("t1", "n", "d", "i", creator, price=10.0)["success"]
    m.tokens["t1"].owner = seller
    m.tokens["t1"].for_sale = True
    m.tokens["t1"].price = 10.0
    m.tokens["t1"].price_satoshi = int(to_satoshi(10))

    real_apply = __import__(
        "runtime.amount", fromlist=["apply_store_delta_satoshi"]
    ).apply_store_delta_satoshi
    calls = {"n": 0}

    def _flaky(store, addr, delta, **kw):
        calls["n"] += 1
        if calls["n"] >= 3 and addr == creator:
            return False
        return real_apply(store, addr, delta, **kw)

    import runtime.amount as amt

    monkey = pytest.MonkeyPatch()
    monkey.setattr(amt, "apply_store_delta_satoshi", _flaky)
    try:
        bal_b0 = db.get_balance(buyer)
        bal_s0 = db.get_balance(seller)
        out = m.buy("t1", buyer)
        assert out.get("success") is False
        assert "nft_settle_failed" in str(out.get("error", "")) or "nft_uow" in str(
            out.get("error", "")
        )
        assert db.get_balance(buyer) == bal_b0
        assert db.get_balance(seller) == bal_s0
        assert m.get_token("t1")["owner"] == seller
    finally:
        monkey.undo()


def test_offer_expired_refuse_and_cancel():
    from features.nft import NFTMarketplace
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(f"{tmp}/nft_offer.db")
    db.initialize()
    seller = "0x" + "a" * 40
    buyer = "0x" + "b" * 40
    db.set_balance(seller, 1000.0)
    db.set_balance(buyer, 1000.0)
    m = NFTMarketplace(db=db)
    m.tokens.clear()
    assert m.mint("o1", "O", "d", "i", seller, price=5.0)["success"]
    oid = m.make_offer("o1", buyer, price=5.0, hours=1)
    assert oid
    m.offers[oid]["expires_at"] = int(time.time()) - 5
    bad = m.accept_offer(oid, seller)
    assert bad["success"] is False
    assert "expired" in bad["error"].lower()

    oid2 = m.make_offer("o1", buyer, price=5.0, hours=1)
    assert m.cancel_offer(oid2, buyer)["success"] is True
    assert m.accept_offer(oid2, seller)["success"] is False


def test_finalize_auction_before_ends_at_refused():
    from features.nft import NFTMarketplace
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(f"{tmp}/nft_auc.db")
    db.initialize()
    seller = "0x" + "a" * 40
    buyer = "0x" + "b" * 40
    db.set_balance(seller, 1000.0)
    db.set_balance(buyer, 1000.0)
    m = NFTMarketplace(db=db)
    m.tokens.clear()
    assert m.mint("a1", "A", "d", "i", seller, price=5.0)["success"]
    aid = m.create_auction("a1", seller, start_price=1.0, reserve_price=1.0, hours=1)
    assert aid
    assert m.place_bid(aid, buyer, amount=2.0)["success"]
    early = m.finalize_auction(aid)
    assert early["success"] is False
    assert "ends_at" in early["error"] or "still active" in early["error"].lower()


def test_nft_listings_and_delist():
    from features.nft import NFTMarketplace
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(f"{tmp}/nft_delist.db")
    db.initialize()
    owner = "0x" + "a" * 40
    db.set_balance(owner, 1000.0)
    m = NFTMarketplace(db=db)
    m.tokens.clear()
    assert m.mint("d1", "D", "d", "i", owner, price=5.0)["success"]
    assert m.get_token("d1")["for_sale"] is True
    listings = m.get_listings()
    assert any(t["token_id"] == "d1" for t in listings)
    out = m.delist("d1", owner)
    assert out["success"] is True
    assert out["for_sale"] is False
    assert not any(t["token_id"] == "d1" for t in m.get_listings())


def test_nft_stats_enabled_follows_balance_backend():
    from features.nft import NFTMarketplace

    m = NFTMarketplace(db=None)
    st = m.get_stats()
    assert st["enabled"] is False
    assert st["offers_escrow"] is False
    assert st["auction_escrow"] is False


def test_prod_mesh_ai_flags_remain_false():
    for name in ("node.prod.mesh1.json", "node.prod.mesh2.json", "node.prod.mesh3.json"):
        path = ROOT / "docker" / name
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("feature_ai_agents") is False
        assert data.get("feature_ai_validator") is False
        assert data.get("feature_mev") is False
        assert data.get("feature_nft") is False


def test_ops_anomaly_classifier():
    from features.ai_ops import classify_anomaly

    assert classify_anomaly(
        ready={"status": "ready", "checks": {"state_consistent": True}},
        status={"height": 10, "peer_count": 2, "mesh_min_peers": 2, "sync_stalled": False},
    ) == []
    findings = classify_anomaly(
        ready={"status": "not_ready", "checks": {"state_consistent": False}},
        status={"height": 0, "peer_count": 0, "mesh_min_peers": 2, "sync_stalled": True},
    )
    codes = {f["code"] for f in findings}
    assert "ready_not_ready" in codes
    assert "check_state_consistent_false" in codes
    assert "sync_stalled" in codes


def test_ai_validator_mev_profit_satoshi_none():
    from features.ai_validator import AIValidatorEngine

    eng = AIValidatorEngine()
    out = eng.detect_mev_opportunity([1, 2, 3])
    assert out["invented_numbers"] is False
    for opp in out["opportunities"]:
        assert opp["profit"] is None
        assert opp["profit_satoshi"] is None


def test_http_delist_source_needle():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert 'path == "/nft/delist"' in src
    assert "nft_delist" in src
    assert "hasattr(nft, \"delist\")" in src or "hasattr(nft, 'delist')" in src


def test_main_no_ai_validator_forge_hook():
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "ai_validator.update_performance" not in src
