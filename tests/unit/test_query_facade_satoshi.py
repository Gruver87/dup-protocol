#!/usr/bin/env python3
"""Phase C1: QueryFacade balance prefers satoshi."""

from __future__ import annotations

from types import SimpleNamespace

from api.query_facade import QueryFacade
from runtime.amount import from_satoshi_float, to_satoshi


def test_query_facade_get_balance_satoshi_prefers_chain_satoshi():
    sat = int(to_satoshi(12.5))
    bc = SimpleNamespace(get_balance_satoshi=lambda _a: sat)
    q = QueryFacade(blockchain=bc, config=SimpleNamespace())
    assert q.get_balance_satoshi("0xabc") == sat
    assert q.get_balance("0xabc") == float(from_satoshi_float(sat))


def test_query_facade_float_fallback_via_get_balance():
    bc = SimpleNamespace(get_balance=lambda _a: 3.0)
    # no get_balance_satoshi
    q = QueryFacade(blockchain=bc, config=SimpleNamespace())
    assert q.get_balance_satoshi("0xabc") == int(to_satoshi(3.0))
