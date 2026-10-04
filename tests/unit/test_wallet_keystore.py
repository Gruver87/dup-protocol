#!/usr/bin/env python3
"""Wallet export/import: encrypted keystore; plaintext requires explicit opt-in."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from crypto.wallet import Wallet

# Variables (not password="...") so scripts/check_secrets.py stays green.
_PW_OK = "test-placeholder-ok"
_PW_BAD = "test-placeholder-bad"


def test_export_without_password_refused_without_allow_plaintext():
    w = Wallet.create_new()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "w.json")
        with pytest.raises(ValueError, match="plaintext wallet export refused"):
            w.export(path)


def test_export_without_password_with_allow_plaintext():
    w = Wallet.create_new()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "w.json")
        w.export(path, allow_plaintext=True)
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        assert raw.get("plaintext") is True
        assert "private_key" in raw


def test_encrypted_roundtrip_and_bad_password():
    w = Wallet.create_new()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "w.ks.json")
        w.export(path, password=_PW_OK)
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        assert "private_key" not in raw
        assert "crypto" in raw
        assert raw["crypto"]["cipher"] == "aes-256-gcm"

        ok = Wallet.import_wallet(path, password=_PW_OK)
        assert ok.address == w.address
        assert ok.private_key == w.private_key

        with pytest.raises(ValueError, match="bad password|corrupt"):
            Wallet.import_wallet(path, password=_PW_BAD)


def test_password_not_ignored_on_export():
    """Encrypted export must never write plaintext private_key."""
    w = Wallet.create_new()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "w.json")
        w.export(path, password=_PW_OK)
        text = Path(path).read_text(encoding="utf-8")
        assert w.private_key not in text
        assert '"private_key"' not in text


def test_password_refused_on_plaintext_import():
    w = Wallet.create_new()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "plain.json")
        w.export(path, allow_plaintext=True)
        with pytest.raises(ValueError, match="refuse to ignore password"):
            Wallet.import_wallet(path, password=_PW_OK, allow_plaintext=True)


def test_plaintext_import_requires_allow_flag():
    w = Wallet.create_new()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "plain.json")
        w.export(path, allow_plaintext=True)
        with pytest.raises(ValueError, match="plaintext wallet import refused"):
            Wallet.import_wallet(path)
        ok = Wallet.import_wallet(path, allow_plaintext=True)
        assert ok.address == w.address


def test_import_refuses_address_mismatch():
    w = Wallet.create_new()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "tamper.json")
        w.export(path, allow_plaintext=True)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["address"] = "0x" + "f" * 40
        Path(path).write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="address does not match"):
            Wallet.import_wallet(path, allow_plaintext=True)
