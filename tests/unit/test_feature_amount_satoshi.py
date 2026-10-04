"""Feature sprout money persist dual-writes *_satoshi columns."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.amount import to_satoshi
from storage.database import Database


def _db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    db.initialize()
    return db, path


def test_plasma_deposit_and_exit_amount_satoshi():
    db, path = _db()
    try:
        db.save_plasma_deposit(
            {
                "id": "d1",
                "from": "0xfrom",
                "amount": 12.5,
                "main_tx_hash": "0x1",
                "created_at": 1,
                "status": "confirmed",
            }
        )
        deps = db.get_plasma_deposits()
        assert deps[0]["amount_satoshi"] == int(to_satoshi(12.5))
        db.save_plasma_exit(
            {
                "id": "e1",
                "deposit_id": "d1",
                "user": "0xuser",
                "amount": 12.5,
                "created_at": 2,
                "status": "pending",
            }
        )
        exits = db.get_plasma_exits()
        assert exits[0]["amount_satoshi"] == int(to_satoshi(12.5))
    finally:
        db.close()
        os.remove(path)


def test_lightning_channel_and_payment_satoshi():
    db, path = _db()
    try:
        db.save_lightning_channel(
            {
                "channel_id": "c1",
                "node1": "n1",
                "node2": "n2",
                "capacity": 10.0,
                "balance1": 6.0,
                "balance2": 4.0,
                "status": "open",
                "fee_rate": 0.00001,
                "created_at": 1,
            }
        )
        ch = db.get_lightning_channels()[0]
        assert ch["capacity_satoshi"] == int(to_satoshi(10.0))
        assert ch["balance1_satoshi"] == int(to_satoshi(6.0))
        assert ch["balance2_satoshi"] == int(to_satoshi(4.0))
        db.save_lightning_payment(
            {
                "payment_id": "p1",
                "channel_id": "c1",
                "from_node": "n1",
                "to_node": "n2",
                "amount": 1.25,
                "fee": 0.01,
                "status": "completed",
                "payment_hash": "h",
                "timestamp": 2,
            }
        )
        pay = db.get_lightning_payments()[0]
        assert pay["amount_satoshi"] == int(to_satoshi(1.25))
        assert pay["fee_satoshi"] == int(to_satoshi(0.01))
    finally:
        db.close()
        os.remove(path)


def test_crypto_will_amount_satoshi():
    db, path = _db()
    try:
        db.save_crypto_will(
            {
                "will_id": "w1",
                "owner": "0xo",
                "heir": "0xh",
                "amount": 100.0,
                "assets": {},
                "execution_time": 9,
                "created_at": 1,
                "status": "pending",
                "witnesses": [],
            }
        )
        wills = db.get_crypto_wills()
        assert wills[0]["amount_satoshi"] == int(to_satoshi(100.0))
    finally:
        db.close()
        os.remove(path)


def test_nft_and_channel_state_price_satoshi():
    db, path = _db()
    try:
        db.save_nft_token(
            {
                "token_id": "t1",
                "name": "n",
                "description": "",
                "image_url": "",
                "owner": "0xo",
                "creator": "0xc",
                "price": 3.5,
                "for_sale": True,
                "created_at": 1,
                "metadata": {},
            }
        )
        tok = db.get_nft_tokens()[0]
        assert tok["price_satoshi"] == int(to_satoshi(3.5))
        db.save_nft_offer(
            {
                "offer_id": "o1",
                "token_id": "t1",
                "bidder": "0xb",
                "price": 2.25,
                "expires_at": 9,
                "status": "pending",
                "created_at": 2,
            }
        )
        off = db.get_nft_offers()[0]
        assert off["price_satoshi"] == int(to_satoshi(2.25))
        db.save_nft_auction(
            {
                "auction_id": "a1",
                "token_id": "t1",
                "seller": "0xo",
                "start_price": 1.0,
                "reserve_price": 2.0,
                "current_bid": 1.5,
                "status": "active",
                "ends_at": 99,
                "created_at": 3,
            }
        )
        auc = db.get_nft_auctions()[0]
        assert auc["start_price_satoshi"] == int(to_satoshi(1.0))
        assert auc["reserve_price_satoshi"] == int(to_satoshi(2.0))
        assert auc["current_bid_satoshi"] == int(to_satoshi(1.5))
        db.save_nft_sale(
            {
                "token_id": "t1",
                "from": "0xo",
                "to": "0xb",
                "price": 3.5,
                "type": "buy",
                "timestamp": 4,
            }
        )
        sale = db.get_nft_sales()[0]
        assert sale["price_satoshi"] == int(to_satoshi(3.5))
        db.save_lightning_channel_state(
            {
                "channel_id": "c1",
                "version": 1,
                "balance1": 7.0,
                "balance2": 3.0,
                "state_hash": "h",
                "sig_node1": "",
                "sig_node2": "",
                "updated_at": 5,
            }
        )
        st = db.get_lightning_channel_state("c1")
        assert st is not None
        assert st["balance1_satoshi"] == int(to_satoshi(7.0))
        assert st["balance2_satoshi"] == int(to_satoshi(3.0))
    finally:
        db.close()
        os.remove(path)


def test_source_needles_feature_amount_satoshi():
    src = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    assert "_backfill_feature_amount_satoshi" in src
    assert '("plasma_deposits", "amount_satoshi"' in src
    assert '("lightning_channels", "capacity_satoshi"' in src
    assert '("crypto_wills", "amount_satoshi"' in src
    assert '("nft_tokens", "price_satoshi"' in src
    assert '("lightning_channel_states", "balance1_satoshi"' in src
    assert '("ai_agents", "total_profit_satoshi"' in src
    assert '("mev_simulations", "profit_satoshi"' in src
    rocks = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert "price_satoshi" in rocks
    assert 'f"{field}_satoshi"' in rocks


def test_ai_and_mev_profit_satoshi():
    db, path = _db()
    try:
        db.save_ai_agent(
            {
                "agent_id": "a1",
                "name": "bot",
                "owner": "0xo",
                "agent_type": "transformer",
                "status": "active",
                "created_at": 1,
                "last_action": 1,
                "performance_score": 0.5,
                "total_profit": 8.75,
                "actions_count": 2,
                "strategy": {},
                "memory": [],
            }
        )
        agent = db.get_ai_agents()[0]
        assert agent["total_profit_satoshi"] == int(to_satoshi(8.75))
        db.save_mev_simulation(
            {
                "sim_id": "s1",
                "sim_type": "arb",
                "profit": 0.42,
                "payload": {},
                "created_at": 2,
            }
        )
        sim = db.get_mev_simulations()[0]
        assert sim["profit_satoshi"] == int(to_satoshi(0.42))
    finally:
        db.close()
        os.remove(path)


def test_lightning_open_close_satoshi_debit():
    from features.lightning import LightningNetwork

    db, path = _db()
    try:
        addr = "0x" + "a" * 40
        peer = "0x" + "b" * 40
        db.update_balance(addr, 50.0)
        ln = LightningNetwork(node_address=addr, db=db)
        before = db.get_balance_satoshi(addr)
        cid = ln.open_channel(peer, 10.0)
        assert cid
        assert db.get_balance_satoshi(addr) == before - int(to_satoshi(10.0))
        ch = db.get_lightning_channels()[0]
        assert ch["capacity_satoshi"] == int(to_satoshi(10.0))
        assert ln.close_channel(cid) is True
        assert db.get_balance_satoshi(addr) == before
    finally:
        db.close()
        os.remove(path)


def test_resolve_price_satoshi_and_settle_raise():
    import pytest
    from features.nft import NFTMarketplace, resolve_price_satoshi

    with pytest.raises(ValueError, match="non-integral"):
        resolve_price_satoshi(price=1.25)
    assert resolve_price_satoshi(price_satoshi=42) == 42
    assert resolve_price_satoshi(price=10.0) == int(to_satoshi(10.0))

    src = (ROOT / "features" / "nft.py").read_text(encoding="utf-8")
    assert "def resolve_price_satoshi" in src
    assert "nft_uow_required" in src
    assert "Never return False after a partial" in src

    db, path = _db()
    try:
        seller = "0x" + "a" * 40
        buyer = "0x" + "b" * 40
        db.update_balance(seller, 100.0)
        db.update_balance(buyer, 5.0)
        nft = NFTMarketplace(db=db)
        nft.tokens.clear()
        r = nft.mint("t_settle", "n", "d", "i", seller, price=10.0)
        assert r["success"] is True
        assert r["price_satoshi"] == int(to_satoshi(10.0))
        listed = nft.list_for_sale("t_settle", seller, price_satoshi=int(to_satoshi(10.0)))
        assert listed["success"] is True
        buy = nft.buy("t_settle", buyer)
        assert buy["success"] is False
        assert "insufficient" in buy["error"]
    finally:
        db.close()
        os.remove(path)


def test_lightning_find_route_satoshi():
    from features.lightning import LightningChannel, LightningNetwork

    ln = LightningNetwork(node_address="n1", db=None)
    ln.channels["c1"] = LightningChannel("c1", "n1", "n2", 10.0, balance1=6.0, balance2=4.0)
    assert ln.find_route("n2", 5.0) == ["c1"]
    assert ln.find_route("n2", None, amount_satoshi=int(to_satoshi(5.0))) == ["c1"]
    assert ln.find_route("n2", 7.0) == []
    src = (ROOT / "features" / "lightning.py").read_text(encoding="utf-8")
    assert "need_sat, amount = resolve_amount_satoshi" in src
    assert "amount_satoshi=amt_sat" in src


def test_nft_offer_soft_escrow_hold_and_cancel():
    from features.nft import NFTMarketplace

    db, path = _db()
    try:
        seller = "0x" + "a" * 40
        buyer = "0x" + "b" * 40
        db.set_balance(seller, 1000.0)
        db.set_balance(buyer, 1000.0)
        nft = NFTMarketplace(db=db)
        nft.tokens.clear()
        assert nft.mint("e1", "E", "d", "i", seller, price=5.0)["success"]
        bal0 = db.get_balance(buyer)
        oid = nft.make_offer("e1", buyer, price_satoshi=int(to_satoshi(5)), hours=1)
        assert oid
        assert int(nft.offers[oid]["held_satoshi"]) == int(to_satoshi(5))
        assert abs(db.get_balance(buyer) - (bal0 - 5.0)) < 1e-9
        assert nft.get_stats()["offers_escrow"] is True
        assert nft.cancel_offer(oid, buyer)["success"] is True
        assert abs(db.get_balance(buyer) - bal0) < 1e-9

        oid2 = nft.make_offer("e1", buyer, price_satoshi=int(to_satoshi(5)), hours=1)
        assert oid2
        bal1 = db.get_balance(buyer)
        accepted = nft.accept_offer(oid2, seller)
        assert accepted["success"] is True
        assert nft.get_token("e1")["owner"] == buyer
        # Hold already debited on offer; accept credits seller/royalty only.
        assert abs(db.get_balance(buyer) - bal1) < 1e-9
        assert db.get_balance(seller) > 1000.0 - 1.0  # mint fee already paid
        http_src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        offer_chunk = http_src.split('path == "/nft/offer"')[1].split(
            'elif path == "/nft/cancel-offer"'
        )[0]
        assert "held_satoshi" in offer_chunk
        assert '"offers_escrow": False' not in offer_chunk
        assert 'path == "/nft/cancel-offer"' in http_src
    finally:
        db.close()
        os.remove(path)


def test_nft_auction_soft_escrow_bid_and_cancel():
    from features.nft import NFTMarketplace

    db, path = _db()
    try:
        seller = "0x" + "a" * 40
        buyer = "0x" + "b" * 40
        db.set_balance(seller, 1000.0)
        db.set_balance(buyer, 1000.0)
        nft = NFTMarketplace(db=db)
        nft.tokens.clear()
        assert nft.mint("e2", "E2", "d", "i", seller, price=5.0)["success"]
        aid = nft.create_auction(
            "e2",
            seller,
            start_price_satoshi=int(to_satoshi(1)),
            reserve_price_satoshi=int(to_satoshi(1)),
            hours=1,
        )
        assert aid
        assert nft.get_stats()["auction_escrow"] is True
        bal0 = db.get_balance(buyer)
        assert nft.place_bid(aid, buyer, amount_satoshi=int(to_satoshi(4)))["success"]
        assert int(nft.auctions[aid]["held_satoshi"]) == int(to_satoshi(4))
        assert abs(db.get_balance(buyer) - (bal0 - 4.0)) < 1e-9
        out = nft.cancel_auction(aid, seller)
        assert out["success"] is True
        assert int(out["refunded_satoshi"]) == int(to_satoshi(4))
        assert abs(db.get_balance(buyer) - bal0) < 1e-9
        http_src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        assert 'path == "/nft/cancel-auction"' in http_src
    finally:
        db.close()
        os.remove(path)
