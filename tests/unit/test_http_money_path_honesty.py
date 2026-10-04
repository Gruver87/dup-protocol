"""HTTP money-path honesty: no invent-0, single satoshi authority, legacy 410."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_l1_register_does_not_invent_zero_on_bad_amount() -> None:
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/bridge/oracle/l1-register"')[1].split("elif path")[0]
    assert "has_money" in chunk
    assert "amount, amount_sat = 0.0, 0" not in chunk
    assert 'self._error(400, str(exc))' in chunk


def test_state_balance_ims_missing_uses_satoshi_authority() -> None:
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path.startswith("/state/balance/")')[1].split("elif path")[0]
    assert "from_satoshi_float" in chunk
    assert "get_balance_satoshi" in chunk
    assert 'bal = bc.get_balance(addr)' not in chunk


def test_nft_list_legacy_tombstone() -> None:
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/nft/list-legacy"')[1].split("elif path")[0]
    assert "410" in chunk
    assert "price_satoshi" in chunk
    assert "create_listing" not in chunk


def test_call_drop_satoshi_does_not_soft_strip() -> None:
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split("def _call_drop_satoshi_kwargs")[1].split("\ndef ")[0]
    assert "endswith" not in chunk
    assert "slim" not in chunk


def test_query_facade_uses_canonical_balance() -> None:
    src = (ROOT / "api" / "query_facade.py").read_text(encoding="utf-8")
    assert "canonical_balance_satoshi(store, address)" in src


def test_rocks_live_meta_warns_on_corrupt() -> None:
    src = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert "corrupt live_state_root_height meta" in src
