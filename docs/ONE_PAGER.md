# DUP Protocol — one-pager (EN) · industrial pin

**DUP Labs** · **DUP Protocol** · Uladzimir Dabranski (D.U.P.)  
**Date:** 2026-10-07 · Full path: [SHOWCASE.md](SHOWCASE.md) · RU: [ONE_PAGER_RU.md](ONE_PAGER_RU.md)  
**Repo:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)

---

## One sentence

**DUP Protocol** is an industrial **hybrid L1** (Python + Rust) with a fail-closed private prod-profile mesh, satoshi-honest money, and on-disk soak evidence — split into an **audit-freeze pin** and an **R&D sandbox**.

---

## Architecture (one line)

`API / RPC → Core + Mempool → Consensus / P2P / Sync → Storage / Rocks → abs_native (Rust)`

Working-tip pin mesh: **rust-libp2p** (ADR 0020). Freeze tag soak: **TCP+TLS**. Money: **satoshi integers**.

---

## Two repos

| | Pin (this tree) | Experimental |
|---|-----|----------------|
| GitHub | [`dup-protocol`](https://github.com/Gruver87/dup-protocol) | [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental) |
| Role | Audit freeze + working tip | libp2p / LR lab / EVM depth / mempool Rust |
| Show | Tip-v2 soak [`375d14f`](evidence/runs/375d14f/) · ADR 0020 Quick [`pin-libp2p-cutover-pending`](evidence/runs/pin-libp2p-cutover-pending/) | STRICT packs on Exp only |

---

## Evidence scoreboard (pin)

| Pack / claim | Proves |
|--------------|--------|
| Tag `v1.3.1339-tip-v2-industrial` · [`375d14f`](evidence/runs/375d14f/) | Historical **TCP+TLS** tip-v2 48h soak (`passed=true`, `hard_fails=0`) |
| [`pin-libp2p-cutover-pending`](evidence/runs/pin-libp2p-cutover-pending/) | ADR 0020 mesh JSON cutover + **Quick** probe — **not** 48h soak |
| Bridge OFF | `verify_bridge_off_lab.ps1` + gate |
| Exp→pin merge waves | Units + `industrial_gate` on pin HEAD — see [FUND_READINESS.md](FUND_READINESS.md) |

Experimental STRICT / Long-Range / EVM depth soaks: cite **only** on Experimental. Detail: [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md) · [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md).

---

## Ask

Technical diligence / grant / ПВТ review of the **private mesh + on-disk evidence** — not a token listing, not “mainnet ready.”

Live demo: [DEMO_RUNBOOK_PIN.md](DEMO_RUNBOOK_PIN.md). FAQ: [FAQ.md](FAQ.md).

---

## Forbidden

Public audited mainnet · soak without pack id · Quick ≠ soak · pin libp2p 48h PASS (deferred) · prod Long-Range · bridge ON · ERC-721 parity · inventing company email / TM registration · citing Exp STRICT packs as pin evidence.
