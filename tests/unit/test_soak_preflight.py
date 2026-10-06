#!/usr/bin/env python3
"""Soak preflight wiring tests."""

import importlib.util
import os
import sys
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)


def _load(name: str, rel: str):
    path = os.path.join(ROOT, rel)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_soak_preflight_module_exists():
    assert os.path.isfile(os.path.join(ROOT, "scripts", "soak_preflight.py"))
    assert os.path.isfile(os.path.join(ROOT, "scripts", "prepare_48h_soak.ps1"))
    assert os.path.isfile(os.path.join(ROOT, "scripts", "start_soak_prod_mesh_48h.ps1"))
    prep = open(
        os.path.join(ROOT, "scripts", "prepare_48h_soak.ps1"), encoding="utf-8"
    ).read()
    assert "--require-wire-probe" in prep
    assert "--require-libp2p" in prep
    assert "check_mesh_catchup" in prep
    assert "soak_48h_prep.json" in prep
    assert "stop_soak_monitors" in prep
    assert r"\(unhealthy\)" in prep
    assert "COMMITTED_STATE_ROOT_OK" in prep
    stop = open(
        os.path.join(ROOT, "scripts", "stop_soak_monitors.ps1"), encoding="utf-8"
    ).read()
    assert "mempool_validation_sidecar" in stop
    assert "health_watch" in stop
    assert "selfPid" in stop or "ProcessId=$selfPid" in stop


def test_soak_preflight_detects_unreachable_mesh(monkeypatch):
    mod = _load("soak_preflight", "scripts/soak_preflight.py")

    def _fail_urlopen(*_args, **_kwargs):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _fail_urlopen)
    errors, _warnings, meta = mod.run_soak_preflight(hours=48)
    assert errors
    assert meta.get("ready") is False
    assert "start_command" in meta
    assert meta.get("hours_planned") == 48


def test_soak_preflight_accepts_require_wire_probe(monkeypatch):
    mod = _load("soak_preflight", "scripts/soak_preflight.py")

    def _fail_urlopen(*_args, **_kwargs):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _fail_urlopen)
    errors, _warnings, meta = mod.run_soak_preflight(
        hours=48, require_p2p_tls=True, require_wire_probe=True, require_libp2p=True
    )
    assert errors
    assert meta.get("require_wire_probe") is True
    assert meta.get("require_libp2p") is True
    assert "start_soak_prod_mesh_48h" in str(meta.get("start_command") or "")


def test_soak_preflight_require_wire_uses_full_harness():
    path = os.path.join(ROOT, "scripts", "soak_preflight.py")
    text = open(path, encoding="utf-8").read()
    assert "quick=False" in text
    assert "peer_timeout=8.0" in text
    assert "attempts = 3 if require_wire_probe else 1" in text
    assert "--require-wire-probe" in text
    assert "--require-libp2p" in text


def test_monolith_gate_accepts_soak_preflight_flag():
    mod = _load("monolith_gate", "scripts/monolith_gate.py")
    import inspect

    sig = inspect.signature(mod.run_monolith_gate)
    assert "soak_preflight" in sig.parameters


def test_soak_preflight_write_report(tmp_path, monkeypatch):
    mod = _load("soak_preflight", "scripts/soak_preflight.py")
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    path = mod.write_report([], ["warn"], {"ready": True})
    assert path == tmp_path / "logs" / "soak_preflight.json"
    assert path.is_file()
    payload = path.read_text(encoding="utf-8")
    assert "warn" in payload
