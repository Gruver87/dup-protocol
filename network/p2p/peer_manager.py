# -*- coding: utf-8 -*-
"""Shim → ``network.legacy_test_p2p.peer_manager`` (Phase D quarantine)."""
from __future__ import annotations

import warnings

warnings.warn(
    "network.p2p.peer_manager is legacy-test-only; import network.legacy_test_p2p.peer_manager",
    DeprecationWarning,
    stacklevel=2,
)

from network.legacy_test_p2p.peer_manager import *  # noqa: F401,F403
