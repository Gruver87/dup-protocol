"""Wallet/burn GET responses expose integer balance_satoshi authority."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_wallet_burn_balance_satoshi_needles():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    for path, needle in (
        ('"/wallet/status"', "balance_satoshi"),
        ('"/burn-stats"', "burn_address_balance_satoshi"),
        ('"/wallet/balance"', "balance_satoshi"),
    ):
        chunk = src.split(f"path == {path}" if path != '"/wallet/balance"' else 'path.startswith("/wallet/balance")')[1]
        chunk = chunk.split("elif path")[0]
        assert needle in chunk, path
        assert "get_balance_satoshi" in chunk, path
