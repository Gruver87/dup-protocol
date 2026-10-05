#!/usr/bin/env python3
"""Fail-closed parent lookup: store errors refuse, not soft-skip."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.p2p_node import P2PNode
from runtime.config import Config


def _node() -> P2PNode:
    cfg = Config()
    cfg.p2p_native_transport = False
    cfg.require_native_crypto = False
    cfg.deployment_mode = "dev"
    cfg.bootstrap_peers = []
    chain = MagicMock()
    chain.get_height.return_value = 10
    chain.get_last_block.return_value = {"hash": "ab" * 32, "height": 10}
    node = P2PNode(cfg, chain, MagicMock())
    return node


def test_try_expected_parent_ok():
    node = _node()
    node._expected_parent_for_height = MagicMock(return_value="cd" * 32)  # type: ignore
    parent, reason = node._try_expected_parent(10)
    assert parent == "cd" * 32
    assert reason == ""


def test_try_expected_parent_unreadable():
    node = _node()

    def _boom(_h):
        raise RuntimeError("store down")

    node._expected_parent_for_height = _boom  # type: ignore
    parent, reason = node._try_expected_parent(10)
    assert parent is None
    assert reason == "local_parent_unreadable"


def test_same_height_parent_refuse_on_unreadable():
    node = _node()

    def _boom(_h):
        raise RuntimeError("store down")

    node._expected_parent_for_height = _boom  # type: ignore
    block = MagicMock()
    block.height = 10
    block.hash = "ee" * 32
    block.parent_hash = "ff" * 32
    reason = node._new_block_same_height_parent_refuse_reason(block, 10)
    assert reason == "local_parent_unreadable"
