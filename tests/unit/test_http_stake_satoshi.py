#!/usr/bin/env python3
"""HTTP validator register prefers stake_satoshi (P2P parity)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.http import _http_stake_abs


def test_stake_satoshi_preferred() -> None:
    cfg = SimpleNamespace(deployment_mode="dev")
    abs_v, sat = _http_stake_abs({"stake_satoshi": 32_000_000}, cfg)
    assert sat == 32_000_000
    assert abs_v == pytest.approx(32.0)


def test_prod_refuses_float_only_stake() -> None:
    cfg = SimpleNamespace(deployment_mode="prod")
    with pytest.raises(ValueError, match="stake_satoshi required"):
        _http_stake_abs({"stake": 32.0}, cfg)


def test_dev_allows_float_stake() -> None:
    cfg = SimpleNamespace(deployment_mode="dev")
    abs_v, sat = _http_stake_abs({"stake": 32.0}, cfg)
    assert abs_v == pytest.approx(32.0)
    assert sat == 32_000_000
