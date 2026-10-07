# -*- coding: utf-8 -*-
"""P2P package — industrial node runtime (+ legacy-test shims under this tree).

Industrial plane: ``network.p2p_node`` / ``network.p2p_dispatch``.
Modules ``handshake`` / ``messages`` / ``peer_manager`` / ``discovery`` /
``message_handler`` are **legacy-test-only** shims → ``network.legacy_test_p2p``.
"""
from network.p2p_node import P2PNode

__all__ = ["P2PNode"]
