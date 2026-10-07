# -*- coding: utf-8 -*-
"""LEGACY TEST-ONLY P2P helpers (Phase D quarantine).

Industrial mesh uses ``network.p2p_node`` / ``network.p2p_dispatch``.
These modules exist for ``tests/legacy`` and historical unit fixtures only.
Do not wire into prod NodeOrchestrator or tip-v2 paths.
"""

from __future__ import annotations

LEGACY_TEST_ONLY = True

__all__ = ["LEGACY_TEST_ONLY"]
