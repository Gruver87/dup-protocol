"""Exp→pin honesty: readiness peer heights, RpcService.enabled, UoW/consensus logs."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]


def test_rpc_service_enabled_tracks_query_port():
    from api.rpc_service import RpcService

    svc = RpcService(query=None, config=SimpleNamespace())
    assert svc.get_stats()["enabled"] is False
    q = SimpleNamespace(tip_height=lambda: 7)
    svc2 = RpcService(query=q, config=SimpleNamespace())
    assert svc2.get_stats()["enabled"] is True
    assert svc2.get_stats()["tip"] == 7


def test_peer_heights_logs_get_peers_info_failure(caplog):
    import logging

    from api import http as http_mod

    class _P2P:
        def get_peers_info(self):
            raise RuntimeError("peers info boom")

        peers = {}

    with caplog.at_level(logging.WARNING, logger="API"):
        heights = http_mod._peer_heights_from_p2p(_P2P())
    assert heights == []
    assert "peer heights from get_peers_info failed" in caplog.text


def test_honesty_wave_needles_present():
    http = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "peer heights from get_peers_info failed" in http
    assert "JSONRPCHandler accepting_requests not set" in http
    rpc = (ROOT / "api" / "rpc_service.py").read_text(encoding="utf-8")
    assert '"enabled": self.query is not None' in rpc
    adapter = (ROOT / "consensus" / "adapter.py").read_text(encoding="utf-8")
    assert "arm_quorum_live failed" in adapter
    assert "round_state add_block failed" in adapter
    bc = (ROOT / "core" / "blockchain.py").read_text(encoding="utf-8")
    assert "UoW abort failed after StorageError" in bc
    assert "canonical persist failed" in bc
    rocks = (ROOT / "storage" / "adapters" / "rocks_adapter.py").read_text(
        encoding="utf-8"
    )
    assert "storage ping failed" in rocks
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "set_accepting_requests failed at boot" in main
    p2p = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    assert "P2PLineFramer construct failed" in p2p
