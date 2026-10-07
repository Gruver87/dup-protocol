# -*- coding: utf-8 -*-
"""Shim → ``network.legacy_test_p2p.message_handler`` (Phase D quarantine)."""
from __future__ import annotations

import warnings

warnings.warn(
    "network.p2p.message_handler is legacy-test-only; "
    "import network.legacy_test_p2p.message_handler",
    DeprecationWarning,
    stacklevel=2,
)

from network.legacy_test_p2p.message_handler import *  # noqa: F401,F403
