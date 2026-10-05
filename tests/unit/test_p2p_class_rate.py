#!/usr/bin/env python3
"""Per-peer P2P class quotas: attest / tx / block announce cannot share one window.

Ported from DUP experimental STRICT hardening (no Long-Range / ws_checkpoint class).
Unit scope only — mesh probe / industrial gate are separate acceptance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.p2p_node import (
    MSG_ATTESTATION,
    MSG_NEW_BLOCK,
    MSG_NEW_TX,
    MSG_PING,
    P2PNode,
    RATE_LIMIT_EXEMPT_TYPES,
)
from runtime.config import Config


def _node(**caps) -> P2PNode:
    cfg = Config()
    cfg.require_native_crypto = False
    cfg.deployment_mode = "dev"
    cfg.p2p_max_messages_per_sec = 500
    cfg.p2p_exempt_messages_per_sec = 2000
    cfg.p2p_attest_messages_per_sec = 2
    cfg.p2p_tx_messages_per_sec = 2
    cfg.p2p_block_announce_messages_per_sec = 2
    for key, val in caps.items():
        setattr(cfg, key, val)
    return P2PNode(cfg, None, None)


def test_attestation_class_does_not_starve_tx():
    node = _node()
    assert node._rate_limit_ok("p1", MSG_ATTESTATION) is True
    assert node._rate_limit_ok("p1", MSG_ATTESTATION) is True
    assert node._rate_limit_ok("p1", MSG_ATTESTATION) is False
    assert node._rate_limit_ok("p1", MSG_NEW_TX) is True
    assert node._rate_limit_ok("p1", MSG_NEW_TX) is True
    assert node._rate_limit_ok("p1", MSG_NEW_TX) is False


def test_tx_class_does_not_starve_attestation():
    node = _node()
    assert node._rate_limit_ok("p1", MSG_NEW_TX) is True
    assert node._rate_limit_ok("p1", MSG_NEW_TX) is True
    assert node._rate_limit_ok("p1", MSG_NEW_TX) is False
    assert node._rate_limit_ok("p1", MSG_ATTESTATION) is True


def test_block_announce_class_on_exempt_type():
    node = _node()
    assert MSG_NEW_BLOCK in RATE_LIMIT_EXEMPT_TYPES
    assert node._rate_limit_ok("p1", MSG_NEW_BLOCK) is True
    assert node._rate_limit_ok("p1", MSG_NEW_BLOCK) is True
    assert node._rate_limit_ok("p1", MSG_NEW_BLOCK) is False
    assert node._rate_limit_ok("p1", MSG_PING) is True


def test_class_cap_zero_disables_quota():
    node = _node(
        p2p_attest_messages_per_sec=0,
        p2p_max_messages_per_sec=500,
    )
    for _ in range(5):
        assert node._rate_limit_ok("p1", MSG_ATTESTATION) is True


def test_class_windows_are_per_peer():
    node = _node()
    assert node._rate_limit_ok("p1", MSG_ATTESTATION) is True
    assert node._rate_limit_ok("p1", MSG_ATTESTATION) is True
    assert node._rate_limit_ok("p1", MSG_ATTESTATION) is False
    assert node._rate_limit_ok("p2", MSG_ATTESTATION) is True


def test_class_rate_ok_direct_covers_ingress_path():
    """Ingress path calls _class_rate_ok directly (primary budget already native)."""
    node = _node()
    assert node._class_rate_ok("p1", MSG_NEW_TX) is True
    assert node._class_rate_ok("p1", MSG_NEW_TX) is True
    assert node._class_rate_ok("p1", MSG_NEW_TX) is False
    # Un-classed types and empty peer ids are never class-limited.
    assert node._class_rate_ok("p1", MSG_PING) is True
    assert node._class_rate_ok("", MSG_NEW_TX) is True


def test_class_windows_pruned_under_peer_churn():
    node = _node(p2p_attest_messages_per_sec=1000)
    stale_ts = 1.0  # long expired window
    for i in range(4100):
        node._peer_class_windows[f"old-{i}\0attest"] = (1, stale_ts)
    assert node._class_rate_ok("fresh", MSG_ATTESTATION) is True
    assert len(node._peer_class_windows) < 100
    assert "fresh\0attest" in node._peer_class_windows


def test_class_exceeded_is_soft_refuse_not_ban():
    node = _node()
    peer = SimpleNamespace(peer_id="p1", host="127.0.0.1", port=1)
    node.peer_manager.peer_key = lambda _p: "p1"  # type: ignore[method-assign]
    before = int(getattr(node, "_soft_refuse_total", 0) or 0)
    assert node._strike_peer_sync(peer, "rate_limit_class_exceeded") is False
    assert int(node._soft_refuse_total) == before + 1
    st = node.get_p2p_security_status()
    assert st["rate_limit_class_drops"] >= 1


def test_security_status_exposes_class_caps():
    node = _node()
    st = node.get_p2p_security_status()
    assert st.get("attest_messages_per_sec") == 2
    assert st.get("tx_messages_per_sec") == 2
    assert st.get("block_announce_messages_per_sec") == 2
    assert "rate_limit_class_drops" in st


def test_config_defaults_and_env(monkeypatch):
    cfg = Config()
    assert cfg.p2p_attest_messages_per_sec == 80
    assert cfg.p2p_tx_messages_per_sec == 120
    assert cfg.p2p_block_announce_messages_per_sec == 40


def test_prod_json_carries_class_caps():
    for rel in (
        "docker/node.prod.json",
        "docker/node.prod.mesh1.json",
        "docker/node.prod.mesh2.json",
        "docker/node.prod.mesh3.json",
        "deploy/k8s/node.prod.k8s.json",
        "node.prod.example.json",
        "node.prod.mainnet-v1.example.json",
        "node.prod.mainnet-v1.bridge.example.json",
    ):
        cfg = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        assert cfg["p2p_attest_messages_per_sec"] > 0, rel
        assert cfg["p2p_tx_messages_per_sec"] > 0, rel
        assert cfg["p2p_block_announce_messages_per_sec"] > 0, rel
        assert cfg.get("feature_long_range", False) is False, rel


def test_needles():
    p2p = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    assert "def _class_rate_ok" in p2p
    assert "def _rate_limit_class_limit" in p2p
    assert "rate_limit_class_exceeded" in p2p
    assert "ws_checkpoint" not in p2p  # Long-Range gossip must not be ported to pin
    cfg = (ROOT / "runtime" / "config.py").read_text(encoding="utf-8")
    assert "p2p_attest_messages_per_sec" in cfg
    reject = (ROOT / "network" / "transport" / "reject.py").read_text(encoding="utf-8")
    assert "rate_limit_class_exceeded" in reject
