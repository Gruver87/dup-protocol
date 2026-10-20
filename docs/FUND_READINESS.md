# Fund / diligence readiness — DUP Protocol industrial pin (honest)

**Audience:** grant officers, investors, HTP / ПВТ reviewers, technical advisors.  
**Date:** 2026-10-09 · Repo: [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol) · branch `master`  
**Front door:** [FUND_AUDIT_PREP.md](FUND_AUDIT_PREP.md)  
**Brand:** [BRAND.md](BRAND.md) — **DUP Labs** · **DUP Protocol** · Uladzimir Dabranski (D.U.P.)  
**Not:** public audited mainnet · not listed token · not Experimental Long-Range / Exp soak packs as pin evidence.  
**Former folder name:** Absolute_Blockchain_Ultimate_Hybrid (path only).

**Showcase:** [SHOWCASE.md](SHOWCASE.md)  
**Operator pack:** [FUND_DEMO_OPERATOR_PACK.md](FUND_DEMO_OPERATOR_PACK.md)  
**15-minute brief:** [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md)  
**Evidence ledger:** [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md) · **Gaps:** [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)  
**R&D sibling (not pin evidence):** [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental)

---

## What this is

Industrial **private-testnet / firm-engagement** hybrid L1 (Python orchestration + Rust/PyO3 hot path).  
**Working-tip prod 3-node mesh** uses **rust-libp2p** (ADR 0020). Freeze tag `v1.3.1339-tip-v2-industrial` is **historical TCP+TLS** soak evidence. Pin libp2p STRICT attempt **VOID** (host power-off 2026-10-08); soak **STRICT 2026-10-11 10:39+03 stopped short after 44.2h (not PASS). STRICT 2026-10-15–17 PASS on dirty git (archived `pin-libp2p-strict-48h-dirty-c1c281f`). STRICT 2026-10-18 09:59+03 through 2026-10-20 09:59+03 PASS (passed=true, hard_fails=0, mesh_warn=0, warn_lines=0, 48.0004h; pack pin-libp2p-strict-48h; git `c5ac635c` clean; tagged `v1.3.1340-libp2p-industrial-mesh`; not mainnet)**.

---

## What we claim (with pin evidence)

| Claim | Evidence |
|-------|----------|
| Tip-v2 industrial freeze + TCP+TLS 48h soak | tag `v1.3.1339-tip-v2-industrial` · pack `375d14f` era — see [EVIDENCE_MATRIX](EVIDENCE_MATRIX.md) |
| ADR 0020 mesh JSON cutover + Quick probe | `docs/evidence/runs/pin-libp2p-cutover-pending/` — Quick PASS; **not** 48h soak |
| Fail-closed satoshi / RPC / sprout honesty | Exp→pin merge waves CLOSED on pin HEAD — units + `industrial_gate` |
| Bridge OFF on live mesh | `bridge_off_audit_gate` + `verify_bridge_off_lab.ps1` |
| Phase-5 aux sprout labs (offline) | `verify_sprout_labs.ps1` (oracle / cross-shard / NFT / AI) — flags stay false on 778888 |

### STRICT / Exp soak scoreboard

Experimental STRICT / Long-Range / EVM depth soak packs live **only** on [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental). **Do not cite them as pin industrial evidence.**

---

## What we do **not** claim

- Public mainnet / external firm security audit PDF complete
- The 2026-10-08 VOID window and the 2026-10-11 short window as soak PASS
- Tag `v1.3.1340-libp2p-industrial-mesh` (cut; not public mainnet)  
- Long-Range production / BLS (`feature_long_range=false` in prod JSON)  
- Bridge L1 lock/mint contracts live  
- NIST PQ signature backends (correct `NotImplemented`)  
- Experimental soaks as pin packs  

---

## Architecture (diligence map)

```text
API / JSON-RPC / WebSocket  →  Core + Mempool  →  Consensus / P2P / Sync
                                      ↓
                              StoragePort / Rocks
                                      ↓
                              abs_native (Rust PyO3)
```

ADRs: 0001 tip-safety · 0009 hybrid · 0015 secrets · 0016 profiles · 0017 Long-Range (lab-only / refuse on pin) · 0020 libp2p mesh · 0021 money/mempool satoshi.

---

## Pre-meeting checklist (code side)

| Item | Status |
|------|--------|
| Fail-closed money (satoshi) + wire refuse float-only | Done — units + gate |
| Tip-safety / ancestry window (not WS checkpoints) | Done — ADR 0001 |
| Bridge OFF defaults + audit gate | Done |
| Sprout labs verify (oracle/shard/NFT/AI) | Done — `verify_sprout_labs.ps1` |
| Industrial HIGH honesty / industrial_gate | Done |
| Fresh 48h soak on current HEAD (libp2p) | **PASS** 2026-10-18–20 (`hard_fails=0`, `warn_lines=0`, clean git `c5ac635c`, [`pin-libp2p-strict-48h`](evidence/runs/pin-libp2p-strict-48h/), tag `v1.3.1340-libp2p-industrial-mesh`). Prior dirty 2026-10-15–17 archived. 2026-10-08 **VOID** (not PASS) — [`SOAK_VOID_HOST_POWEROFF_2026-10-08.txt`](evidence/runs/pin-libp2p-cutover-pending/SOAK_VOID_HOST_POWEROFF_2026-10-08.txt). 2026-10-11 short window not PASS. Not mainnet. |
| External audit / secrets rotate / validator ceremony live | Org Phase 6 |

---

## Recommended diligence path (60 minutes)

1. Read [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md) + this page  
2. Skim [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md) — open freeze tag pack + cutover-pending README  
3. Operator verify: [VERIFY_SUITE.md](VERIFY_SUITE.md) (`verify_project` / `verify_sprout_labs`)  
4. Optional live: `.\scripts\probe_prod_mesh.ps1 -Quick` if mesh already up  
5. Gaps first: [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)

**Bottom line:** ready for **technical diligence on an industrial private mesh**. Pin libp2p STRICT 48h **PASS** is packaged on clean HEAD (`pin-libp2p-strict-48h`). Not ready to claim **public audited mainnet**.
