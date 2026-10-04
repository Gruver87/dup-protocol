"""EVM money paths refuse float update_balance / set_balance fallback."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution import evm_adapter as evm_mod
from execution.evm_adapter import EVMAdapter
from runtime.amount import WEI_PER_SATOSHI


class _FloatOnlyStore:
    """Incomplete store: balances readable as satoshi, but no satoshi write API."""

    def __init__(self) -> None:
        self._sat = {
            "0xfrom": 5_000_000,
            "0xto": 0,
            "0xcontract": 1_000_000,
        }

    def _key(self, addr: str) -> str:
        return str(addr or "").lower()

    def get_balance_satoshi(self, addr: str) -> int:
        return int(self._sat.get(self._key(addr), 0))

    def get_balance(self, addr: str) -> float:
        return self.get_balance_satoshi(addr) / 1_000_000.0

    def update_balance(self, addr: str, delta: float) -> float:
        raise AssertionError("float update_balance must not be used")

    def set_balance(self, addr: str, balance: float) -> None:
        raise AssertionError("float set_balance must not be used")

    def get_account(self, addr: str) -> dict:
        return {
            "balance_satoshi": self.get_balance_satoshi(addr),
            "balance": self.get_balance(addr),
            "nonce": 0,
            "code": "0x60",
            "storage": "{}",
        }

    def save_account(self, address: str, **kwargs) -> None:
        return None

    def get_chain_tip(self) -> int:
        return 0


def _adapter() -> EVMAdapter:
    cfg = SimpleNamespace(
        require_native_crypto=False,
        deployment_mode="dev",
        evm_create2_eip1014=False,
    )
    return EVMAdapter(db=_FloatOnlyStore(), config=cfg)


def test_transfer_sat_refuses_float_store():
    ad = _adapter()
    err = ad._transfer_sat_fail_closed("0xfrom", "0xto", 1000)
    assert err == "satoshi_store_required"


def test_writeback_transfer_refuses_float_store(monkeypatch):
    ad = _adapter()

    def _boom(*_a, **_k):
        raise RuntimeError("force_python_fallback")

    monkeypatch.setattr(evm_mod.native, "evm_apply_writeback_ops", _boom, raising=False)
    with pytest.raises(RuntimeError, match="satoshi_store_required_writeback"):
        ad._apply_nested_writeback_ops_now(
            [
                {
                    "op": "transfer_value",
                    "from": "0xfrom",
                    "to": "0xto",
                    "value_wei": 1000 * WEI_PER_SATOSHI,
                }
            ]
        )


def test_selfdestruct_refuses_float_store():
    ad = _adapter()
    with pytest.raises(RuntimeError, match="satoshi_store_required_selfdestruct"):
        ad._selfdestruct_contract("0xcontract", "0xto")


def test_evm_adapter_source_requires_allow_float_fallback_false():
    src = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
    assert "allow_float_fallback=False" in src
    assert "from_satoshi_float(have - need)" not in src
    assert "wei_to_abs" not in src
