"""NFT marketplace port (ADR 0016 Profile C — app staging).

Industrial L1 must not call Rocks NFT helpers from transport without this port.
Balance/fee mutations belong on the same apply / Storage UoW path as L1 txs;
``NullNftMarketplacePort`` is the fail-closed default when FEATURE_NFT is off.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from runtime.amount import money_abs


@runtime_checkable
class NftMarketplacePort(Protocol):
    """Port for NFT marketplace operations (staging / app profile)."""

    def mint(
        self,
        token_id: str,
        creator: str,
        name: str,
        description: str = "",
        image_url: str = "",
        *,
        price: float = 0.0,
        price_satoshi: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mint a token; fee debit must be UoW-safe on the bound store."""
        ...

    def list_for_sale(
        self,
        token_id: str,
        owner: str,
        price: Optional[float] = None,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        ...

    def delist(self, token_id: str, owner: str) -> Dict[str, Any]:
        ...

    def buy(self, token_id: str, buyer: str) -> Dict[str, Any]:
        """Purchase; ABS transfers must not bypass tip apply when on L1 balances."""
        ...

    def make_offer(
        self,
        token_id: str,
        bidder: str,
        price: float = 0.0,
        hours: int = 24,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        ...

    def accept_offer(self, offer_id: str, seller: str) -> Dict[str, Any]:
        ...

    def cancel_offer(self, offer_id: str, bidder: str) -> Dict[str, Any]:
        ...

    def create_auction(
        self,
        token_id: str,
        seller: str,
        start_price: float,
        reserve_price: float,
        hours: int = 24,
        *,
        start_price_satoshi: Optional[int] = None,
        reserve_price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        ...

    def place_bid(
        self,
        auction_id: str,
        bidder: str,
        amount: float = 0.0,
        *,
        amount_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        ...

    def finalize_auction(self, auction_id: str) -> Dict[str, Any]:
        ...

    def cancel_auction(self, auction_id: str, seller: str) -> Dict[str, Any]:
        ...

    def get_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        ...

    def list_tokens(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        ...

    def get_listings(self) -> List[Dict[str, Any]]:
        ...

    def get_stats(self) -> Dict[str, Any]:
        ...


def _disabled(op: str) -> Dict[str, Any]:
    return {
        "success": False,
        "ok": False,
        "error": "nft_disabled",
        "op": op,
        "adr": "0016",
    }


class NullNftMarketplacePort:
    """Fail-closed NFT port when the sprout is disabled (prod mesh)."""

    def mint(
        self,
        token_id: str,
        creator: str,
        name: str,
        description: str = "",
        image_url: str = "",
        *,
        price: float = 0.0,
        price_satoshi: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return _disabled("mint")

    def list_for_sale(
        self,
        token_id: str,
        owner: str,
        price: Optional[float] = None,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        return _disabled("list_for_sale")

    def delist(self, token_id: str, owner: str) -> Dict[str, Any]:
        return _disabled("delist")

    def buy(self, token_id: str, buyer: str) -> Dict[str, Any]:
        return _disabled("buy")

    def make_offer(
        self,
        token_id: str,
        bidder: str,
        price: float = 0.0,
        hours: int = 24,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        return _disabled("make_offer")

    def accept_offer(self, offer_id: str, seller: str) -> Dict[str, Any]:
        return _disabled("accept_offer")

    def cancel_offer(self, offer_id: str, bidder: str) -> Dict[str, Any]:
        return _disabled("cancel_offer")

    def create_auction(
        self,
        token_id: str,
        seller: str,
        start_price: float,
        reserve_price: float,
        hours: int = 24,
        *,
        start_price_satoshi: Optional[int] = None,
        reserve_price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        return _disabled("create_auction")

    def place_bid(
        self,
        auction_id: str,
        bidder: str,
        amount: float = 0.0,
        *,
        amount_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        return _disabled("place_bid")

    def finalize_auction(self, auction_id: str) -> Dict[str, Any]:
        return _disabled("finalize_auction")

    def cancel_auction(self, auction_id: str, seller: str) -> Dict[str, Any]:
        return _disabled("cancel_auction")

    def get_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        return None

    def list_tokens(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_listings(self) -> List[Dict[str, Any]]:
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "execution_bound": False,
            "offers_escrow": False,
            "auction_escrow": False,
            "escrow_note": "nft sprout off / NullNftMarketplacePort",
            "tier": "app-profile",
            "adr": "0016",
            "consensus_wired": False,
            "honesty": (
                "nft marketplace sprout — not consensus / prod feature_nft=false"
            ),
        }


class NftMarketplaceAdapter:
    """Adapt legacy ``NFTMarketplace`` to ``NftMarketplacePort``."""

    def __init__(self, marketplace: Any) -> None:
        if marketplace is None:
            raise ValueError("marketplace is required")
        self._m = marketplace

    def mint(
        self,
        token_id: str,
        creator: str,
        name: str,
        description: str = "",
        image_url: str = "",
        *,
        price: float = 0.0,
        price_satoshi: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _ = metadata  # reserved; core mint does not persist free-form metadata yet
        fn = getattr(self._m, "mint", None)
        if not callable(fn):
            return {"success": False, "error": "mint_unsupported"}
        # Core signature: mint(token_id, name, description, image_url, creator, price, ...)
        result = fn(
            token_id,
            name,
            description,
            image_url,
            creator,
            price,
            price_satoshi=price_satoshi,
        )
        if isinstance(result, dict):
            out = dict(result)
            out.setdefault("success", bool(out.get("success", out.get("ok", False))))
            return out
        return {"success": True, "token": getattr(result, "to_dict", lambda: result)()}

    def list_for_sale(
        self,
        token_id: str,
        owner: str,
        price: Optional[float] = None,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        fn = getattr(self._m, "list_for_sale", None) or getattr(self._m, "sell", None)
        if not callable(fn):
            return {"success": False, "error": "list_unsupported"}
        if price_satoshi is not None:
            result = fn(token_id, owner, price_satoshi=int(price_satoshi))
        else:
            result = fn(token_id, owner, money_abs(price or 0, field="price"))
        return result if isinstance(result, dict) else {"success": True, "result": result}

    def delist(self, token_id: str, owner: str) -> Dict[str, Any]:
        fn = getattr(self._m, "delist", None)
        if not callable(fn):
            return {"success": False, "error": "delist_unsupported"}
        result = fn(token_id, owner)
        return result if isinstance(result, dict) else {"success": True, "result": result}

    def buy(self, token_id: str, buyer: str) -> Dict[str, Any]:
        fn = getattr(self._m, "buy", None) or getattr(self._m, "purchase", None)
        if not callable(fn):
            return {"success": False, "error": "buy_unsupported"}
        result = fn(token_id, buyer)
        return result if isinstance(result, dict) else {"success": True, "result": result}

    def make_offer(
        self,
        token_id: str,
        bidder: str,
        price: float = 0.0,
        hours: int = 24,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        fn = getattr(self._m, "make_offer", None)
        if not callable(fn):
            return {"success": False, "error": "offer_unsupported"}
        oid = fn(token_id, bidder, price, hours, price_satoshi=price_satoshi)
        if oid:
            return {"success": True, "offer_id": oid}
        return {"success": False, "error": "offer_refused"}

    def accept_offer(self, offer_id: str, seller: str) -> Dict[str, Any]:
        fn = getattr(self._m, "accept_offer", None)
        if not callable(fn):
            return {"success": False, "error": "accept_unsupported"}
        result = fn(offer_id, seller)
        return result if isinstance(result, dict) else {"success": True, "result": result}

    def cancel_offer(self, offer_id: str, bidder: str) -> Dict[str, Any]:
        fn = getattr(self._m, "cancel_offer", None)
        if not callable(fn):
            return {"success": False, "error": "cancel_unsupported"}
        result = fn(offer_id, bidder)
        return result if isinstance(result, dict) else {"success": True, "result": result}

    def create_auction(
        self,
        token_id: str,
        seller: str,
        start_price: float,
        reserve_price: float,
        hours: int = 24,
        *,
        start_price_satoshi: Optional[int] = None,
        reserve_price_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        fn = getattr(self._m, "create_auction", None)
        if not callable(fn):
            return {"success": False, "error": "auction_unsupported"}
        aid = fn(
            token_id,
            seller,
            start_price,
            reserve_price,
            hours,
            start_price_satoshi=start_price_satoshi,
            reserve_price_satoshi=reserve_price_satoshi,
        )
        if aid:
            return {"success": True, "auction_id": aid}
        return {"success": False, "error": "auction_refused"}

    def place_bid(
        self,
        auction_id: str,
        bidder: str,
        amount: float = 0.0,
        *,
        amount_satoshi: Optional[int] = None,
    ) -> Dict[str, Any]:
        fn = getattr(self._m, "place_bid", None)
        if not callable(fn):
            return {"success": False, "error": "bid_unsupported"}
        result = fn(auction_id, bidder, amount, amount_satoshi=amount_satoshi)
        return result if isinstance(result, dict) else {"success": True, "result": result}

    def finalize_auction(self, auction_id: str) -> Dict[str, Any]:
        fn = getattr(self._m, "finalize_auction", None)
        if not callable(fn):
            return {"success": False, "error": "finalize_unsupported"}
        result = fn(auction_id)
        return result if isinstance(result, dict) else {"success": True, "result": result}

    def cancel_auction(self, auction_id: str, seller: str) -> Dict[str, Any]:
        fn = getattr(self._m, "cancel_auction", None)
        if not callable(fn):
            return {"success": False, "error": "cancel_auction_unsupported"}
        result = fn(auction_id, seller)
        return result if isinstance(result, dict) else {"success": True, "result": result}

    def get_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        fn = getattr(self._m, "get_token", None)
        if not callable(fn):
            tok = getattr(self._m, "tokens", {}).get(token_id)
            if tok is None:
                return None
            return tok.to_dict() if hasattr(tok, "to_dict") else dict(tok)
        result = fn(token_id)
        if result is None:
            return None
        return result if isinstance(result, dict) else result.to_dict()

    def list_tokens(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        if owner is not None and hasattr(self._m, "get_by_owner"):
            raw = self._m.get_by_owner(owner)
        else:
            fn = getattr(self._m, "list_tokens", None) or getattr(self._m, "get_all", None)
            if callable(fn):
                raw = fn()
            else:
                raw = list(getattr(self._m, "tokens", {}).values())
        out: List[Dict[str, Any]] = []
        for item in raw or []:
            if hasattr(item, "to_dict"):
                d = item.to_dict()
            elif isinstance(item, dict):
                d = item
            else:
                continue
            if owner and d.get("owner") != owner:
                continue
            out.append(d)
        return out

    def get_listings(self) -> List[Dict[str, Any]]:
        fn = getattr(self._m, "get_listings", None) or getattr(self._m, "get_on_sale", None)
        if callable(fn):
            raw = fn()
            return [x if isinstance(x, dict) else x.to_dict() for x in (raw or [])]
        return [t for t in self.list_tokens() if t.get("for_sale")]

    def get_stats(self) -> Dict[str, Any]:
        fn = getattr(self._m, "get_stats", None)
        if callable(fn):
            stats = fn()
            if isinstance(stats, dict):
                stats = dict(stats)
                # Never invent enabled=True over an explicit False from core.
                if "enabled" not in stats:
                    stats["enabled"] = bool(stats.get("execution_bound") or stats.get("balance_backend"))
                stats.setdefault("tier", "app-profile")
                stats.setdefault("adr", "0016")
                return stats
        return {
            "enabled": False,
            "tier": "app-profile",
            "adr": "0016",
            "token_count": len(getattr(self._m, "tokens", {}) or {}),
        }
