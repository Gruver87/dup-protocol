#!/usr/bin/env python3
"""soak_guard refuses live mesh hammering while soak monitor is ALIVE."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load():
    path = ROOT / "scripts" / "soak_guard.py"
    spec = importlib.util.spec_from_file_location("soak_guard", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_refuse_when_pids_present(monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "list_soak_monitor_pids", lambda: [12345])
    monkeypatch.setattr(mod, "soak_active_marker", lambda: {"log_file": "logs/x.log"})
    with pytest.raises(SystemExit) as ei:
        mod.refuse_live_mesh_if_soak_alive(force=False, context="unit")
    assert ei.value.code == 2


def test_force_bypasses(monkeypatch, capsys):
    mod = _load()
    monkeypatch.setattr(mod, "list_soak_monitor_pids", lambda: [12345])
    mod.refuse_live_mesh_if_soak_alive(force=True, context="unit")
    out = capsys.readouterr().out
    assert "bypassed" in out


def test_no_pids_ok(monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "list_soak_monitor_pids", lambda: [])
    mod.refuse_live_mesh_if_soak_alive(force=False)
