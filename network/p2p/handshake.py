# -*- coding: utf-8 -*-
"""Shim → ``network.legacy_test_p2p.handshake`` (Phase D quarantine)."""
from __future__ import annotations

import warnings

warnings.warn(
    "network.p2p.handshake is legacy-test-only; import network.legacy_test_p2p.handshake",
    DeprecationWarning,
    stacklevel=2,
)

from network.legacy_test_p2p.handshake import *  # noqa: F401,F403
