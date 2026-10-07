#!/usr/bin/env python3
"""Phase D: legacy P2P helpers live under network.legacy_test_p2p only."""

from pathlib import Path


def test_legacy_package_exports_message_handler():
    from network.legacy_test_p2p.message_handler import MessageHandler

    assert MessageHandler is not None
    assert hasattr(MessageHandler, "_send")


def test_p2p_package_shims_to_legacy():
    shim = Path("network/p2p/message_handler.py").read_text(encoding="utf-8")
    assert "network.legacy_test_p2p.message_handler" in shim
    assert "DeprecationWarning" in shim
    body = Path("network/legacy_test_p2p/message_handler.py").read_text(encoding="utf-8")
    assert "_send_failures" in body
    assert "[MessageHandler]" in body
    assert "failed peer=" in body


def test_consensus_adapter_logger_no_print_no_lr():
    src = Path("consensus/adapter.py").read_text(encoding="utf-8")
    assert "print(" not in src
    assert 'logger.warning(f"[Consensus] FAIL: engine slash' in src
    assert "from consensus.long_range" not in src
    assert '"long_range_defense": False' in src
