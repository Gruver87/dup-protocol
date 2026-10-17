# Pin libp2p STRICT 48h soak — PASS

**Kind:** ADR 0020 industrial mesh soak  
**Status:** **PASS** on this host. Not public mainnet. Tag `v1.3.1340-libp2p-industrial-mesh` is **not cut**.  
**Window:** 2026-10-15 20:27:58+03 through 2026-10-17 20:28:00+03 (`hours_elapsed=48.0007`).  
**Chain:** prod-profile `778888` · rust-libp2p (`feature_libp2p=true`, `p2p_tls_enabled=false`).

## Report

| Field | Value |
|-------|--------|
| `passed` | true |
| `strict` | true |
| `hard_fail_lines` | 0 |
| `mesh_warn_lines` | 0 |
| `fail_lines` | 0 |
| `health_watch_exit` | 0 |
| `mesh_ok_lines` | 2802 |
| `warn_lines` | 9 |
| max gap between mesh lines | 87s (2026-10-17 13:28:15) |
| git_sha at start | `c1c281f41d6710e3c008b223f499542012ef9a0b` |
| git_dirty at start | true (host scripts not in that commit) |
| image | `sha256:be576392c01f2ba22bebebef1e4e486b7106ae373ebbbd3dedf1be5265bfa908` |

The nine warnings are `WARN OK port` lines on 2026-10-17 13:25–13:31 (a peer count of 1, then `tip_lagging` / `ready_flap`). Mesh lines stayed `OK mesh aligned`. STRICT scores `mesh_warn` only on `WARN mesh misaligned`, and there were none.

## Files

- [`soak_report_48h_libp2p_strict.json`](soak_report_48h_libp2p_strict.json)
- [`soak_48h_libp2p_strict.log`](soak_48h_libp2p_strict.log)

## Not this pack

- 2026-10-08 power-off attempt stays **VOID** (`pin-libp2p-cutover-pending`) — not PASS.
- 2026-10-11 10:39+03 window stopped 2026-10-13 06:51+03 after 44.2h — not PASS.
- Freeze tag `v1.3.1339-tip-v2-industrial` stays **TCP+TLS** historical evidence.
- Experimental soak packs are not pin evidence.
