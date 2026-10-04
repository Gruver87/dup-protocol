"""CryptoWill + feature save_* + validator manifest satoshi authority."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.amount import to_satoshi


def test_crypto_will_create_prefer_amount_satoshi():
    from features.crypto_will import CryptoWillManager
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "will.db"))
    db.initialize()
    owner = "0x" + "a" * 40
    heir = "0x" + "b" * 40
    db.set_balance(owner, 100.0)
    cw = CryptoWillManager(db=db)
    amt_sat = int(to_satoshi(25.0))
    wid = cw.create_will(
        owner, heir, 25.0, {}, execution_delay=86400, amount_satoshi=amt_sat
    )
    assert wid
    will = cw.wills[wid]
    assert will.amount_satoshi == amt_sat
    assert db.get_balance_satoshi(owner) == int(to_satoshi(100.0)) - amt_sat
    rows = db.get_crypto_wills()
    assert rows[0]["amount_satoshi"] == amt_sat


def test_save_plasma_deposit_prefers_inbound_satoshi():
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "pl.db"))
    db.initialize()
    sat = int(to_satoshi(12.5))
    db.save_plasma_deposit(
        {
            "id": "d1",
            "from": "0xfrom",
            "amount": 12.5,
            "amount_satoshi": sat,
            "main_tx_hash": "0x1",
            "created_at": 1,
            "status": "confirmed",
        }
    )
    deps = db.get_plasma_deposits()
    assert deps[0]["amount_satoshi"] == sat


def test_save_plasma_deposit_mismatch_refuses():
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "pl2.db"))
    db.initialize()
    try:
        db.save_plasma_deposit(
            {
                "id": "d2",
                "from": "0xfrom",
                "amount": 12.5,
                "amount_satoshi": int(to_satoshi(13.0)),
                "main_tx_hash": "0x1",
                "created_at": 1,
                "status": "confirmed",
            }
        )
        assert False, "expected amount_satoshi_mismatch"
    except ValueError as exc:
        assert "amount_satoshi_mismatch" in str(exc)


def test_apply_public_manifest_registry_uses_satoshi():
    from runtime.amount import from_satoshi_float
    from runtime.validator_loader import apply_public_manifest

    class _Consensus:
        def __init__(self):
            self.validators = {}

        def add_validator(self, address, stake, *, stake_satoshi=None):
            self.validators[address] = stake

    class _DB:
        def __init__(self):
            self._validators = []
            self.saved = []

        def get_validators(self, active_only=True):
            return list(self._validators)

        def save_validator(self, address, stake, *, stake_satoshi=None):
            self.saved.append((address, stake, stake_satoshi))
            self._validators.append(
                {
                    "address": address,
                    "stake": stake,
                    "stake_satoshi": stake_satoshi,
                    "active": True,
                }
            )

    class _Registry:
        def __init__(self):
            self.registered = []

        def register_validator(self, address, stake):
            self.registered.append((address, stake))

    addr = "0x" + "c" * 40
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "validators.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": 1,
                    "validators": [
                        {
                            "index": 1,
                            "address": addr,
                            "stake": 99.0,
                            "stake_satoshi": 5_000_000_000,
                        }
                    ],
                },
                f,
            )
        node = type(
            "Node",
            (),
            {
                "config": type(
                    "Cfg", (), {"is_production": False, "min_stake": 1000}
                )(),
                "consensus": _Consensus(),
                "db": _DB(),
                "validator_registry": _Registry(),
            },
        )()
        assert apply_public_manifest(node, path) == 1
        expected_abs = float(from_satoshi_float(5_000_000_000))
        assert node.consensus.validators[addr] == expected_abs
        assert node.db.saved[-1] == (addr, expected_abs, 5_000_000_000)
        assert node.validator_registry.registered[-1] == (addr, 5_000_000_000)


def test_source_needles_will_http_and_resolve_abs_sat():
    http_src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "amount_satoshi=int(amount_sat)" in http_src
    assert "create_will(" in http_src
    db_src = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    assert "def _resolve_abs_sat" in db_src
    will_src = (ROOT / "features" / "crypto_will.py").read_text(encoding="utf-8")
    assert "amount_satoshi: int | None = None" in will_src
