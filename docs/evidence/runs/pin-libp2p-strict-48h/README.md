# Pin libp2p STRICT 48h soak — PASS (clean commit)

**Kind:** ADR 0020 industrial mesh soak  
**Status:** **PASS** on this host. Not public mainnet.  
**Release tag:** [`v1.3.1340-libp2p-industrial-mesh`](https://github.com/Gruver87/dup-protocol/releases/tag/v1.3.1340-libp2p-industrial-mesh)  
**Window:** 2026-10-18 09:59:31+03 through 2026-10-20 09:59:33+03 (`hours_elapsed=48.0004`).  
**Chain:** prod-profile `778888` · rust-libp2p (`feature_libp2p=true`, `p2p_tls_enabled=false`).

## Report

| Field | Value |
|-------|--------|
| `passed` | true |
| `strict` | true |
| `hard_fail_lines` | 0 |
| `mesh_warn_lines` | 0 |
| `fail_lines` | 0 |
| `warn_lines` | 0 |
| `health_watch_exit` | 0 |
| `mesh_ok_lines` | 2802 |
| `cycles_observed` | 2802 |
| git_sha at start | `c5ac635c55187b904cf1caed97ebdc165b443753` |
| git_dirty at start | **false** |
| image | `sha256:83d7e19ef3e9632e79ac04f27bd8651f550f0d4607306f69c82a2b034f1f922e` |

Final mesh line: height **49124**, peers=2 on all three nodes, `OK mesh aligned`. Volumes were kept (`-KeepVolumes`); tip continued from the preserved RocksDB chain (not height 0). That is expected and does not invalidate the window.

## Files

- [`soak_report_48h_libp2p_strict.json`](soak_report_48h_libp2p_strict.json)
- [`soak_48h_libp2p_strict.log`](soak_48h_libp2p_strict.log)
- [`soak_48h_prep.json`](soak_48h_prep.json) — prep meta (`git_dirty=false`, image pin)

## Prior dirty window (archived)

The earlier STRICT PASS 2026-10-15–17 (`git_sha=c1c281f`, `git_dirty=true`, image `sha256:be576392…`) remains on disk as historical evidence under [`../pin-libp2p-strict-48h-dirty-c1c281f/`](../pin-libp2p-strict-48h-dirty-c1c281f/). This folder is the **clean-commit** primary pack.

## Not this pack

- 2026-10-08 power-off attempt stays **VOID** (`pin-libp2p-cutover-pending`) — not PASS.
- 2026-10-11 10:39+03 window stopped 2026-10-13 06:51+03 after 44.2h — not PASS.
- Freeze tag `v1.3.1339-tip-v2-industrial` stays **TCP+TLS** historical evidence.
- Experimental soak packs are not pin evidence.
- Public mainnet is **not** claimed by this tag.
