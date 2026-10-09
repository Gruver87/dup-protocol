# ADR 0020 — libp2p industrial mesh cutover (pin)

- **Status:** Accepted (pin industrial mesh cutover; Quick probe PASS packaged; 48h mesh soak on pin **VOID** 2026-10-08 · not PASS)
- **Date:** 2026-08-22 (Experimental); rebound to pin 2026-10-05
- **Deciders:** DUP Labs maintainers
- **Supersedes (this tree):** ADR 0018 §5 and ADR 0019 industrial JSON freeze
  (`feature_libp2p=false` on `778888` prod-profile mesh).
- **Applies to:** pin industrial prod-profile 3-node mesh
  (`docker/node.prod.mesh{1,2,3}.json`, `docker-compose.prod.3node.yml`).
- **Historical (unchanged):** freeze tag `v1.3.1339-tip-v2-industrial` remains the
  **TCP+TLS/mTLS** audit-freeze. Its evidence packs are TCP+TLS evidence and must
  not be relabeled as libp2p.

## Context

The pin prod-profile mesh (`chain_id` `778888`) shipped native TCP+TLS/mTLS
through `v1.3.1339-tip-v2-industrial`. Pin **TCP+TLS** 48h soak **PASS** for
tip-v2 is `docs/evidence/runs/375d14f/` (freeze tag evidence). Experimental
TCP+TLS pack `0a7932c4` is **not** pin evidence.

ADR 0018/0019 built rust-libp2p (Noise/Yamux + `/abs/wire`) behind
`FEATURE_LIBP2P`, but the live `P2PNode` path still bound `P2PNativeListener`.
Labs A–DB and `verify_adr0019_libp2p_hard` are not a live L1 mesh.

Experimental completed the cutover and a libp2p 48h soak
([`gruver87/dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental),
pack `3c801b87`, `passed=true`, `hard_fails=0`, window 2026-09-01→03). That
pack is **Experimental** evidence; it is not pin evidence.

## Decision

1. The pin industrial 3-node mesh uses **rust-libp2p** as the data-plane
   transport (Noise XX + Yamux + ADR 0008 `/abs/wire`).
2. Transports are **mutually exclusive**: `feature_libp2p=true` requires
   `p2p_tls_enabled=false`; `p2p_tls_enabled=true` requires
   `feature_libp2p=false`. Config refuses both-true.
3. `docker/node.prod.json` (single node) and the `p2ptls` compose overlays remain
   the **TCP+TLS alternate** (`feature_libp2p=false`, `p2p_tls_enabled=true`).
4. A libp2p industrial PASS **on the pin** needs its own 48h soak after this
   cutover (`passed=true`, `hard_fails=0`, `hours_elapsed>=48`), packaged under
   `docs/evidence/runs/<image>/`. Quick probe PASS is packaged under
   `pin-libp2p-cutover-pending/`; STRICT attempt **VOID** (host power-off
   2026-10-08 — not PASS · not restarted). Do not cite `3c801b87` or
   `0a7932c4` as pin libp2p soak.
5. Session crypto on the mesh is **Noise**. Native mTLS overlay
   (`docker-compose.prod.3node.p2ptls.yml`) is not the default for this mesh.
6. `feature_long_range` (ADR 0017) and `bridge_enabled` stay **false**.
7. Application admit/dispatch stays above transport (ADR 0002 / 0008):
   `p2p_dispatch`, tip-safety, state-root gates.

## Fail-closed invariant

When `feature_libp2p=true`:

- Boot **refuses** if `abs_native.libp2p_available()` is false.
- **No** silent fallback to TCP+TLS (that would paint a green mesh that is
  still native).
- Do **not** run `P2PNativeListener` and libp2p forge in parallel (split-brain).
- Prepare-fail on egress is HARD REFUSE (`send_abs_wire` does not encode around
  admit). Inbound garbage is REFUSE, not dispatch.

## Consequences

- Prod Config no longer unconditionally clears `feature_libp2p`; JSON/env may
  enable it. `feature_long_range` remains hard-off in prod.
- `docker/node.prod.mesh{1,2,3}.json` set `feature_libp2p: true`,
  `p2p_tls_enabled: false`.
- `Dockerfile.prod` and `scripts/build_native.ps1` build `abs_native` with Cargo
  feature `libp2p`.
- `scripts/industrial_gate.py` requires mesh JSON `feature_libp2p=true`, TLS off,
  and the ADR 0020 honesty surfaces in `p2p_node.py` / `api/http.py`.
- `scripts/docker_prod_3node.ps1` refuses `-P2pTls` for this mesh profile and
  asserts `/status.libp2p.active` with the rust backend.
- Tag `v1.3.1339-tip-v2-industrial` stays the historical TCP+TLS freeze; it is
  not retagged by this ADR.
