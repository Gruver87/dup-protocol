# Legacy network quarantine (Phase D3) — industrial pin

**Industrial plane (do use):**

| Role | Module |
|------|--------|
| P2P node / mesh | `network.p2p_node`, `network.p2p_dispatch`, `network.p2p_tls` (or ADR 0020 libp2p path when armed) |
| Sync / catch-up | `sync.sync_engine`, `sync.catchup` |

**Legacy test-only (do not wire into prod):**

| Old import (shim) | Canonical |
|-------------------|-----------|
| `network.p2p.handshake` / `messages` / `peer_manager` / `discovery` / `message_handler` | `network.legacy_test_p2p.*` |
| `network.sync.fast_sync` | `network.sync.legacy_test_fast_sync` (if present) |
| `network.sync.sync_manager` | `network.sync.legacy_test_sync_manager` (if present) |

Shims emit `DeprecationWarning` and re-export. New tests must import the
`legacy_test_*` paths. Tip-v2 / mempool / prod mesh must not construct these
managers.
