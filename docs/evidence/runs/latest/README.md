# `latest/` — pointer only (not current HEAD evidence)

**Do not treat this directory name as “current soak / current mesh proof.”**

`manifest.json` here is a **historical pointer** into the tip-v2 TCP+TLS pack
[`../375d14f/`](../375d14f/) (freeze tag `v1.3.1339-tip-v2-industrial`).
`probe_log` in that manifest is intentionally `missing` for this thin pointer.

| Need | Open |
|------|------|
| Tip-v2 48h PASS (TCP+TLS) | [`../375d14f/`](../375d14f/) |
| ADR 0020 cutover + Quick + VOID libp2p | [`../pin-libp2p-cutover-pending/`](../pin-libp2p-cutover-pending/) |
| Fund / audit front door | [`../../FUND_AUDIT_PREP.md`](../../FUND_AUDIT_PREP.md) |

Working tip / HEAD claims require a new pack under `docs/evidence/runs/<id>/`
plus matrix sync — not this folder rename.
