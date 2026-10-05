#!/usr/bin/env python3
"""Phase 0 HTTP-hang fix: wire-probe HOL backoff (ADR 0020 libp2p mesh cutover)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from runtime.mesh_mining import mesh_ready_for_mining
from sync.sync_engine import SyncEngine

ROOT = Path(__file__).resolve().parents[2]


def _node(probe: MagicMock) -> SimpleNamespace:
    return SimpleNamespace(
        blockchain=SimpleNamespace(
            get_state_root=lambda: "abc",
            get_height=lambda: 1,
            get_block=lambda _h: None,
        ),
        request_peer_state_roots_sync=probe,
        p2p=SimpleNamespace(_state_consistent=False),
    )


def _engine(probe: MagicMock) -> SyncEngine:
    peer = SimpleNamespace(peer_id="peer1", height=1)
    eng = SyncEngine(_node(probe))
    eng._collect_p2p_peers = lambda: [peer]  # type: ignore[method-assign]
    return eng


def test_sync_engine_defaults_expose_backoff_attrs() -> None:
    eng = SyncEngine(SimpleNamespace())
    assert eng._wire_probe_fail_ts == 0.0
    assert eng._wire_probe_backoff_sec == 8.0


def test_timeout_sets_fail_ts_and_backoff_skips_resolicit(capsys) -> None:
    probe = MagicMock(return_value=None)
    eng = _engine(probe)
    assert eng.sync_state() is False
    assert eng._wire_probe_fail_ts > 0.0
    assert probe.call_count == 1

    # Second call inside backoff must NOT solicit again and must stay fail-closed.
    assert eng.sync_state() is False
    assert probe.call_count == 1
    assert "wire probe backoff" in capsys.readouterr().out


def test_empty_and_exception_probe_set_fail_ts() -> None:
    for probe in (
        MagicMock(return_value=[]),
        MagicMock(side_effect=RuntimeError("boom")),
    ):
        eng = _engine(probe)
        assert eng.sync_state() is False
        assert eng._wire_probe_fail_ts > 0.0


def test_successful_probe_clears_fail_ts() -> None:
    probe = MagicMock(return_value=[{"peer_id": "peer1", "height": 1, "state_root": "abc"}])
    eng = _engine(probe)
    eng._wire_probe_fail_ts = 1.0  # long expired
    eng._wire_probe_backoff_sec = 0.0
    assert eng.sync_state() is True
    assert eng._wire_probe_fail_ts == 0.0


def test_mesh_ready_soft_fail_only_relaxes_unanimous_tip_without_wire_roots() -> None:
    kwargs = dict(
        min_mesh_peers=2,
        connected_peers=2,
        local_height=5,
        local_root="abc",
        state_consistent=False,
        peer_heights=[5, 5],
    )
    assert mesh_ready_for_mining(wire_roots=[], **kwargs) is False
    assert mesh_ready_for_mining(wire_roots=[], wire_soft_fail=True, **kwargs) is True
    # Real root mismatch still refuses even under soft-fail.
    mismatch = [{"height": 5, "state_root": "other"}]
    assert mesh_ready_for_mining(wire_roots=mismatch, wire_soft_fail=True, **kwargs) is False
    # Followers behind still refuse.
    behind = dict(kwargs, peer_heights=[4, 5])
    assert mesh_ready_for_mining(wire_roots=[], wire_soft_fail=True, **behind) is False


def test_main_mining_loop_wire_probe_backoff_surface() -> None:
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    for needle in (
        "_wire_probe_fail_ts",
        "_wire_probe_backoff_sec",
        "_wire_roots_cache",
        "_under_mesh_reconnect_ts",
        "reconnect_known_peers",
        "wire_soft_fail",
    ):
        assert needle in src, needle
    # Prod must never relax mesh readiness via soft-fail.
    assert 'and (not bool(getattr(self.config, "is_production", False)))' in src
