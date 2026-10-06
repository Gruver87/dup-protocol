"""Cached genesis ceremony status for GET /status (no per-request re-verify)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import api.http as http_mod


def test_genesis_ceremony_status_missing_manifest():
    cfg = MagicMock()
    cfg.validators_manifest_path = ""
    out = http_mod._genesis_ceremony_status(cfg)
    assert out["ready"] is False
    assert out["mainnet_addresses_ready"] is False


def test_genesis_ceremony_status_caches_by_mtime(tmp_path, monkeypatch):
    http_mod._CEREMONY_STATUS_CACHE.clear()
    manifest = tmp_path / "validators.manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    cfg = MagicMock()
    cfg.validators_manifest_path = str(manifest)

    calls = {"n": 0}

    def fake_verify(cfg_arg, strict_addresses=False):
        calls["n"] += 1
        return [], {
            "mainnet_addresses_ready": True,
            "ceremony_hash": "abc",
            "validator_set_hash": "def",
            "validators_count": 3,
        }

    monkeypatch.setattr(
        "runtime.genesis_ceremony.verify_live_manifest",
        fake_verify,
        raising=False,
    )
    # Patch the import path used inside the helper.
    import runtime.genesis_ceremony as gc

    monkeypatch.setattr(gc, "verify_live_manifest", fake_verify)

    a = http_mod._genesis_ceremony_status(cfg)
    b = http_mod._genesis_ceremony_status(cfg)
    assert a["ready"] is True
    assert a["ceremony_hash"] == "abc"
    assert b["ready"] is True
    assert calls["n"] == 1

    # Touch mtime → cache miss.
    import time

    time.sleep(0.02)
    manifest.write_text("{}\n", encoding="utf-8")
    c = http_mod._genesis_ceremony_status(cfg)
    assert c["ready"] is True
    assert calls["n"] == 2
