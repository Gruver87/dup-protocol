#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFT Marketplace — ADR 0016 app-profile sprout (Profile C / staging).

Honesty: prod ``feature_nft=false`` on 778888. Not consensus-wired. Not ERC-721 claim.
Money prefers integer ``price_satoshi``; non-integral float-only prices refused.
Paid settle raises on failure so ``atomic()`` rolls back (no bool after partial debit).
"""

import json
import logging
import time
import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from crypto import native

logger = logging.getLogger(__name__)

HONESTY = (
    "nft marketplace sprout: app-profile / staging — "
    "not consensus / not prod 778888 feature_nft / not ERC-721 claim"
)


def resolve_price_satoshi(
    *,
    price: Optional[Any] = None,
    price_satoshi: Optional[Any] = None,
) -> int:
    """Prefer satoshi; refuse non-integral float ABS without satoshi twin."""
    from runtime.amount import to_satoshi

    if price_satoshi is not None:
        if isinstance(price_satoshi, bool):
            raise ValueError("price_satoshi: bool refused")
        if isinstance(price_satoshi, float):
            raise ValueError("price_satoshi must be int, got float")
        return max(0, int(price_satoshi))
    if price is None:
        raise ValueError("price or price_satoshi required")
    if isinstance(price, bool):
        raise ValueError("price: bool refused")
    if isinstance(price, float) and not price.is_integer():
        raise ValueError("non-integral float price refused without price_satoshi")
    return max(0, int(to_satoshi(price)))


@dataclass
class NFTToken:
    token_id: str
    name: str
    description: str
    image_url: str
    owner: str
    creator: str
    price: float = 0.0
    price_satoshi: int = 0
    for_sale: bool = False
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        from runtime.amount import from_satoshi_float, to_satoshi

        if self.price_satoshi:
            self.price_satoshi = max(0, int(self.price_satoshi))
            self.price = float(from_satoshi_float(self.price_satoshi))
        else:
            self.price_satoshi = int(to_satoshi(self.price or 0))
            self.price = float(from_satoshi_float(self.price_satoshi))

    def to_dict(self) -> Dict:
        return {
            "token_id": self.token_id,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "owner": self.owner,
            "creator": self.creator,
            "price": self.price,
            "price_satoshi": int(self.price_satoshi),
            "for_sale": self.for_sale,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class NFTMarketplace:
    """
    NFT маркетплейс, интегрированный с балансами блокчейна.
    При покупке/продаже ABS-балансы обновляются через db.
    """

    MINT_FEE = 1.0   # стоимость создания NFT в ABS
    ROYALTY = 0.05   # 5% роялти создателю при каждой продаже

    def __init__(self, db=None, bus=None):
        self.db = db
        self.bus = bus
        self.tokens: Dict[str, NFTToken] = {}
        self.offers: Dict[str, Dict] = {}
        self.auctions: Dict[str, Dict] = {}
        self.sales_history: List[Dict] = []
        self.lock = threading.RLock()
        self._load_from_db()
        if not self.tokens:
            self._load_genesis_collection()
            self._persist_all()
        print(f"[NFT] Marketplace initialized ({len(self.tokens)} tokens, "
              f"persisted={bool(self.db and hasattr(self.db, 'get_nft_tokens'))})")

    def _token_from_dict(self, d: Dict) -> NFTToken:
        return NFTToken(
            token_id=d["token_id"],
            name=d.get("name", ""),
            description=d.get("description", ""),
            image_url=d.get("image_url", ""),
            owner=d.get("owner", ""),
            creator=d.get("creator", ""),
            price=float(d.get("price", 0)),
            price_satoshi=int(d.get("price_satoshi") or 0),
            for_sale=bool(d.get("for_sale")),
            created_at=float(d.get("created_at", time.time())),
            metadata=d.get("metadata") or {},
        )

    def _load_from_db(self) -> None:
        if not self.db or not hasattr(self.db, "get_nft_tokens"):
            return
        for row in self.db.get_nft_tokens():
            self.tokens[row["token_id"]] = self._token_from_dict(row)
        if hasattr(self.db, "get_nft_offers"):
            for o in self.db.get_nft_offers():
                oid = o.get("offer_id")
                if oid:
                    self.offers[oid] = o
        if hasattr(self.db, "get_nft_auctions"):
            for a in self.db.get_nft_auctions():
                aid = a.get("auction_id")
                if aid:
                    self.auctions[aid] = a
        if hasattr(self.db, "get_nft_sales"):
            self.sales_history = self.db.get_nft_sales(limit=500)

    def _persist_token(self, token_id: str) -> None:
        if not self.db or not hasattr(self.db, "save_nft_token"):
            return
        t = self.tokens.get(token_id)
        if t:
            self.db.save_nft_token(t.to_dict())

    def _persist_offer(self, offer_id: str) -> None:
        if not self.db or not hasattr(self.db, "save_nft_offer"):
            return
        o = self.offers.get(offer_id)
        if o:
            self.db.save_nft_offer(o)

    def _persist_auction(self, auction_id: str) -> None:
        if not self.db or not hasattr(self.db, "save_nft_auction"):
            return
        a = self.auctions.get(auction_id)
        if a:
            self.db.save_nft_auction(a)

    def _record_sale(self, sale: Dict) -> None:
        self.sales_history.append(sale)
        if self.db and hasattr(self.db, "save_nft_sale"):
            self.db.save_nft_sale(sale)

    def _persist_all(self) -> None:
        for tid in list(self.tokens.keys()):
            self._persist_token(tid)
        for oid in list(self.offers.keys()):
            self._persist_offer(oid)
        for aid in list(self.auctions.keys()):
            self._persist_auction(aid)

    def _has_balance_backend(self) -> bool:
        return bool(
            self.db
            and hasattr(self.db, "get_balance")
            and (
                hasattr(self.db, "balance_delta_satoshi")
                or hasattr(self.db, "update_balance_satoshi")
                or hasattr(self.db, "update_balance")
            )
        )

    def _has_atomic_uow(self) -> bool:
        """True when store exposes ``atomic()`` (ADR 0016 NFT UoW path)."""
        return bool(self.db and callable(getattr(self.db, "atomic", None)))

    def _uow(self):
        """Storage unit-of-work for balance + NFT persist; null if unavailable."""
        if self._has_atomic_uow():
            return self.db.atomic()
        from contextlib import nullcontext

        return nullcontext()

    def _balance_sat(self, addr: str) -> int:
        from runtime.amount import to_satoshi

        if not self._has_balance_backend():
            return 0
        if hasattr(self.db, "get_balance_satoshi"):
            return int(self.db.get_balance_satoshi(addr))
        return int(to_satoshi(self.db.get_balance(addr)))

    def _balance(self, addr: str) -> float:
        from runtime.amount import from_satoshi_float

        return float(from_satoshi_float(self._balance_sat(addr)))

    def _debit(self, addr: str, amount: float) -> bool:
        from runtime.amount import apply_store_delta_satoshi, to_satoshi, try_debit_satoshi

        if not self._has_balance_backend():
            return False
        try:
            need = int(to_satoshi(amount))
            try_debit_satoshi(self._balance_sat(addr), debit_satoshi=need)
        except (TypeError, ValueError):
            return False
        if need <= 0:
            return False
        return bool(
            apply_store_delta_satoshi(
                self.db, addr, -need, allow_float_fallback=False
            )
        )

    def _credit(self, addr: str, amount: float) -> bool:
        from runtime.amount import apply_store_delta_satoshi, to_satoshi

        if not self._has_balance_backend():
            return False
        try:
            add = int(to_satoshi(amount))
        except (TypeError, ValueError):
            return False
        if add <= 0:
            return False
        return bool(
            apply_store_delta_satoshi(
                self.db, addr, add, allow_float_fallback=False
            )
        )

    def _debit_sat(self, addr: str, sat: int) -> None:
        from runtime.amount import apply_store_delta_satoshi

        need = int(sat)
        if need <= 0:
            raise RuntimeError("invalid debit")
        if int(self._balance_sat(addr)) < need:
            raise RuntimeError("insufficient balance or balance backend unavailable")
        if not apply_store_delta_satoshi(
            self.db, addr, -need, allow_float_fallback=False
        ):
            raise RuntimeError("nft_settle_failed: debit")

    def _credit_sat(self, addr: str, sat: int) -> None:
        from runtime.amount import apply_store_delta_satoshi

        add = int(sat)
        if add <= 0:
            return
        if not apply_store_delta_satoshi(
            self.db, addr, add, allow_float_fallback=False
        ):
            raise RuntimeError("nft_settle_failed: credit")

    def _credit_proceeds(self, seller: str, creator: str, price_sat: int) -> None:
        """Credit seller (+ royalty) from already-held buyer funds."""
        price_sat = int(price_sat)
        if price_sat <= 0:
            raise RuntimeError("invalid settle price")
        royalty_sat = (price_sat * int(self.ROYALTY * 10_000)) // 10_000
        seller_sat = price_sat - royalty_sat
        self._credit_sat(seller, seller_sat)
        if creator != seller and royalty_sat > 0:
            self._credit_sat(creator, royalty_sat)

    def _require_paid_uow(self) -> None:
        """Paid NFT paths need atomic store — refuse silent multi-step commit."""
        if self._has_balance_backend() and not self._has_atomic_uow():
            raise RuntimeError("nft_uow_required")

    def _settle_sale(
        self,
        buyer: str,
        seller: str,
        creator: str,
        price: float,
        *,
        price_satoshi: Optional[int] = None,
    ) -> None:
        """Settle ABS balances. Raise on any failure so ``atomic()`` rolls back.

        Never return False after a partial debit/credit — that would commit a
        half-applied UoW when callers ``return`` inside ``with db.atomic()``.
        """
        from runtime.amount import apply_store_delta_satoshi

        if not self._has_balance_backend():
            raise RuntimeError("balance backend unavailable")
        try:
            price_sat = int(
                resolve_price_satoshi(price=price, price_satoshi=price_satoshi)
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"invalid settle price: {exc}") from exc
        if price_sat <= 0:
            raise RuntimeError("invalid settle price")
        try:
            if int(self._balance_sat(buyer)) < price_sat:
                raise RuntimeError("insufficient balance or balance backend unavailable")
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "insufficient balance or balance backend unavailable"
            ) from exc
        royalty_sat = (price_sat * int(self.ROYALTY * 10_000)) // 10_000
        seller_sat = price_sat - royalty_sat
        if not apply_store_delta_satoshi(
            self.db, buyer, -price_sat, allow_float_fallback=False
        ):
            raise RuntimeError("nft_settle_failed: buyer debit")
        if not apply_store_delta_satoshi(
            self.db, seller, seller_sat, allow_float_fallback=False
        ):
            raise RuntimeError("nft_settle_failed: seller credit")
        if creator != seller and royalty_sat > 0:
            if not apply_store_delta_satoshi(
                self.db, creator, royalty_sat, allow_float_fallback=False
            ):
                raise RuntimeError("nft_settle_failed: royalty credit")

    def _load_genesis_collection(self):
        """Начальная коллекция Genesis."""
        genesis = [
            ("abs_genesis_crown",    "Absolute Crown",    "The ultimate crown of the Absolute Kingdom", "crown",    100.0),
            ("abs_quantum_guardian", "Quantum Guardian",  "Guardian of the quantum realm",              "guardian", 200.0),
            ("abs_genesis_block",    "Genesis Block",     "The very first block of Absolute chain",     "block",    500.0),
            ("abs_elemental_master", "Elemental Master",  "Master of all four elements",                "master",   300.0),
            ("abs_wisdom_relic",     "Wisdom Relic",      "Ancient artifact of wisdom",                 "relic",    150.0),
        ]
        for tid, name, desc, img, price in genesis:
            self._mint_internal(tid, name, desc, img, "0xgenesis", price)

    def _mint_internal(self, token_id, name, description, image_url, creator, price):
        if token_id not in self.tokens:
            sat = resolve_price_satoshi(price=price)
            from runtime.amount import from_satoshi_float

            self.tokens[token_id] = NFTToken(
                token_id=token_id, name=name, description=description,
                image_url=image_url, owner=creator, creator=creator,
                price=from_satoshi_float(sat), price_satoshi=sat,
                for_sale=(sat > 0),
            )

    # ── Создание NFT ─────────────────────────────────────────────────────────

    def mint(
        self,
        token_id: str,
        name: str,
        description: str,
        image_url: str,
        creator: str,
        price: float = 0.0,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Dict:
        """Create NFT. Charges MINT_FEE from creator (atomic UoW when available)."""
        with self.lock:
            if token_id in self.tokens:
                return {"success": False, "error": "token_id already exists"}
            try:
                list_sat = resolve_price_satoshi(
                    price=price, price_satoshi=price_satoshi
                )
            except ValueError as exc:
                return {"success": False, "error": str(exc)}
            from runtime.amount import from_satoshi_float

            price_abs = float(from_satoshi_float(list_sat))

            try:
                self._require_paid_uow()
                with self._uow():
                    if not self._debit(creator, self.MINT_FEE):
                        return {
                            "success": False,
                            "error": f"Need {self.MINT_FEE} ABS to mint",
                        }

                    self.tokens[token_id] = NFTToken(
                        token_id=token_id, name=name, description=description,
                        image_url=image_url, owner=creator, creator=creator,
                        price=price_abs, price_satoshi=list_sat,
                        for_sale=(list_sat > 0),
                    )
                    self._persist_token(token_id)
            except Exception as exc:
                self.tokens.pop(token_id, None)
                err = str(exc)
                if "nft_uow_required" in err:
                    return {"success": False, "error": err}
                return {"success": False, "error": f"nft_uow_failed: {exc}"}

            if self.bus:
                self.bus.emit("nft.minted", {"token_id": token_id, "creator": creator})

            return {
                "success": True,
                "token_id": token_id,
                "price": price_abs,
                "price_satoshi": list_sat,
                "uow_atomic": self._has_atomic_uow(),
            }

    # ── Торговля ─────────────────────────────────────────────────────────────

    def list_for_sale(
        self,
        token_id: str,
        owner: str,
        price: Optional[float] = None,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Dict:
        with self.lock:
            try:
                sat = resolve_price_satoshi(price=price, price_satoshi=price_satoshi)
            except ValueError as exc:
                return {"success": False, "error": str(exc)}
            if sat <= 0:
                return {"success": False, "error": "price must be > 0"}
            if token_id not in self.tokens:
                return {"success": False, "error": "not found"}
            t = self.tokens[token_id]
            if t.owner != owner:
                return {"success": False, "error": "not owner"}
            from runtime.amount import from_satoshi_float

            t.price_satoshi = sat
            t.price = float(from_satoshi_float(sat))
            t.for_sale = True
            self._persist_token(token_id)
            return {
                "success": True,
                "token_id": token_id,
                "price": t.price,
                "price_satoshi": sat,
            }

    def buy(self, token_id: str, buyer: str) -> Dict:
        """Buy NFT. ABS settles seller + creator royalty in one UoW."""
        with self.lock:
            if token_id not in self.tokens:
                return {"success": False, "error": "not found"}
            t = self.tokens[token_id]
            if not t.for_sale:
                return {"success": False, "error": "not for sale"}
            if buyer == t.owner:
                return {"success": False, "error": "already owner"}

            price_sat = int(t.price_satoshi or resolve_price_satoshi(price=t.price))
            price = t.price
            old_owner = t.owner
            old_for_sale = t.for_sale

            try:
                self._require_paid_uow()
                with self._uow():
                    self._settle_sale(
                        buyer, t.owner, t.creator, price, price_satoshi=price_sat
                    )
                    t.owner = buyer
                    t.for_sale = False
                    self._persist_token(token_id)
                    self._record_sale({
                        "token_id": token_id, "from": old_owner,
                        "to": buyer, "price": price, "price_satoshi": price_sat,
                        "type": "buy", "timestamp": int(time.time()),
                    })
            except Exception as exc:
                t.owner = old_owner
                t.for_sale = old_for_sale
                err = str(exc)
                if "insufficient balance" in err or "balance backend" in err:
                    return {
                        "success": False,
                        "error": "insufficient balance or balance backend unavailable",
                    }
                if "nft_uow_required" in err or "nft_settle_failed" in err:
                    return {"success": False, "error": err}
                return {"success": False, "error": f"nft_uow_failed: {exc}"}

            if self.bus:
                self.bus.emit("nft.sold", {
                    "token_id": token_id, "buyer": buyer,
                    "seller": old_owner, "price": price,
                })

            return {
                "success": True,
                "token_id": token_id,
                "buyer": buyer,
                "price": price,
                "price_satoshi": price_sat,
                "uow_atomic": self._has_atomic_uow(),
            }

    def transfer(self, token_id: str, from_addr: str, to_addr: str) -> Dict:
        with self.lock:
            if not to_addr:
                return {"success": False, "error": "recipient required"}
            if token_id not in self.tokens:
                return {"success": False, "error": "not found"}
            t = self.tokens[token_id]
            if t.owner != from_addr:
                return {"success": False, "error": "not owner"}
            t.owner = to_addr
            t.for_sale = False
            self._persist_token(token_id)
            return {"success": True}

    # ── Геттеры ──────────────────────────────────────────────────────────────

    def get_token(self, token_id: str) -> Optional[Dict]:
        with self.lock:
            t = self.tokens.get(token_id)
            return t.to_dict() if t else None

    def get_by_owner(self, owner: str) -> List[Dict]:
        with self.lock:
            return [t.to_dict() for t in self.tokens.values() if t.owner == owner]

    def get_on_sale(self) -> List[Dict]:
        with self.lock:
            return [t.to_dict() for t in self.tokens.values() if t.for_sale]

    def get_all(self) -> List[Dict]:
        with self.lock:
            return [t.to_dict() for t in self.tokens.values()]

    def get_stats(self) -> Dict:
        with self.lock:
            persisted = bool(self.db and hasattr(self.db, "get_nft_tokens"))
            balance_bound = self._has_balance_backend()
            return {
                "total_tokens": len(self.tokens),
                "on_sale": sum(1 for t in self.tokens.values() if t.for_sale),
                "unique_owners": len({t.owner for t in self.tokens.values()}),
                "total_value": sum(t.price for t in self.tokens.values() if t.for_sale),
                "mint_fee": self.MINT_FEE,
                "royalty_pct": self.ROYALTY * 100,
                "total_sales": len(self.sales_history),
                "total_offers": len(self.offers),
                "active_auctions": sum(1 for a in self.auctions.values() if a.get("status") == "active"),
                "persisted": persisted,
                "balance_backend": balance_bound,
                # Balance mutations + persist share db.atomic() when available (ADR 0016).
                "execution_bound": balance_bound,
                "uow_atomic": self._has_atomic_uow(),
                "offers_escrow": bool(balance_bound),
                "auction_escrow": bool(balance_bound),
                "escrow_note": (
                    "soft satoshi hold on offer/bid (persisted held_satoshi); "
                    "not L1 escrow contract"
                    if balance_bound
                    else "no balance backend"
                ),
                "on_chain_standard": False,
                "consensus_wired": False,
                # enabled follows balance backend — never paint live marketplace without it.
                "enabled": bool(balance_bound),
                "tier": "app-profile",
                "adr": "0016",
                "honesty": HONESTY,
            }

    # ── Offers ────────────────────────────────────────────────────────────────

    def make_offer(
        self,
        token_id: str,
        bidder: str,
        price: float = 0.0,
        hours: int = 24,
        *,
        price_satoshi: Optional[int] = None,
    ) -> Optional[str]:
        """Create a purchase offer; soft-escrow holds bidder funds until accept/cancel."""
        with self.lock:
            try:
                sat = resolve_price_satoshi(price=price, price_satoshi=price_satoshi)
            except ValueError:
                return None
            if sat <= 0:
                return None
            if token_id not in self.tokens:
                return None
            from runtime.amount import from_satoshi_float

            price_abs = float(from_satoshi_float(sat))
            if not self._has_balance_backend():
                return None
            offer_id = native.sha256_hex(
                f"{token_id}{bidder}{sat}{time.time()}".encode()
            )[:16]
            try:
                self._require_paid_uow()
                with self._uow():
                    self._debit_sat(bidder, sat)
                    self.offers[offer_id] = {
                        "offer_id": offer_id,
                        "token_id": token_id,
                        "bidder": bidder,
                        "price": price_abs,
                        "price_satoshi": sat,
                        "held_satoshi": sat,
                        "expires_at": int(time.time()) + hours * 3600,
                        "status": "pending",
                        "created_at": int(time.time()),
                    }
                    self._persist_offer(offer_id)
            except Exception:
                self.offers.pop(offer_id, None)
                return None
            return offer_id

    def cancel_offer(self, offer_id: str, bidder: str) -> Dict:
        """Cancel a pending offer (bidder only); refund soft escrow hold."""
        with self.lock:
            offer = self.offers.get(offer_id)
            if not offer:
                return {"success": False, "error": "Offer not found"}
            if offer.get("status") != "pending":
                return {"success": False, "error": "Offer not pending"}
            if str(offer.get("bidder") or "") != str(bidder or ""):
                return {"success": False, "error": "Not offer bidder"}
            held = int(offer.get("held_satoshi") or 0)
            old_status = offer["status"]
            try:
                if held > 0:
                    self._require_paid_uow()
                with self._uow():
                    if held > 0:
                        self._credit_sat(bidder, held)
                        offer["held_satoshi"] = 0
                    offer["status"] = "cancelled"
                    self._persist_offer(offer_id)
            except Exception as exc:
                offer["status"] = old_status
                if held > 0:
                    offer["held_satoshi"] = held
                return {"success": False, "error": f"nft_uow_failed: {exc}"}
            return {
                "success": True,
                "offer_id": offer_id,
                "status": "cancelled",
                "refunded_satoshi": held,
                "offers_escrow": True,
            }

    def accept_offer(self, offer_id: str, seller: str) -> Dict:
        """Accept an offer — settle from soft escrow hold in one UoW."""
        with self.lock:
            offer = self.offers.get(offer_id)
            if not offer or offer["status"] != "pending":
                return {"success": False, "error": "Offer not found or expired"}
            if int(time.time()) > int(offer.get("expires_at") or 0):
                held = int(offer.get("held_satoshi") or 0)
                try:
                    if held > 0:
                        self._require_paid_uow()
                        with self._uow():
                            self._credit_sat(offer["bidder"], held)
                            offer["held_satoshi"] = 0
                            offer["status"] = "expired"
                            self._persist_offer(offer_id)
                    else:
                        offer["status"] = "expired"
                        self._persist_offer(offer_id)
                except Exception as exc:
                    return {"success": False, "error": f"nft_uow_failed: {exc}"}
                return {"success": False, "error": "Offer expired"}
            token_id = offer["token_id"]
            t = self.tokens.get(token_id)
            if not t or t.owner != seller:
                return {"success": False, "error": "Not token owner"}
            price = offer["price"]
            try:
                price_sat = int(
                    offer.get("price_satoshi")
                    or resolve_price_satoshi(price=price)
                )
            except ValueError as exc:
                return {"success": False, "error": str(exc)}
            held = int(offer.get("held_satoshi") or 0)
            old_owner = t.owner
            old_for_sale = t.for_sale
            old_status = offer["status"]
            old_held = held
            try:
                self._require_paid_uow()
                with self._uow():
                    if held == price_sat and held > 0:
                        offer["held_satoshi"] = 0
                        self._credit_proceeds(seller, t.creator, price_sat)
                    else:
                        # Legacy path (no hold) — full settle debit.
                        self._settle_sale(
                            offer["bidder"],
                            seller,
                            t.creator,
                            price,
                            price_satoshi=price_sat,
                        )
                        offer["held_satoshi"] = 0
                    t.owner = offer["bidder"]
                    t.for_sale = False
                    self._persist_token(token_id)
                    offer["status"] = "accepted"
                    self._persist_offer(offer_id)
                    self._record_sale({
                        "token_id": token_id, "from": old_owner,
                        "to": offer["bidder"], "price": price,
                        "price_satoshi": price_sat,
                        "type": "offer", "timestamp": int(time.time()),
                    })
            except Exception as exc:
                t.owner = old_owner
                t.for_sale = old_for_sale
                offer["status"] = old_status
                offer["held_satoshi"] = old_held
                err = str(exc)
                if "insufficient balance" in err or "balance backend" in err:
                    return {
                        "success": False,
                        "error": "Bidder has insufficient balance or balance backend unavailable",
                    }
                if "nft_uow_required" in err or "nft_settle_failed" in err:
                    return {"success": False, "error": err}
                return {"success": False, "error": f"nft_uow_failed: {exc}"}
            if self.bus:
                self.bus.emit("nft.offer_accepted", {"offer_id": offer_id, "token_id": token_id})
            return {
                "success": True,
                "offer_id": offer_id,
                "token_id": token_id,
                "price": price,
                "price_satoshi": int(price_sat or 0),
                "uow_atomic": self._has_atomic_uow(),
            }

    def get_offers(self, token_id: str = None) -> List[Dict]:
        with self.lock:
            now = int(time.time())
            offers = [o for o in self.offers.values()
                      if (token_id is None or o["token_id"] == token_id)
                      and o["expires_at"] > now]
            return offers

    # ── Auctions ──────────────────────────────────────────────────────────────

    def create_auction(
        self,
        token_id: str,
        seller: str,
        start_price: float = 0.0,
        reserve_price: float = 0.0,
        hours: int = 24,
        auction_type: str = "english",
        *,
        start_price_satoshi: Optional[int] = None,
        reserve_price_satoshi: Optional[int] = None,
    ) -> Optional[str]:
        """Create an English auction for an NFT."""
        with self.lock:
            try:
                start_sat = resolve_price_satoshi(
                    price=start_price, price_satoshi=start_price_satoshi
                )
                reserve_sat = resolve_price_satoshi(
                    price=reserve_price, price_satoshi=reserve_price_satoshi
                )
            except ValueError:
                return None
            if start_sat <= 0 or reserve_sat < 0 or hours <= 0:
                return None
            t = self.tokens.get(token_id)
            if not t or t.owner != seller:
                return None
            from runtime.amount import from_satoshi_float

            start_abs = float(from_satoshi_float(start_sat))
            reserve_abs = float(from_satoshi_float(reserve_sat))
            auction_id = native.sha256_hex(
                f"{token_id}{seller}{start_sat}{time.time()}".encode()
            )[:16]
            self.auctions[auction_id] = {
                "auction_id": auction_id,
                "token_id": token_id,
                "seller": seller,
                "start_price": start_abs,
                "start_price_satoshi": start_sat,
                "reserve_price": reserve_abs,
                "reserve_price_satoshi": reserve_sat,
                "current_bid": start_abs,
                "current_bid_satoshi": start_sat,
                "current_bidder": None,
                "held_satoshi": 0,
                "held_bidder": None,
                "auction_type": auction_type,
                "ends_at": int(time.time()) + hours * 3600,
                "status": "active",
                "bids": [],
                "created_at": int(time.time()),
            }
            self._persist_auction(auction_id)
            return auction_id

    def place_bid(
        self,
        auction_id: str,
        bidder: str,
        amount: float = 0.0,
        *,
        amount_satoshi: Optional[int] = None,
    ) -> Dict:
        with self.lock:
            auction = self.auctions.get(auction_id)
            if not auction or auction["status"] != "active":
                return {"success": False, "error": "Auction not found or ended"}
            if int(time.time()) > auction["ends_at"]:
                auction["status"] = "ended"
                self._persist_auction(auction_id)
                return {"success": False, "error": "Auction has ended"}
            try:
                bid_sat = resolve_price_satoshi(
                    price=amount, price_satoshi=amount_satoshi
                )
            except ValueError as exc:
                return {"success": False, "error": str(exc)}
            current_sat = int(
                auction.get("current_bid_satoshi")
                or resolve_price_satoshi(price=auction.get("current_bid", 0))
            )
            if bid_sat <= current_sat:
                return {
                    "success": False,
                    "error": f"Bid must be > {auction['current_bid']}",
                }
            from runtime.amount import from_satoshi_float

            amount_abs = float(from_satoshi_float(bid_sat))
            if not self._has_balance_backend():
                return {
                    "success": False,
                    "error": "insufficient balance or balance backend unavailable",
                }
            prev_held = int(auction.get("held_satoshi") or 0)
            prev_bidder = auction.get("held_bidder")
            old_bid = auction.get("current_bid")
            old_bid_sat = auction.get("current_bid_satoshi")
            old_bidder = auction.get("current_bidder")
            old_bids = list(auction.get("bids") or [])
            try:
                self._require_paid_uow()
                with self._uow():
                    if prev_held > 0 and prev_bidder:
                        self._credit_sat(str(prev_bidder), prev_held)
                    self._debit_sat(bidder, bid_sat)
                    auction["bids"] = old_bids + [
                        {
                            "bidder": bidder,
                            "amount": amount_abs,
                            "amount_satoshi": bid_sat,
                            "ts": int(time.time()),
                        }
                    ]
                    auction["current_bid"] = amount_abs
                    auction["current_bid_satoshi"] = bid_sat
                    auction["current_bidder"] = bidder
                    auction["held_satoshi"] = bid_sat
                    auction["held_bidder"] = bidder
                    self._persist_auction(auction_id)
            except Exception as exc:
                auction["bids"] = old_bids
                auction["current_bid"] = old_bid
                auction["current_bid_satoshi"] = old_bid_sat
                auction["current_bidder"] = old_bidder
                auction["held_satoshi"] = prev_held
                auction["held_bidder"] = prev_bidder
                err = str(exc)
                if "insufficient balance" in err or "balance backend" in err:
                    return {
                        "success": False,
                        "error": "insufficient balance or balance backend unavailable",
                    }
                return {"success": False, "error": f"nft_uow_failed: {exc}"}
            return {
                "success": True,
                "auction_id": auction_id,
                "current_bid": amount_abs,
                "current_bid_satoshi": bid_sat,
                "bidder": bidder,
                "auction_escrow": True,
            }

    def cancel_auction(self, auction_id: str, seller: str) -> Dict:
        """Seller cancels active auction; refunds soft bid hold."""
        with self.lock:
            auction = self.auctions.get(auction_id)
            if not auction:
                return {"success": False, "error": "Auction not found"}
            if auction.get("status") != "active":
                return {"success": False, "error": "Auction not active"}
            if str(auction.get("seller") or "") != str(seller or ""):
                return {"success": False, "error": "Not auction seller"}
            held = int(auction.get("held_satoshi") or 0)
            held_bidder = auction.get("held_bidder")
            old_status = auction["status"]
            try:
                if held > 0:
                    self._require_paid_uow()
                with self._uow():
                    if held > 0 and held_bidder:
                        self._credit_sat(str(held_bidder), held)
                    auction["held_satoshi"] = 0
                    auction["held_bidder"] = None
                    auction["status"] = "cancelled"
                    self._persist_auction(auction_id)
            except Exception as exc:
                auction["status"] = old_status
                auction["held_satoshi"] = held
                auction["held_bidder"] = held_bidder
                return {"success": False, "error": f"nft_uow_failed: {exc}"}
            return {
                "success": True,
                "auction_id": auction_id,
                "status": "cancelled",
                "refunded_satoshi": held,
                "auction_escrow": True,
            }

    def finalize_auction(self, auction_id: str) -> Dict:
        """Finalize auction; settle balances + ownership in one UoW (no pre-settle finalize)."""
        with self.lock:
            auction = self.auctions.get(auction_id)
            if not auction:
                return {"success": False, "error": "Auction not found"}
            if auction["status"] != "active":
                return {"success": False, "error": "Auction already finalized"}
            # Refuse early finalize — auction window must elapse.
            if int(time.time()) < int(auction.get("ends_at") or 0):
                return {
                    "success": False,
                    "error": "Auction still active (ends_at not reached)",
                    "ends_at": int(auction.get("ends_at") or 0),
                }
            winner = auction["current_bidder"]
            price = auction["current_bid"]
            try:
                price_sat = int(
                    auction.get("current_bid_satoshi")
                    or resolve_price_satoshi(price=price)
                )
                reserve_sat = int(
                    auction.get("reserve_price_satoshi")
                    or resolve_price_satoshi(price=auction.get("reserve_price", 0))
                )
            except ValueError as exc:
                return {"success": False, "error": str(exc)}
            old_status = auction["status"]
            token_id = auction["token_id"]
            held = int(auction.get("held_satoshi") or 0)
            held_bidder = auction.get("held_bidder")
            t = self.tokens.get(token_id) if winner and price_sat >= reserve_sat else None
            old_owner = t.owner if t else None
            old_for_sale = t.for_sale if t else None

            try:
                if held > 0 or (winner and price_sat >= reserve_sat):
                    self._require_paid_uow()
                with self._uow():
                    if winner and price_sat >= reserve_sat:
                        if not t:
                            if held > 0 and held_bidder:
                                self._credit_sat(str(held_bidder), held)
                                auction["held_satoshi"] = 0
                                auction["held_bidder"] = None
                            raise RuntimeError("Auction token not found")
                        if (
                            held == price_sat
                            and held > 0
                            and str(held_bidder or "") == str(winner)
                        ):
                            auction["held_satoshi"] = 0
                            auction["held_bidder"] = None
                            self._credit_proceeds(old_owner, t.creator, price_sat)
                        else:
                            # Legacy path without hold — full settle.
                            self._settle_sale(
                                winner,
                                old_owner,
                                t.creator,
                                price,
                                price_satoshi=price_sat,
                            )
                            auction["held_satoshi"] = 0
                            auction["held_bidder"] = None
                        t.owner = winner
                        t.for_sale = False
                        self._persist_token(token_id)
                        self._record_sale({
                            "token_id": token_id,
                            "from": old_owner,
                            "to": winner,
                            "price": price,
                            "price_satoshi": price_sat,
                            "type": "auction",
                            "timestamp": int(time.time()),
                        })
                    elif held > 0 and held_bidder:
                        # Reserve not met — refund soft escrow.
                        self._credit_sat(str(held_bidder), held)
                        auction["held_satoshi"] = 0
                        auction["held_bidder"] = None
                    auction["status"] = "finalized"
                    self._persist_auction(auction_id)
            except Exception as exc:
                auction["status"] = old_status
                if t is not None and old_owner is not None:
                    t.owner = old_owner
                    t.for_sale = old_for_sale
                err = str(exc)
                if "insufficient balance" in err or "balance backend" in err:
                    return {
                        "success": False,
                        "error": "insufficient balance or balance backend unavailable",
                    }
                if "token not found" in err.lower():
                    auction["status"] = "settlement_failed"
                    try:
                        self._persist_auction(auction_id)
                    except Exception as persist_exc:
                        logger.warning(
                            "nft auction settlement_failed persist refused: %s",
                            persist_exc,
                        )
                    return {"success": False, "error": "Auction token not found"}
                return {"success": False, "error": f"nft_uow_failed: {exc}"}

            if winner and price_sat >= reserve_sat:
                return {
                    "success": True,
                    "auction_id": auction_id,
                    "winner": winner,
                    "price": price,
                    "price_satoshi": price_sat,
                    "uow_atomic": self._has_atomic_uow(),
                }
            return {
                "success": True,
                "auction_id": auction_id,
                "message": "Reserve price not met — no sale",
                "uow_atomic": self._has_atomic_uow(),
            }

    def get_auctions(self, active_only: bool = False) -> List[Dict]:
        with self.lock:
            auctions = list(self.auctions.values())
            if active_only:
                auctions = [a for a in auctions if a["status"] == "active"]
            return auctions

    def get_sales_history(self, token_id: str = None, limit: int = 50) -> List[Dict]:
        with self.lock:
            sales = self.sales_history
            if token_id:
                sales = [s for s in sales if s["token_id"] == token_id]
            return sales[-limit:][::-1]
