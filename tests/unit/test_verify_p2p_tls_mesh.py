#!/usr/bin/env python3
"""P2P TLS mesh verify and preflight tests."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_p2p_tls_scripts_exist():
    assert (ROOT / "scripts" / "verify_p2p_tls_mesh.py").is_file()
    assert (ROOT / "scripts" / "p2p_tls_preflight.py").is_file()
    assert (ROOT / "scripts" / "p2p_tls_evidence_suite.ps1").is_file()
    assert (ROOT / "scripts" / "docker_prod_3node_p2ptls.ps1").is_file()


def test_static_tls_material_requires_node_dirs(tmp_path):
    mod = _load("verify_p2p_tls_mesh", "scripts/verify_p2p_tls_mesh.py")
    empty_root = tmp_path / "empty_tls_mesh"
    with patch.object(mod, "TLS_MESH_ROOT", empty_root):
        errors, _warnings, meta = mod.check_static_tls_material()
    assert meta["nodes"]
    assert any("missing TLS file" in e for e in errors)


def test_live_tls_verify_fails_when_not_ready():
    mod = _load("verify_p2p_tls_mesh", "scripts/verify_p2p_tls_mesh.py")
    sec = {"tls": {"enabled": True, "ready": False, "errors": ["cert missing"]}}

    def fake_api(url, timeout=10.0):
        if url.rstrip("/").endswith("/status"):
            # TCP+TLS alternate: libp2p off so TLS path still applies.
            return {"libp2p": {"feature_libp2p": False, "active": False}}
        if "/p2p/security" in url:
            return sec
        if "/health/ready" in url:
            return {"status": "ready"}
        return {}

    with patch.object(mod, "_api", side_effect=fake_api), patch.object(mod, "_probe_ready", return_value=True), patch.object(
        mod, "check_static_tls_material", return_value=([], [], {})
    ):
        errors, _warnings, meta = mod.verify_p2p_tls_mesh(check_static=False, require_tls=True)
    assert meta["reachable"] == 3
    assert any("P2P TLS not ready" in e for e in errors)


def test_live_libp2p_mesh_is_not_applicable_for_tls_verify():
    """ADR 0020 default mesh: Noise active → TLS verify N/A; ready stays false."""
    mod = _load("verify_p2p_tls_mesh", "scripts/verify_p2p_tls_mesh.py")

    def fake_api(url, timeout=10.0):
        if url.rstrip("/").endswith("/status"):
            return {
                "libp2p": {
                    "feature_libp2p": True,
                    "active": True,
                    "honesty": "ADR0020_experimental_libp2p_industrial_mesh",
                }
            }
        if "/health/ready" in url:
            return {"status": "ready"}
        return {}

    with patch.object(mod, "_api", side_effect=fake_api), patch.object(
        mod, "_probe_ready", return_value=True
    ):
        errors, warnings, meta = mod.verify_p2p_tls_mesh(check_static=False, require_tls=True)
    assert errors == []
    assert meta.get("not_applicable") is True
    assert meta.get("ready") is False
    assert meta.get("tls_ready") is False
    assert meta.get("transport_mode") == "adr0020_libp2p_noise"
    assert any("ADR 0020" in w for w in warnings)


def test_libp2p_active_requires_explicit_feature_flag():
    """Missing feature_libp2p must not default to True (fail-closed)."""
    mod = _load("verify_p2p_tls_mesh", "scripts/verify_p2p_tls_mesh.py")
    assert mod._libp2p_active({"libp2p": {"active": True}}) is False
    assert mod._libp2p_active({"libp2p": {"active": True, "feature_libp2p": True}}) is True
    assert mod._libp2p_active({"libp2p": {"active": True, "feature_libp2p": False}}) is False


def test_p2p_tls_preflight_static():
    mod = _load("p2p_tls_preflight", "scripts/p2p_tls_preflight.py")
    errors, _warnings, meta = mod.run_p2p_tls_preflight(live=False)
    assert "deploy_steps" in meta
    assert meta["live"] is False
    assert isinstance(errors, list)
