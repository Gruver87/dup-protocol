# `latest/` — pointer only (not current HEAD evidence)

**Do not treat this directory name as “current soak / current mesh proof.”**

`manifest.json` here is a **historical pointer** into the tip-v2 TCP+TLS pack
[`../375d14f/`](../375d14f/) (freeze tag `v1.3.1339-tip-v2-industrial`).
`probe_log` in that manifest is intentionally `missing` for this thin pointer.

| Need | Open |
|------|------|
| Tip-v2 48h PASS (TCP+TLS) | [`../375d14f/`](../375d14f/) |
| libp2p STRICT 48h PASS clean (2026-10-18–20) | [`../pin-libp2p-strict-48h/`](../pin-libp2p-strict-48h/) |
| libp2p STRICT 48h PASS dirty archive (2026-10-15–17) | [`../pin-libp2p-strict-48h-dirty-c1c281f/`](../pin-libp2p-strict-48h-dirty-c1c281f/) |
| ADR 0020 cutover + Quick + VOID libp2p | [`../pin-libp2p-cutover-pending/`](../pin-libp2p-cutover-pending/) |
| Fund / audit front door | [`../../FUND_AUDIT_PREP.md`](../../FUND_AUDIT_PREP.md) |

The primary libp2p STRICT 48h PASS is [`../pin-libp2p-strict-48h/`](../pin-libp2p-strict-48h/) (clean `c5ac635c`).
This folder stays the tip-v2 pointer. Do not rename it into that pack.
