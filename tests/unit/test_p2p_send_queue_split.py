#!/usr/bin/env python3
"""Outbound send-queue split (root / ctrl / gossip) + wait= semantics.

Ported from DUP experimental STRICT hardening. Unit scope only — acceptance for
P2P changes still requires the mesh probe + industrial gate (l1-mesh-integration-gate).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.p2p_node import (
    MSG_ATTESTATION,
    MSG_BLOCK,
    MSG_NEW_BLOCK,
    MSG_NEW_TX,
    MSG_PING,
    MSG_STATE_ROOT_REQUEST,
    MSG_STATE_ROOT_RESPONSE,
    MSG_STATUS,
    PeerConnection,
)


def _peer(qmax: int = 32) -> PeerConnection:
    peer = PeerConnection(send_queue_max=qmax, drain_timeout_sec=5.0)
    # No worker: tests inspect queue routing / drain order only.
    peer._ensure_send_worker = lambda: None  # type: ignore[method-assign]
    peer._send_wake = asyncio.Event()
    return peer


@pytest.mark.asyncio
async def test_send_routes_by_class():
    peer = _peer()
    assert await peer.send(MSG_STATE_ROOT_REQUEST, {"height": 1}) is True
    assert await peer.send(MSG_STATE_ROOT_RESPONSE, {"height": 1}) is True
    assert await peer.send(MSG_STATUS, {"height": 1}) is True
    assert await peer.send(MSG_BLOCK, {"height": 1}) is True
    assert await peer.send(MSG_NEW_BLOCK, {"height": 1}) is True
    assert await peer.send(MSG_ATTESTATION, {"x": 1}) is True
    assert await peer.send(MSG_NEW_TX, {"x": 1}) is True
    assert peer._send_root_q.qsize() == 2
    assert peer._send_ctrl_q.qsize() == 3
    assert peer._send_q.qsize() == 2


@pytest.mark.asyncio
async def test_state_root_send_enqueues_without_waiting_write():
    peer = _peer()
    t0 = time.monotonic()
    ok = await asyncio.wait_for(
        peer.send(MSG_STATE_ROOT_REQUEST, {"height": 1}), timeout=0.5
    )
    assert ok is True
    assert (time.monotonic() - t0) < 0.4
    item = peer._send_root_q.get_nowait()
    assert item[0] == MSG_STATE_ROOT_REQUEST
    assert item[1] == {"height": 1}
    assert item[2] is None  # wait=False: no write Future


@pytest.mark.asyncio
async def test_wait_true_attaches_future_and_times_out_without_worker():
    peer = _peer()
    peer._drain_timeout_sec = 0.5
    t0 = time.monotonic()
    ok = await peer.send(MSG_STATUS, {"height": 1}, wait=True)
    assert ok is False  # nobody drains -> bounded timeout, not a hang
    assert (time.monotonic() - t0) < 3.0
    assert peer._send_ctrl_q.get_nowait()[2] is not None


@pytest.mark.asyncio
async def test_next_outbound_priority_root_then_ctrl_then_gossip():
    peer = _peer()
    await peer.send(MSG_ATTESTATION, {"g": 1})
    await peer.send(MSG_STATUS, {"c": 1})
    await peer.send(MSG_STATE_ROOT_REQUEST, {"r": 1})
    order = [
        (await asyncio.wait_for(peer._next_outbound(), 0.5))[0] for _ in range(3)
    ]
    assert order == [MSG_STATE_ROOT_REQUEST, MSG_STATUS, MSG_ATTESTATION]


@pytest.mark.asyncio
async def test_next_outbound_wakes_on_enqueue():
    peer = _peer()
    getter = asyncio.create_task(peer._next_outbound())
    await asyncio.sleep(0.05)
    assert not getter.done()
    await peer.send(MSG_PING, {"ts": 1.0})
    item = await asyncio.wait_for(getter, 0.5)
    assert item[0] == MSG_PING


@pytest.mark.asyncio
async def test_gossip_full_drops_and_calls_hook_but_ctrl_full_warns(caplog):
    peer = _peer(qmax=8)
    drops: list = []
    peer._on_send_drop = lambda: drops.append(1)
    for _ in range(8):
        assert await peer.send(MSG_ATTESTATION, {"x": 1}) is True
    assert await peer.send(MSG_ATTESTATION, {"x": 1}) is False
    assert drops == [1]

    # ctrl queue is max(32, qmax): fill it; ctrl overflow warns, never calls drop hook.
    for _ in range(32):
        assert await peer.send(MSG_STATUS, {"x": 1}) is True
    with caplog.at_level(logging.WARNING, logger="P2P"):
        assert await peer.send(MSG_STATUS, {"x": 1}) is False
    assert drops == [1]
    assert "send queue full" in caplog.text


@pytest.mark.asyncio
async def test_worker_delivers_priority_first_and_wait_reports_result():
    peer = PeerConnection(send_queue_max=32, drain_timeout_sec=5.0)
    written: list = []

    async def _write(msg_type, data):
        written.append(msg_type)
        return True

    peer._write_message = _write  # type: ignore[method-assign]
    # Enqueue before the worker starts so ordering is queue-priority, not arrival.
    peer._send_q.put_nowait((MSG_ATTESTATION, {"g": 1}, None))
    peer._send_ctrl_q.put_nowait((MSG_STATUS, {"c": 1}, None))
    peer._send_root_q.put_nowait((MSG_STATE_ROOT_REQUEST, {"r": 1}, None))
    ok = await peer.send(MSG_PING, {"ts": 1.0}, wait=True)
    assert ok is True
    assert written[0] == MSG_STATE_ROOT_REQUEST
    assert set(written) == {
        MSG_STATE_ROOT_REQUEST,
        MSG_STATUS,
        MSG_ATTESTATION,
        MSG_PING,
    }
    peer.close()


@pytest.mark.asyncio
async def test_root_timeout_retry_tuple_is_writable_and_bounded():
    """A re-queued root frame carries a 4th ``tries`` field; batch writers must cope."""
    peer = PeerConnection(send_queue_max=32, drain_timeout_sec=5.0)
    calls: list = []

    async def _write(msg_type, data):
        calls.append((msg_type, data))
        return True

    peer._write_message = _write  # type: ignore[method-assign]
    fut = asyncio.get_running_loop().create_future()
    out = await peer._write_messages_batch(
        [(MSG_STATE_ROOT_REQUEST, {"height": 3}, fut, 1)]
    )
    assert out == [True]
    out = await peer._write_messages_batch(
        [
            (MSG_STATE_ROOT_REQUEST, {"height": 3}, fut, 1),
            (MSG_STATUS, {"height": 3}, None),
        ]
    )
    assert out == [True, True]
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_worker_requeues_state_root_on_timeout_at_most_twice():
    peer = PeerConnection(send_queue_max=32, drain_timeout_sec=5.0)
    attempts: list = []

    async def _timeout(_batch):
        attempts.append(1)
        raise asyncio.TimeoutError()

    peer._write_messages_batch = _timeout  # type: ignore[method-assign]
    fails: list = []
    peer._on_send_fail = lambda: fails.append(1)
    peer._send_root_q.put_nowait((MSG_STATE_ROOT_REQUEST, {"height": 1}, None))
    peer._ensure_send_worker()
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and len(attempts) < 3:
        await asyncio.sleep(0.02)
    await asyncio.sleep(0.2)
    assert len(attempts) == 3  # first try + 2 bounded retries
    assert len(fails) == 3
    peer.close()


def test_close_wakes_all_queues_and_logs_failure(caplog):
    class _BoomQ:
        def put_nowait(self, _item):
            raise RuntimeError("q full")

    peer = PeerConnection(None, None)
    peer._send_q = _BoomQ()  # type: ignore[assignment]
    with caplog.at_level(logging.DEBUG, logger="P2P"):
        peer.close()
    assert "close send_q wake failed" in caplog.text
    assert peer._send_ctrl_q.get_nowait() is None
    assert peer._send_root_q.get_nowait() is None


def test_needles():
    p2p = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    for needle in (
        "_send_ctrl_q",
        "_send_root_q",
        "def _next_outbound",
        "def _outbound_queues",
        "def _wake_send",
        "state_root enqueue does not wait the write Future",
        "wait: bool = False",
    ):
        assert needle in p2p, needle
