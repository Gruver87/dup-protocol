"""Address activity exposes integer balance_satoshi authority."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_rocks_address_activity_has_balance_satoshi_needle():
    src = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    chunk = src.split("def get_address_activity")[1].split("\n    def ")[0]
    assert "balance_satoshi" in chunk
    assert "account_satoshi" in chunk
    assert "account_balance_abs" in chunk


def test_address_http_fallback_has_balance_satoshi():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path.startswith("/address/")')[1].split("elif path ==")[0]
    assert "balance_satoshi" in chunk
    assert "get_balance_satoshi" in chunk
