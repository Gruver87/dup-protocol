#!/usr/bin/env python3
"""Fail-loud honesty for prod-critical silent-except surfaces."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from blockchain.immutable_state import ImmutableStateManager
from sync.sync_engine import SyncEngine


def test_sync_state_logs_wire_probe_failure(capsys):
    peer = SimpleNamespace(peer_id="peer1", height=1)
    node = SimpleNamespace(
        blockchain=SimpleNamespace(
            get_state_root=lambda: "abc",
            get_height=lambda: 1,
            get_block=lambda _h: None,
        ),
        request_peer_state_roots_sync=MagicMock(side_effect=RuntimeError("boom")),
        p2p=SimpleNamespace(_state_consistent=True),
    )
    # SyncEngine expects node with peers collector
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: [peer]  # type: ignore
    ok = eng.sync_state()
    captured = capsys.readouterr()
    assert "wire probe failed" in captured.out
    assert eng.get_status().get("wire_probe_ok") is False
    assert eng.get_status().get("wire_probe_probed") is True
    assert ok is False
    assert node.p2p._state_consistent is False


def test_sync_state_solo_keeps_never_probed():
    """Solo / no peers must leave wire_probe as never-probed and clear consistency."""
    node = SimpleNamespace(
        blockchain=SimpleNamespace(
            get_state_root=lambda: "abc",
            get_height=lambda: 1,
            get_block=lambda _h: None,
        ),
        p2p=SimpleNamespace(_state_consistent=True),
    )
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: []  # type: ignore
    ok = eng.sync_state()
    assert ok is False
    assert eng._last_wire_probe_ok is None
    assert node.p2p._state_consistent is False
    st = eng.get_status()
    assert st.get("wire_probe_probed") is False
    assert st.get("wire_probe_ok") is False


def test_sync_state_peers_behind_no_same_height_match_fail_closed(capsys):
    """Peers all behind (or empty same-height roots) must not paint green."""
    peer = SimpleNamespace(peer_id="peer1", height=0)
    node = SimpleNamespace(
        blockchain=SimpleNamespace(
            get_state_root=lambda: "abc",
            get_height=lambda: 5,
            get_block=lambda _h: None,
        ),
        request_peer_state_roots_sync=MagicMock(
            return_value=[{"peer_id": "peer1", "height": 3, "state_root": "abc"}]
        ),
        p2p=SimpleNamespace(_state_consistent=True),
    )
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: [peer]  # type: ignore
    ok = eng.sync_state()
    captured = capsys.readouterr()
    assert ok is False
    assert "same-height" in captured.out.lower()
    assert node.p2p._state_consistent is False


def test_sync_state_empty_probe_with_peers_fail_closed(capsys):
    peer = SimpleNamespace(peer_id="peer1", height=1)
    node = SimpleNamespace(
        blockchain=SimpleNamespace(
            get_state_root=lambda: "abc",
            get_height=lambda: 1,
            get_block=lambda _h: None,
        ),
        request_peer_state_roots_sync=MagicMock(return_value=[]),
        p2p=SimpleNamespace(_state_consistent=True),
    )
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: [peer]  # type: ignore
    ok = eng.sync_state()
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower()
    assert ok is False
    assert eng.get_status().get("wire_probe_ok") is False
    assert node.p2p._state_consistent is False


def test_sync_state_timeout_none_fail_closed(capsys):
    peer = SimpleNamespace(peer_id="peer1", height=1)
    node = SimpleNamespace(
        blockchain=SimpleNamespace(
            get_state_root=lambda: "abc",
            get_height=lambda: 1,
            get_block=lambda _h: None,
        ),
        request_peer_state_roots_sync=MagicMock(return_value=None),
        p2p=SimpleNamespace(_state_consistent=True),
    )
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: [peer]  # type: ignore
    ok = eng.sync_state()
    assert ok is False
    assert eng.get_status().get("wire_probe_ok") is False


def test_sync_status_unknown_probe_is_fail_closed():
    eng = SyncEngine(SimpleNamespace(p2p=SimpleNamespace(_state_consistent=True)))
    eng._collect_p2p_peers = lambda: []  # type: ignore
    st = eng.get_status()
    assert st.get("wire_probe_ok") is False
    assert st.get("wire_probe_probed") is False


def test_sync_state_missing_get_state_root_fail_closed(capsys):
    node = SimpleNamespace(
        blockchain=SimpleNamespace(get_height=lambda: 1),
        p2p=SimpleNamespace(_state_consistent=True),
    )
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: []  # type: ignore
    ok = eng.sync_state()
    captured = capsys.readouterr()
    assert ok is False
    assert "missing get_state_root" in captured.out
    assert node.p2p._state_consistent is False
    assert eng.get_status().get("wire_probe_ok") is False


def test_ims_reconcile_fail_loud_nonce():
    store = SimpleNamespace(
        get_balance_satoshi=lambda _a: 1_000_000,
        get_nonce=MagicMock(side_effect=RuntimeError("nonce down")),
    )
    ims = ImmutableStateManager()
    raised = False
    try:
        ims.reconcile_from_store(store, ["alice"], fail_loud=True)
    except RuntimeError:
        raised = True
    assert raised


def test_ims_reconcile_nonce_soft_without_fail_loud(capsys):
    store = SimpleNamespace(
        get_balance_satoshi=lambda _a: 2_000_000,
        get_nonce=MagicMock(side_effect=RuntimeError("nonce down")),
    )
    ims = ImmutableStateManager()
    n = ims.reconcile_from_store(store, ["bob"], fail_loud=False)
    assert n == 1
    assert ims.get_balance_satoshi("bob") == 2_000_000
    assert "get_nonce failed" in capsys.readouterr().out


def test_state_root_status_peer_probe_error_surface():
    # Static contract: api/http.py must expose peer_probe_error key
    from pathlib import Path

    text = Path("api/http.py").read_text(encoding="utf-8")
    assert "peer_probe_error" in text
    assert "record_state_root_mismatch failed" in Path("core/blockchain.py").read_text(
        encoding="utf-8"
    )
    assert "genesis meta write failed" in Path("core/blockchain.py").read_text(encoding="utf-8")
    assert "sync_state probe failed" in Path("main.py").read_text(encoding="utf-8")


def test_local_needs_genesis_store_error_empty_tip_fail_closed(caplog):
    """Empty tip + store error must still request genesis, not skip as 'have chain'."""
    import logging

    class _BoomStore:
        def get_height(self):
            return 0

        def get_last_block(self):
            raise RuntimeError("store down")

    eng = SyncEngine(SimpleNamespace(blockchain=_BoomStore()))
    with caplog.at_level(logging.WARNING, logger="Sync.Engine"):
        assert eng._local_needs_genesis() is True
    assert "get_last_block failed in _local_needs_genesis" in caplog.text


def test_local_needs_genesis_store_error_nonempty_does_not_force_genesis():
    """Non-empty height must not force genesis import over an existing chain."""

    class _BoomStore:
        def get_height(self):
            return 100

        def get_last_block(self):
            raise RuntimeError("store down")

    eng = SyncEngine(SimpleNamespace(blockchain=_BoomStore()))
    assert eng._local_needs_genesis() is False


def test_shared_sync_engine_and_unsolicited_state_root_honesty():
    from pathlib import Path

    main_py = Path("main.py").read_text(encoding="utf-8")
    assert "p2p.sync_engine = self.sync_engine" in main_py
    assert "shared with P2P" in main_py
    assert "ai_validator.update_performance" not in main_py
    p2p_py = Path("network/p2p_node.py").read_text(encoding="utf-8")
    solicit_py = Path("sync/solicit.py").read_text(encoding="utf-8")
    # ADR 0003: solicit-only strike lives in SyncSolicitHub (evacuated from p2p).
    assert "unsolicited_state_root_response" in solicit_py
    assert "solicit_hub.fulfill_or_reject" in p2p_py
    sync_py = Path("sync/sync_engine.py").read_text(encoding="utf-8")
    assert "State root mismatch vs" in sync_py
    http_py = Path("api/http.py").read_text(encoding="utf-8")
    assert 'after.get("state_consistent", False)' in http_py
    alerts = Path("deploy/prometheus/alerts.yml").read_text(encoding="utf-8")
    assert "AbsoluteSyncWireProbeNeverProbed" in alerts
    assert "AbsoluteProdSqliteEngine" in alerts


def test_empty_probe_does_not_wipe_last_known_green():
    """Block-gossip empty RTT must not LOCKED_DOWN a just-proven same-height match."""
    root = "aa" * 32
    peer = SimpleNamespace(peer_id="p1", height=1, head=root, dial_target="")
    node = SimpleNamespace(
        blockchain=SimpleNamespace(
            get_state_root=lambda: root,
            get_height=lambda: 1,
            get_block=lambda _h: None,
        ),
        request_peer_state_roots_sync=MagicMock(
            return_value=[{"peer_id": "p1", "height": 1, "state_root": root}]
        ),
        p2p=SimpleNamespace(_state_consistent=False),
        _state_consistent=False,
    )
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: [peer]  # type: ignore
    assert eng.sync_state() is True
    node.request_peer_state_roots_sync = MagicMock(return_value=[])
    assert eng.sync_state() is True
    assert eng.consistency.snapshot().consistent is True
    assert node._state_consistent is True


def test_empty_probe_sticky_green_expires(capsys):
    """Persistent empty wire must not stay green after consecutive empties."""
    root = "aa" * 32
    peer = SimpleNamespace(peer_id="p1", height=1, head=root, dial_target="")
    node = SimpleNamespace(
        blockchain=SimpleNamespace(
            get_state_root=lambda: root,
            get_height=lambda: 1,
            get_block=lambda _h: None,
        ),
        request_peer_state_roots_sync=MagicMock(
            return_value=[{"peer_id": "p1", "height": 1, "state_root": root}]
        ),
        p2p=SimpleNamespace(_state_consistent=False),
        _state_consistent=False,
    )
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: [peer]  # type: ignore
    eng._wire_probe_backoff_sec = 0.0
    eng._wire_sticky_empty_max = 3
    assert eng.sync_state() is True
    node.request_peer_state_roots_sync = MagicMock(return_value=[])
    assert eng.sync_state() is True
    assert eng.sync_state() is True
    assert eng.sync_state() is False
    assert "sticky green expired" in capsys.readouterr().out
    assert node._state_consistent is False


def test_registry_adapter_logs_bus_and_lockdown_failures(caplog):
    import logging

    from consensus.bft.types import ConsensusSecurityEvidence
    from consensus.registry_adapter import (
        AdapterConsensusEvidence,
        AdapterConsensusLockdown,
        AdapterConsensusSideEffect,
    )

    class _Bus:
        def emit(self, *_a, **_k):
            raise RuntimeError("bus down")

    adapter = SimpleNamespace(bus=_Bus())

    def _bad_hook(_reason: str) -> None:
        raise RuntimeError("hook down")

    adapter._lockdown_hook = _bad_hook
    with caplog.at_level(logging.WARNING, logger="abs.consensus"):
        AdapterConsensusEvidence(adapter).emit(
            ConsensusSecurityEvidence(reason_code="double_vote", validator_id="v1")
        )
        AdapterConsensusLockdown(adapter).request_lockdown("consensus_double_sign")
        AdapterConsensusSideEffect(adapter).on_finalized("ab" * 32, 3)
    text = caplog.text
    assert "security.consensus_refuse emit failed" in text
    assert "security.consensus_lockdown emit failed" in text
    assert "consensus lockdown hook failed" in text
    assert "consensus.finalized emit failed" in text


def test_fork_async_reorg_logs_then_sync_fallback(caplog):
    import logging

    from network.fork_adapters import ForkReconcileP2PChainAdapter

    class _Loop:
        def is_running(self):
            return True

    class _P2P:
        def _reorg_and_import_async(self, *_a, **_k):
            raise RuntimeError("async boom")

        def _reorg_and_import(self, *_a, **_k):
            return True

    with caplog.at_level(logging.WARNING, logger="P2P.ForkAdapter"):
        ok = ForkReconcileP2PChainAdapter(_P2P(), _Loop()).reorg_and_import(
            1, {"hash": "aa"}
        )
    assert ok is True
    assert "async reorg_and_import failed" in caplog.text


def test_http_engine_result_refuses_truthy_objects():
    from api.http import _http_engine_result

    class _Truthy:
        def __bool__(self):
            return True

    assert _http_engine_result(True) == {"success": True}
    assert _http_engine_result(False) == {"success": False}
    assert _http_engine_result(None)["error"] == "engine_returned_none"
    assert _http_engine_result(_Truthy())["success"] is False
    assert _http_engine_result(_Truthy())["error"] == "engine_result_not_boolean"
    assert _http_engine_result({"ok": 1})["ok"] == 1
    flagged = type("R", (), {"success": False, "error": "locked"})()
    out = _http_engine_result(flagged)
    assert out["success"] is False
    assert out["error"] == "locked"


def test_format_tx_uses_satoshi_not_ieee_float():
    from api.eth_format import format_tx
    from runtime.amount import WEI_PER_SATOSHI, to_satoshi

    row = format_tx({"hash": "0xab", "value": 1.5, "block_height": 3})
    assert row["value"] == hex(to_satoshi(1.5) * WEI_PER_SATOSHI)
    junk = format_tx({"hash": "0xcd", "value": True})
    assert junk["value"] is None
