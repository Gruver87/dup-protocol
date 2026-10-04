"""Exp mid-soak honesty: no invent gas/fee/amount on send/P2P/sign/L2."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from runtime.amount import to_satoshi

ROOT = Path(__file__).resolve().parents[2]


def test_http_amount_abs_prod_refuses_float_only():
    from api.http import _http_amount_abs

    cfg = MagicMock()
    cfg.deployment_mode = "prod"
    with pytest.raises(ValueError, match="amount_satoshi required"):
        _http_amount_abs({"amount": 1.0}, cfg)

    abs_v, sat = _http_amount_abs({"amount_satoshi": 1_000_000}, cfg)
    assert sat == 1_000_000
    assert abs_v == 1.0


def test_http_amount_abs_dev_allows_float():
    from api.http import _http_amount_abs

    cfg = MagicMock()
    cfg.deployment_mode = "dev"
    abs_v, sat = _http_amount_abs({"amount": 2.5}, cfg)
    assert sat == int(to_satoshi(2.5))
    assert abs_v == 2.5


def _dev_cfg(**kwargs):
    cfg = MagicMock()
    cfg.is_production = False
    cfg.deployment_mode = "dev"
    cfg.chain_id = 1
    cfg.burn_rate = 0
    cfg.require_signatures = False
    cfg.node_id = "t"
    cfg.base_gas_price = 21000
    for key, value in kwargs.items():
        setattr(cfg, key, value)
    return cfg


def test_send_tx_requires_gas_and_refuses_zero_gas_price():
    from api.http import _handle_send_tx_obj

    cfg = _dev_cfg(gas_price_wei=0)
    bc = MagicMock()
    bc.validate_transaction.return_value = {"valid": True}
    bc.db = MagicMock()
    mp = MagicMock()

    with pytest.raises(ValueError, match="gas or gas_limit required"):
        _handle_send_tx_obj(
            {"from": "0x" + "a" * 40, "to": "0x" + "b" * 40, "value": 1.0, "nonce": 0},
            bc,
            mp,
            cfg,
        )

    with pytest.raises(ValueError, match="fee_gas_price_unset"):
        _handle_send_tx_obj(
            {
                "from": "0x" + "a" * 40,
                "to": "0x" + "b" * 40,
                "value": 1.0,
                "nonce": 0,
                "gas": 21000,
            },
            bc,
            mp,
            cfg,
        )


def test_auto_sign_requires_explicit_gas():
    from api.http import _handle_send_tx_with_wallet

    cfg = _dev_cfg()
    wallet = MagicMock()
    wallet.address = "0x" + "a" * 40
    bc = MagicMock()
    bc.db.get_nonce.return_value = 0
    mp = MagicMock()

    with pytest.raises(ValueError, match="gas or gas_limit required for auto_sign"):
        _handle_send_tx_with_wallet(
            {"auto_sign": True, "to": "0x" + "b" * 40, "value": 1},
            bc,
            mp,
            cfg,
            wallet=wallet,
        )


def test_wallet_canonical_always_hashes_gas_21000():
    from crypto.wallet import Wallet

    payload = Wallet._canonical_tx_for_hash(
        {
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "value": 1,
            "nonce": 0,
            "chain_id": 1,
            "gas_limit": 21000,
        }
    )
    assert payload["gas_limit"] == 21000


def test_p2p_no_invent_gas_21000_needle():
    src = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    assert "p2p_mempool_require_explicit_gas" in src
    assert "gas_missing" in src
    assert "int(data.get(\"gas\", 0) or 0) or 21_000" not in src


def test_mempool_wire_no_invent_gas():
    src = (ROOT / "blockchain" / "mempool_wire.py").read_text(encoding="utf-8")
    assert "or 21_000" not in src


def test_tx_sign_uses_http_amount_abs():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/tx/sign"')[1].split("elif path")[0]
    assert "_http_amount_abs" in chunk
    assert '_http_abs(body.get("amount", 0))' not in chunk


def test_l2_rest_uses_http_amount_abs():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    for marker in (
        'path == "/lightning/open"',
        'path == "/lightning/pay"',
        'path == "/will/create"',
        'path == "/plasma/deposit"',
        'path == "/plasma/tx"',
    ):
        chunk = src.split(marker)[1].split("elif path")[0]
        assert "_http_amount_abs" in chunk, marker
