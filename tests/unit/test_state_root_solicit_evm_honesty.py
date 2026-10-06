"""State-root solicit height + EVM API honesty (Exp→pin)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def test_state_root_solicit_height_asks_local_tip_not_stale_peer():
    from network.p2p_node import P2PNode

    node = object.__new__(P2PNode)
    node.blockchain = SimpleNamespace(get_height=lambda: 42)
    peer = SimpleNamespace(height=10, peer_id="p1")
    assert node._state_root_solicit_height(peer, None) == 42
    assert node._state_root_solicit_height(peer, 7) == 7
    assert node._state_root_solicit_height(peer, -3) == 0


def test_validate_bytecode_unavailable_is_503_not_invalid(monkeypatch):
    """Import/probe failure must not paint valid=false."""
    import api.http as http_mod

    src = (http_mod.__file__ and open(http_mod.__file__, encoding="utf-8").read()) or ""
    chunk = src.split('path == "/evm/validate-bytecode"')[1].split(
        'path == "/contract/deploy"'
    )[0]
    assert "bytecode validation unavailable" in chunk
    assert 'self._json({"valid": False' not in chunk
    assert "503" in chunk


def test_supported_opcodes_uses_merge_compat_summary():
    import api.http as http_mod

    src = open(http_mod.__file__, encoding="utf-8").read()
    chunk = src.split('path == "/evm/supported-opcodes"')[1].split(
        'path == "/evm/status"'
    )[0]
    assert "merge_compat_summary" in chunk
    assert "supported_opcodes_summary()" in chunk
