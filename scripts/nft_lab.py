#!/usr/bin/env python3
"""NFT marketplace lab — offline self-check (NOT soak / NOT prod feature_nft / NOT ERC-721).

Verifies satoshi price honesty, mint/list/buy UoW, prod mesh flag freeze.
Optional live staging :19080 stats read if port open.
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.nft import HONESTY, NFTMarketplace, resolve_price_satoshi
from runtime.amount import to_satoshi
from storage.database import Database


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _check_prod_flags() -> str | None:
    for name in ("node.prod.mesh1.json", "node.prod.mesh2.json", "node.prod.mesh3.json"):
        path = ROOT / "docker" / name
        if not path.is_file():
            return f"missing {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("feature_nft") is not False:
            return f"{name}: feature_nft must be false"
    return None


def main() -> int:
    print("nft_lab - NOT soak / NOT mainnet / NOT prod feature_nft / NOT ERC-721")
    print("honesty:", HONESTY)

    err = _check_prod_flags()
    if err:
        return _fail(err)
    print("OK: prod mesh feature_nft=false")

    http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if "_nft_sprout_enabled" not in http_py:
        return _fail("HTTP must gate NFT sprouts via _nft_sprout_enabled")
    if '"offers_escrow": False' in http_py.split('path == "/nft/offer"')[1].split("elif path ==")[0]:
        return _fail("POST /nft/offer must not hardcode offers_escrow=False")
    main_py = (ROOT / "main.py").read_text(encoding="utf-8")
    if 'getattr(config, "feature_nft", False)' not in main_py:
        return _fail("main.py feature_nft default must be False")
    print("OK: HTTP NFT sprout gate + offer escrow honesty")

    try:
        resolve_price_satoshi(price=1.25)
        return _fail("expected refuse dust float price")
    except ValueError:
        pass
    assert resolve_price_satoshi(price_satoshi=1_500_000) == 1_500_000
    assert resolve_price_satoshi(price=2.0) == int(to_satoshi(2))

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "nft_lab.db"))
        db.initialize()
        seller = "0x" + "a" * 40
        buyer = "0x" + "b" * 40
        db.set_balance(seller, 1000.0)
        db.set_balance(buyer, 1000.0)

        m = NFTMarketplace(db=db)
        # clear genesis so mint path is clean
        m.tokens.clear()
        st = m.get_stats()
        if st.get("consensus_wired") is not False:
            return _fail("consensus_wired must be False")
        if st.get("tier") != "app-profile":
            return _fail("tier must be app-profile")

        r = m.mint("lab1", "Lab", "d", "img", seller, price=10.0)
        if not r.get("success"):
            return _fail(f"mint failed: {r}")
        if r.get("price_satoshi") != int(to_satoshi(10)):
            return _fail("mint price_satoshi mismatch")

        listed = m.list_for_sale("lab1", seller, price_satoshi=int(to_satoshi(25)))
        if not listed.get("success"):
            return _fail(f"list failed: {listed}")

        dust = m.list_for_sale("lab1", seller, price=1.25)
        if dust.get("success"):
            return _fail("dust float list must refuse")

        buy = m.buy("lab1", buyer)
        if not buy.get("success"):
            return _fail(f"buy failed: {buy}")
        if buy.get("price_satoshi") != int(to_satoshi(25)):
            return _fail("buy price_satoshi mismatch")
        tok = m.get_token("lab1")
        if not tok or tok["owner"] != buyer:
            return _fail("owner after buy mismatch")
        if tok.get("price_satoshi") is None:
            return _fail("token missing price_satoshi")

        # offer / cancel / expired accept (soft escrow hold)
        db.set_balance(seller, 1000.0)
        db.set_balance(buyer, 1000.0)
        r2 = m.mint("lab2", "Lab2", "d", "img", seller, price=5.0)
        if not r2.get("success"):
            return _fail(f"mint lab2 failed: {r2}")
        bal_b0 = db.get_balance(buyer)
        oid = m.make_offer("lab2", buyer, price_satoshi=int(to_satoshi(5)), hours=1)
        if not oid:
            return _fail("make_offer failed")
        if int(m.offers[oid].get("held_satoshi") or 0) != int(to_satoshi(5)):
            return _fail("offer soft escrow hold missing")
        if abs(db.get_balance(buyer) - (bal_b0 - 5.0)) > 1e-9:
            return _fail("make_offer did not debit soft escrow")
        if not m.cancel_offer(oid, buyer).get("success"):
            return _fail("cancel_offer failed")
        if abs(db.get_balance(buyer) - bal_b0) > 1e-9:
            return _fail("cancel_offer did not refund soft escrow")
        oid2 = m.make_offer("lab2", buyer, price_satoshi=int(to_satoshi(5)), hours=1)
        m.offers[oid2]["expires_at"] = 0
        exp = m.accept_offer(oid2, seller)
        if exp.get("success"):
            return _fail("expired offer must refuse")

        # auction: soft escrow bid hold, cancel refund, then finalize after ends_at
        db.set_balance(seller, 1000.0)
        db.set_balance(buyer, 1000.0)
        assert m.mint("lab3", "Lab3", "d", "img", seller, price=5.0).get("success")
        aid = m.create_auction(
            "lab3",
            seller,
            start_price_satoshi=int(to_satoshi(1)),
            reserve_price_satoshi=int(to_satoshi(1)),
            hours=1,
        )
        if not aid:
            return _fail("create_auction failed")
        if m.finalize_auction(aid).get("success"):
            return _fail("early finalize must refuse")
        assert m.place_bid(aid, buyer, amount_satoshi=int(to_satoshi(2))).get("success")
        held = int(m.auctions[aid].get("held_satoshi") or 0)
        if held != int(to_satoshi(2)):
            return _fail(f"auction soft escrow hold mismatch: {held}")

        assert m.mint("lab3b", "Lab3b", "d", "img", seller, price=5.0).get("success")
        aid2 = m.create_auction(
            "lab3b",
            seller,
            start_price_satoshi=int(to_satoshi(1)),
            reserve_price_satoshi=int(to_satoshi(1)),
            hours=1,
        )
        if not aid2:
            return _fail("create_auction lab3b failed")
        assert m.place_bid(aid2, buyer, amount_satoshi=int(to_satoshi(3))).get("success")
        bal_pre_cancel = db.get_balance(buyer)
        cancel = m.cancel_auction(aid2, seller)
        if not cancel.get("success"):
            return _fail(f"cancel_auction failed: {cancel}")
        if int(cancel.get("refunded_satoshi") or 0) != int(to_satoshi(3)):
            return _fail("cancel_auction refund mismatch")
        if abs(db.get_balance(buyer) - (bal_pre_cancel + 3.0)) > 1e-9:
            return _fail("cancel_auction did not refund bidder balance")

        m.auctions[aid]["ends_at"] = 0
        fin = m.finalize_auction(aid)
        if not fin.get("success"):
            return _fail(f"finalize after ends_at failed: {fin}")
        if m.get_token("lab3")["owner"] != buyer:
            return _fail("auction owner mismatch")

        # delist
        db.set_balance(seller, 1000.0)
        assert m.mint("lab4", "Lab4", "d", "img", seller, price=8.0).get("success")
        assert m.list_for_sale("lab4", seller, price_satoshi=int(to_satoshi(8))).get("success")
        if not m.delist("lab4", seller).get("success"):
            return _fail("delist failed")
        if m.get_listings():
            # other leftover listings ok; lab4 must not be listed
            if any(x.get("token_id") == "lab4" for x in m.get_listings()):
                return _fail("lab4 still listed after delist")

        st = m.get_stats()
        if st.get("enabled") is not True:
            return _fail("enabled must follow balance backend")
        if st.get("offers_escrow") is not True or st.get("auction_escrow") is not True:
            return _fail("soft escrow flags must be true when balance-bound")
        if "soft satoshi hold" not in str(st.get("escrow_note") or ""):
            return _fail("escrow_note must disclose soft hold")

        try:
            db.close()
        except Exception:
            pass

    # optional staging read (HTTP only — pin has no dup_sdk package)
    if _port_open("127.0.0.1", 19080):
        try:
            import json as _json
            import urllib.request

            req = urllib.request.Request(
                "http://127.0.0.1:19080/nft/stats",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                stats = _json.loads(resp.read().decode("utf-8"))
            print("OK: staging /nft/stats keys", sorted(list(stats.keys()))[:10])
        except Exception as exc:
            print(f"WARN: staging nft stats: {exc}")
    else:
        print("SKIP: staging :19080 not open")

    print("OK: nft_lab mint/list/buy/offer/auction/cancel_auction soft-escrow honesty")
    print("RESULT: PASS nft_lab")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
