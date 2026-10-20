# Pin libp2p STRICT 48h soak — PASS (historical dirty git)

**Kind:** ADR 0020 industrial mesh soak (archived)  
**Status:** **PASS** on this host. Not public mainnet.  
**Window:** 2026-10-15 20:27:58+03 through 2026-10-17 20:28:00+03 (`hours_elapsed=48.0007`).  
**Honesty:** `git_dirty=true` at start (`c1c281f`). Image was reused (`-SkipRebuild`): `sha256:be576392…`.

## Primary pack

The clean-commit STRICT PASS is [`../pin-libp2p-strict-48h/`](../pin-libp2p-strict-48h/) (2026-10-18 → 2026-10-20, `c5ac635c`, `git_dirty=false`). Prefer that folder for diligence. This archive stays so the dirty window is not rewritten away.

## Report (this archive)

| Field | Value |
|-------|--------|
| `passed` | true |
| `hard_fail_lines` | 0 |
| `mesh_warn_lines` | 0 |
| `warn_lines` | 9 |
| git_sha at start | `c1c281f41d6710e3c008b223f499542012ef9a0b` |
| git_dirty at start | true |
| image | `sha256:be576392c01f2ba22bebebef1e4e486b7106ae373ebbbd3dedf1be5265bfa908` |

## Files

- [`soak_report_48h_libp2p_strict.json`](soak_report_48h_libp2p_strict.json)
- [`soak_48h_libp2p_strict.log`](soak_48h_libp2p_strict.log)
