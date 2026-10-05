"""Late state_root stash/consume, wire-probe gate, coalesced gather (STRICT mesh P2P).

Ported from DUP experimental STRICT hardening (no Long-Range / ws_checkpoint).
Unit scope only — mesh probe / industrial gate are separate acceptance.
"""
from __future__ import annotations

import asyncio
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.chain_apply_queue import ChainApplyQueue
from network.p2p_node import (
    MSG_STATE_ROOT_RESPONSE,
    P2PNode,
    PeerConnection,
    should_defer_tip_safety_skip_ahead,
)
from sync.solicit import SyncSolicitHub


def _coalesce_node(*, peers=None):
    node = object.__new__(P2PNode)
    node._state_root_probe_task = None
    node._state_root_probe_lock = None
    node._wire_probe_hold_until = 0.0
    node.apply_queue = None
    live = {"p": object()} if peers is None else dict(peers)
    node.peer_manager = SimpleNamespace(peers=live)
    return node


def _late_node() -> P2PNode:
    node = object.__new__(P2PNode)
    node._state_root_late = {}
    node._state_root_timeout_at = {}
    node._state_root_late_accepts_total = 0
    return node


# ── late_state_root stash / consume ─────────────────────────────────────────


def test_stash_late_state_root_only_after_recent_timeout():
    node = _late_node()
    peer = SimpleNamespace(peer_id="p")
    payload = {"height": 1, "state_root": "aa" * 32}
    assert node._stash_late_state_root(peer, payload) is False
    node._state_root_timeout_at["p"] = time.monotonic()
    assert node._stash_late_state_root(peer, payload) is True
    assert node._state_root_late["p"][0]["height"] == 1
    assert node._state_root_late_accepts_total == 1


def test_stash_late_state_root_refuses_expired_timeout_mark_and_non_dict():
    node = _late_node()
    peer = SimpleNamespace(peer_id="p")
    node._state_root_timeout_at["p"] = time.monotonic() - 5.0
    assert node._stash_late_state_root(peer, {"height": 1}) is False
    node._state_root_timeout_at["p"] = time.monotonic()
    assert node._stash_late_state_root(peer, ["not", "a", "dict"]) is False
    assert node._stash_late_state_root(SimpleNamespace(peer_id=""), {"h": 1}) is False
    assert node._state_root_late == {}
    assert node._state_root_late_accepts_total == 0


def test_stash_late_state_root_keys_libp2p_peer_id():
    node = _late_node()
    peer = SimpleNamespace(peer_id="node-a", _libp2p_peer_id="12D3KooW")
    node._state_root_timeout_at["node-a"] = time.monotonic()
    assert node._stash_late_state_root(peer, {"height": 2}) is True
    assert set(node._state_root_late) == {"node-a", "12D3KooW"}


def test_consume_late_state_root_returns_stashed_payload_once():
    node = _late_node()
    peer = SimpleNamespace(peer_id="p")
    assert node._consume_late_state_root(peer) is None
    payload = {"height": 3, "state_root": "ab" * 32}
    node._state_root_late["p"] = (payload, time.monotonic())
    assert node._consume_late_state_root(peer) == payload
    assert node._consume_late_state_root(peer) is None


def test_consume_late_state_root_drops_expired_stash():
    node = _late_node()
    peer = SimpleNamespace(peer_id="p")
    node._state_root_late["p"] = ({"height": 3}, time.monotonic() - 5.0)
    assert node._consume_late_state_root(peer) is None
    assert "p" not in node._state_root_late


def _msg_node(hub: SyncSolicitHub) -> P2PNode:
    node = _late_node()
    node._use_native_transport = True
    node.solicit_hub = hub
    node._strike_peer_sync = MagicMock(return_value=False)  # type: ignore[method-assign]
    node.bump_counter = MagicMock()  # type: ignore[method-assign]
    node._remove_peer = MagicMock()  # type: ignore[method-assign]
    node.dispatcher = SimpleNamespace(dispatch=AsyncMock())
    return node


@pytest.mark.asyncio
async def test_handle_message_stashes_late_state_root_without_strike():
    """Waiter popped by hub.timeout(): reply must be stashed, not struck/dispatched."""
    node = _msg_node(SyncSolicitHub())
    peer = SimpleNamespace(peer_id="p")
    node._state_root_timeout_at["p"] = time.monotonic()
    data = {"height": 7, "state_root": "cc" * 32, "head_hash": "dd" * 32}
    await node._handle_message(
        peer, {"type": MSG_STATE_ROOT_RESPONSE, "data": data}
    )
    assert node._state_root_late["p"][0] == data
    node._strike_peer_sync.assert_not_called()
    node.dispatcher.dispatch.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_state_root_without_timeout_mark_still_dispatches():
    """No recent waiter timeout → never silently absorb (unsolicited path intact)."""
    node = _msg_node(SyncSolicitHub())
    peer = SimpleNamespace(peer_id="p")
    data = {"height": 7, "state_root": "cc" * 32, "head_hash": "dd" * 32}
    await node._handle_message(
        peer, {"type": MSG_STATE_ROOT_RESPONSE, "data": data}
    )
    assert node._state_root_late == {}
    node.dispatcher.dispatch.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_stashes_when_hub_reports_late_state_root():
    """Done-future waiter still armed → hub consumes as late_state_root; stash it."""
    hub = SyncSolicitHub()
    node = _msg_node(hub)
    peer = SimpleNamespace(peer_id="p")
    fut = asyncio.get_running_loop().create_future()
    hub.arm("p", (MSG_STATE_ROOT_RESPONSE,), fut, {"kind": "state_root", "height": 7})
    fut.set_result(None)
    node._state_root_timeout_at["p"] = time.monotonic()
    data = {"height": 7, "state_root": "cc" * 32, "head_hash": "dd" * 32}
    await node._handle_message(
        peer, {"type": MSG_STATE_ROOT_RESPONSE, "data": data}
    )
    assert node._state_root_late["p"][0] == data
    node._strike_peer_sync.assert_not_called()
    node.dispatcher.dispatch.assert_not_awaited()


@pytest.mark.asyncio
async def test_wait_peer_response_timeout_returns_late_reply_from_grace_window():
    hub = SyncSolicitHub()
    node = _msg_node(hub)
    peer = SimpleNamespace(peer_id="p")
    node.peer_manager = SimpleNamespace(peers={"p": peer})
    data = {"height": 7, "state_root": "cc" * 32, "head_hash": "dd" * 32}

    async def _presend():
        async def _late_reply():
            # Lands after the 0.1s waiter timeout, inside the 0.4s grace.
            await asyncio.sleep(0.25)
            await node._handle_message(
                peer, {"type": MSG_STATE_ROOT_RESPONSE, "data": data}
            )

        asyncio.get_running_loop().create_task(_late_reply())
        return True

    out = await node._wait_peer_response(
        peer,
        (MSG_STATE_ROOT_RESPONSE,),
        timeout=0.1,
        presend=_presend,
        request_ctx={"kind": "state_root", "height": 7},
    )
    assert out == {"type": MSG_STATE_ROOT_RESPONSE, "data": data}
    assert node._state_root_late_accepts_total == 1
    node._strike_peer_sync.assert_not_called()
    assert hub.armed_count == 0


@pytest.mark.asyncio
async def test_wait_peer_response_timeout_without_reply_is_none_and_clears_hub():
    hub = SyncSolicitHub()
    node = _msg_node(hub)
    peer = SimpleNamespace(peer_id="p")
    node.peer_manager = SimpleNamespace(peers={"p": peer})
    out = await node._wait_peer_response(
        peer,
        (MSG_STATE_ROOT_RESPONSE,),
        timeout=0.05,
        presend=AsyncMock(return_value=True),
        request_ctx={"kind": "state_root", "height": 1},
    )
    assert out is None
    assert "p" in node._state_root_timeout_at
    assert hub.armed_count == 0


@pytest.mark.asyncio
async def test_wait_peer_response_send_failure_fails_fast():
    hub = SyncSolicitHub()
    node = _msg_node(hub)
    peer = SimpleNamespace(peer_id="p")
    t0 = time.monotonic()
    out = await node._wait_peer_response(
        peer,
        (MSG_STATE_ROOT_RESPONSE,),
        timeout=5.0,
        presend=AsyncMock(return_value=False),
        request_ctx={"kind": "state_root", "height": 1},
    )
    assert out is None
    assert (time.monotonic() - t0) < 1.0
    assert hub.armed_count == 0


@pytest.mark.asyncio
async def test_request_peer_state_root_consumes_late_stash_without_retry():
    node = object.__new__(P2PNode)
    node.blockchain = SimpleNamespace(get_height=lambda: 1)
    peer = SimpleNamespace(peer_id="p", height=1)
    node._consume_late_state_root = lambda _p: {"height": 1, "state_root": "aa" * 32}
    node._state_root_request_ctx = lambda _h: {"kind": "state_root", "height": 1}
    called = {"wait": 0}

    async def _wait(*_a, **_k):
        called["wait"] += 1
        return None

    node._wait_peer_response = _wait  # type: ignore[method-assign]
    out = await node.request_peer_state_root(peer, 1, timeout=0.4, retry=False)
    assert out["height"] == 1
    assert out["state_root"] == "aa" * 32
    assert called["wait"] == 0


@pytest.mark.asyncio
async def test_request_peer_state_root_late_stash_after_empty_wait_skips_retry():
    node = object.__new__(P2PNode)
    node.blockchain = SimpleNamespace(get_height=lambda: 1)
    peer = SimpleNamespace(peer_id="p", height=1)
    stashes = [None, {"height": 1, "state_root": "bb" * 32}]
    node._consume_late_state_root = lambda _p: stashes.pop(0)
    node._state_root_request_ctx = lambda _h: {"kind": "state_root", "height": 1}
    called = {"wait": 0}

    async def _wait(*_a, **_k):
        called["wait"] += 1
        return None

    node._wait_peer_response = _wait  # type: ignore[method-assign]
    out = await node.request_peer_state_root(peer, 1, timeout=0.4, retry=True)
    assert out == {"height": 1, "state_root": "bb" * 32}
    assert called["wait"] == 1  # retry RTT skipped: late stash won


@pytest.mark.asyncio
async def test_request_peer_state_roots_drains_stash_after_empty_wait():
    node = object.__new__(P2PNode)
    peer = SimpleNamespace(peer_id="p1", height=4)
    node.blockchain = SimpleNamespace(get_height=lambda: 4)
    node.peer_manager = SimpleNamespace(peers={"p1": peer})
    node._peer_sync_fail = 0

    async def _empty(*_a, **_k):
        return None

    node.request_peer_state_root = _empty  # type: ignore[method-assign]
    payload = {"height": 4, "state_root": "ab" * 32}
    node._consume_late_state_root = lambda _p: dict(payload)
    out = await node.request_peer_state_roots(per_peer_timeout=0.4, retry=False)
    assert len(out) == 1
    assert out[0]["peer_id"] == "p1"
    assert out[0]["height"] == 4


# ── wire_probe_gate ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wait_wire_probe_gate_holds_until():
    node = object.__new__(P2PNode)
    node.apply_queue = SimpleNamespace(busy=False)
    node._wire_probe_hold_until = time.monotonic() + 0.25
    waited = await node._wait_wire_probe_gate(1.0)
    assert waited >= 0.2
    assert waited < 0.7


@pytest.mark.asyncio
async def test_wait_wire_probe_gate_waits_while_apply_busy_then_releases():
    node = object.__new__(P2PNode)
    q = SimpleNamespace(busy=True, maxsize=64, depth=0)
    node.apply_queue = q
    node._wire_probe_hold_until = 0.0

    async def _release():
        await asyncio.sleep(0.2)
        q.busy = False

    rel = asyncio.create_task(_release())
    waited = await node._wait_wire_probe_gate(1.0)
    await rel
    assert 0.15 <= waited < 0.7


@pytest.mark.asyncio
async def test_wait_wire_probe_gate_is_bounded_when_apply_stays_busy():
    node = object.__new__(P2PNode)
    node.apply_queue = SimpleNamespace(busy=True, maxsize=64, depth=0)
    node._wire_probe_hold_until = 0.0
    waited = await node._wait_wire_probe_gate(0.3)
    assert 0.25 <= waited < 0.8


@pytest.mark.asyncio
async def test_wait_wire_probe_gate_breaks_on_saturated_queue():
    node = object.__new__(P2PNode)
    node.apply_queue = SimpleNamespace(busy=True, maxsize=8, depth=8)
    node._wire_probe_hold_until = time.monotonic() + 5.0
    waited = await node._wait_wire_probe_gate(1.0)
    assert waited < 0.2


@pytest.mark.asyncio
async def test_wait_wire_probe_gate_no_queue_no_hold_returns_immediately():
    node = object.__new__(P2PNode)
    node.apply_queue = None
    node._wire_probe_hold_until = 0.0
    assert (await node._wait_wire_probe_gate(1.0)) < 0.1


def test_note_local_forge_sets_bounded_hold_and_monotonic_height():
    node = object.__new__(P2PNode)
    node._wire_probe_hold_until = 0.0
    node._last_local_forge_height = 0
    t0 = time.monotonic()
    node.note_local_forge(99.0, height=10)
    assert node._wire_probe_hold_until - t0 <= 2.1  # hold clamped to 2s
    assert node._last_local_forge_height == 10
    node.note_local_forge(0.5, height=9)
    assert node._last_local_forge_height == 10


@pytest.mark.asyncio
async def test_coalesced_waits_post_forge_hold_before_flight():
    node = _coalesce_node()
    node._wire_probe_hold_until = time.monotonic() + 0.2
    started = []

    async def _roots(*, per_peer_timeout=8.0, retry=True):
        started.append(time.monotonic())
        return [{"peer_id": "p", "height": 1, "state_root": "aa"}]

    node.request_peer_state_roots = _roots  # type: ignore[method-assign]
    t0 = time.monotonic()
    out = await node._coalesced_peer_state_roots()
    assert out[0]["peer_id"] == "p"
    assert started and (started[0] - t0) >= 0.15


# ── coalesced gather ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_coalesced_peer_state_roots_joins_inflight():
    node = _coalesce_node()
    calls = []

    async def _roots(*, per_peer_timeout=8.0, retry=True):
        calls.append((per_peer_timeout, retry))
        await asyncio.sleep(0.05)
        return [{"peer_id": "p", "height": 1, "state_root": "aa"}]

    node.request_peer_state_roots = _roots  # type: ignore[method-assign]
    t1 = asyncio.create_task(node._coalesced_peer_state_roots())
    t2 = asyncio.create_task(node._coalesced_peer_state_roots())
    r1, r2 = await asyncio.gather(t1, t2)
    assert r1 == r2
    assert len(calls) == 1
    assert calls[0] == (6.5, False)


@pytest.mark.asyncio
async def test_coalesced_flight_clears_task_after_completion():
    node = _coalesce_node()

    async def _roots(*, per_peer_timeout=8.0, retry=True):
        return [{"peer_id": "p"}]

    node.request_peer_state_roots = _roots  # type: ignore[method-assign]
    await node._coalesced_peer_state_roots()
    await asyncio.sleep(0)
    assert node._state_root_probe_task is None


def test_sync_waiter_timeout_does_not_cancel_inflight():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    node = _coalesce_node()
    node._loop = loop
    node._running = True
    finished = {"ok": False, "cancelled": False}

    async def _slow_roots(*, per_peer_timeout=8.0, retry=True):
        try:
            await asyncio.sleep(1.2)
            finished["ok"] = True
            return [{"peer_id": "p"}]
        except asyncio.CancelledError:
            finished["cancelled"] = True
            raise

    node.request_peer_state_roots = _slow_roots  # type: ignore[method-assign]
    try:
        out = node.request_peer_state_roots_sync(timeout=0.5)
        assert out is None
        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline and not finished["ok"]:
            time.sleep(0.05)
        assert finished["ok"] is True
        assert finished["cancelled"] is False
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)


@pytest.mark.asyncio
async def test_coalesce_empty_peers_does_not_join_stale_flight():
    """Isolated node must not wait on a dead-socket coalesced inflight."""
    node = _coalesce_node(peers={})
    started = asyncio.Event()

    async def _slow(*, per_peer_timeout=8.0, retry=True):
        started.set()
        await asyncio.sleep(5)
        return [{"peer_id": "dead"}]

    stale = asyncio.create_task(_slow())
    await started.wait()
    node._state_root_probe_task = stale
    t0 = time.monotonic()
    out = await asyncio.wait_for(node._coalesced_peer_state_roots(), timeout=0.5)
    assert out == []
    assert (time.monotonic() - t0) < 0.4
    stale.cancel()
    await asyncio.gather(stale, return_exceptions=True)


def test_sync_empty_peers_returns_empty_not_timeout():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    node = _coalesce_node(peers={})
    node._loop = loop
    node._running = True

    async def _must_not_run(*, per_peer_timeout=8.0, retry=True):
        raise AssertionError("isolated node must not start a state_root flight")

    node.request_peer_state_roots = _must_not_run  # type: ignore[method-assign]
    try:
        t0 = time.monotonic()
        out = node.request_peer_state_roots_sync(timeout=8)
        assert out == []
        assert (time.monotonic() - t0) < 0.5
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)


def test_apply_completed_wire_probe_sets_consistent() -> None:
    from sync.sync_engine import SyncEngine

    node = object.__new__(P2PNode)
    root = "aa" * 32
    node.blockchain = SimpleNamespace(
        get_state_root=lambda: root,
        get_height=lambda: 5,
    )
    node._state_consistent = False
    peer = SimpleNamespace(peer_id="p1", height=5, head=root, dial_target="")
    node.peer_manager = SimpleNamespace(peers={"p1": peer})
    eng = SyncEngine(node)
    eng._collect_p2p_peers = lambda: [peer]  # type: ignore
    node.sync_engine = eng
    assert eng.consistency.snapshot().consistent is False

    async def _done():
        return [{"peer_id": "p1", "height": 5, "state_root": root}]

    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(_done())
        loop.run_until_complete(task)
        node._apply_completed_wire_probe(task)
    finally:
        loop.close()
    assert eng.consistency.snapshot().consistent is True
    assert node._state_consistent is True


def test_apply_completed_wire_probe_logs_task_failure(caplog) -> None:
    import logging

    node = object.__new__(P2PNode)

    async def _boom():
        raise RuntimeError("probe boom")

    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(_boom())
        try:
            loop.run_until_complete(task)
        except RuntimeError:
            pass
        with caplog.at_level(logging.WARNING, logger="P2P"):
            node._apply_completed_wire_probe(task)
    finally:
        loop.close()
    assert "coalesced wire probe task failed" in caplog.text


# ── tip-safety skip-ahead / apply busy / catch-up lock / write bound ────────


def test_should_defer_tip_safety_skip_ahead_only_tip_plus_two_while_busy():
    assert should_defer_tip_safety_skip_ahead(
        apply_busy=True, candidate_height=12, tip_height=10
    )
    assert not should_defer_tip_safety_skip_ahead(
        apply_busy=False, candidate_height=12, tip_height=10
    )
    assert not should_defer_tip_safety_skip_ahead(
        apply_busy=True, candidate_height=13, tip_height=10
    )
    assert not should_defer_tip_safety_skip_ahead(
        apply_busy=True, candidate_height=11, tip_height=10
    )
    assert not should_defer_tip_safety_skip_ahead(
        apply_busy=True, candidate_height="x", tip_height=10  # type: ignore[arg-type]
    )


def test_tip_safety_precheck_defers_skip_ahead_while_apply_busy():
    node = object.__new__(P2PNode)
    shadow = MagicMock()
    shadow.enforce = True
    node.tip_safety_shadow = shadow
    node.apply_queue = SimpleNamespace(busy=True)
    node.blockchain = SimpleNamespace(get_height=lambda: 10)
    assert node._tip_safety_precheck({"height": 12}) is True
    shadow.observe_before_import.assert_not_called()


def test_tip_safety_precheck_runs_when_apply_idle():
    node = object.__new__(P2PNode)
    shadow = MagicMock()
    shadow.enforce = False
    node.tip_safety_shadow = shadow
    node.apply_queue = SimpleNamespace(busy=False)
    node.blockchain = SimpleNamespace(get_height=lambda: 10)
    assert node._tip_safety_precheck({"height": 12}) is True
    shadow.observe_before_import.assert_called_once()


def test_chain_apply_queue_busy_tracks_in_flight_dispatch():
    started = threading.Event()
    release = threading.Event()

    class _Chain:
        def import_block(self, _blk):
            started.set()
            release.wait(timeout=3.0)
            return True

    q = ChainApplyQueue(_Chain(), maxsize=4, timeout_sec=5.0, name="busy-test")
    try:
        assert q.busy is False
        done: dict = {}

        def _submit():
            done["ok"] = q.submit_import({"height": 1})

        t = threading.Thread(target=_submit, daemon=True)
        t.start()
        assert started.wait(timeout=2.0)
        # qsize is 0 while dispatch runs — busy must still be True.
        assert q.depth == 0
        assert q.busy is True
        assert q.stats()["busy"] is True
        release.set()
        t.join(timeout=3.0)
        assert done.get("ok") is True
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and q.busy:
            time.sleep(0.01)
        assert q.busy is False
    finally:
        release.set()
        q.stop()


@pytest.mark.asyncio
async def test_global_catch_up_lock_is_single_shared_lock():
    node = object.__new__(P2PNode)
    node._catch_up_apply_lock = None
    a = node._global_catch_up_lock()
    b = node._global_catch_up_lock()
    assert a is b
    async with a:
        assert a.locked()
        assert b.locked()


def test_native_write_bound_sets_short_timeout_then_restores_full():
    peer = PeerConnection(drain_timeout_sec=5.0)
    calls: list = []
    conn = SimpleNamespace(set_timeout_ms=lambda ms: calls.append(("t", ms)))
    peer._native_conn = conn
    peer._native_io_timeout_ms = 30000
    out = peer._native_write_bound(lambda x: calls.append(("w", x)) or "ok", b"abc")
    assert out == "ok"
    assert calls == [("t", 750), ("w", b"abc"), ("t", 30000)]


def test_native_write_bound_restores_timeout_when_write_raises():
    peer = PeerConnection(drain_timeout_sec=5.0)
    calls: list = []
    peer._native_conn = SimpleNamespace(
        set_timeout_ms=lambda ms: calls.append(ms)
    )
    peer._native_io_timeout_ms = 30000

    def _boom(*_a):
        raise OSError("write timed out")

    with pytest.raises(OSError):
        peer._native_write_bound(_boom, b"x")
    assert calls == [750, 30000]


def test_native_write_timeout_is_bounded_below_probe_budget():
    assert PeerConnection(drain_timeout_sec=5.0)._native_write_timeout_sec() == 0.75
    assert PeerConnection(drain_timeout_sec=0.5)._native_write_timeout_sec() == 0.5
    assert PeerConnection(drain_timeout_sec=0.5)._native_write_timeout_sec() < 6.5


@pytest.mark.asyncio
async def test_write_payload_uses_bound_native_write():
    peer = PeerConnection(drain_timeout_sec=5.0)
    calls: list = []

    def _write(payload):
        calls.append(("w", payload))
        return len(payload)

    peer._native_conn = SimpleNamespace(
        set_timeout_ms=lambda ms: calls.append(("t", ms)),
        write=_write,
    )
    peer._native_io_timeout_ms = 30000
    await peer._write_payload(b"hello")
    assert calls[0] == ("t", 750)
    assert ("w", b"hello") in calls
    assert calls[-1] == ("t", 30000)
