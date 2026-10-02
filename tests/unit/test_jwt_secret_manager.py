#!/usr/bin/env python3
"""JWT secret resolves via ADR 0015 SecretManagerPort."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from middleware.jwt_auth import _resolve_jwt_secret


def test_jwt_secret_via_env_compat(monkeypatch) -> None:
    monkeypatch.setenv("SECRET_BACKEND", "env")
    monkeypatch.setenv("JWT_SECRET", "a" * 40)
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    assert _resolve_jwt_secret() == "a" * 40


def test_jwt_secret_empty_in_prod_without_env(monkeypatch) -> None:
    monkeypatch.setenv("SECRET_BACKEND", "env")
    monkeypatch.setenv("DEPLOYMENT_MODE", "prod")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    assert _resolve_jwt_secret() == ""
