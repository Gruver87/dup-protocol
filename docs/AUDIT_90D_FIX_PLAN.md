# Audit → 90-day fix plan — industrial pin (honest)

**Repo:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**Rule:** nothing that breaks tip-v2 evidence packs, money satoshi, tip-safety, or prod mesh JSON.  
**Soak:** new 48h soaks stay on the shelf unless a hot-path money/P2P/consensus change requires re-proof.  
**R&D sequence (Experimental):** see [EXECUTION_ORDER on Exp](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/EXECUTION_ORDER.md) — **not** pin evidence.

---

## Safety ladder (always)

```text
1. Honesty / docs / labels          ← no consensus break
2. Quarantine / UI / refuse APIs    ← fail-closed, tests update
3. Additive satoshi ports           ← float display only at REST
4. Behavior harden under flags      ← require_native refuse, etc.
5. Breaking remap / revm            ← ONLY with migration ADR + lab
```

**Forbidden in this window:** Great Merge · bridge ON on live mesh · prod Long-Range · silent opcode remap without ADR.

---

## Pin status (2026-10-07)

| Track | Status |
|-------|--------|
| Honesty / satoshi / RPC / health | **CLOSED** via Exp→pin merge waves — [EVIDENCE_MATRIX](EVIDENCE_MATRIX.md) |
| Bridge OFF audit | **CLOSED** — `verify_bridge_off_lab.ps1` |
| Phase-5 sprout labs (offline) | **CLOSED** — `verify_sprout_labs.ps1` |
| ADR 0020 libp2p mesh JSON + Quick probe | **Packaged** — 2026-10-08 soak **VOID** (not PASS); STRICT 2026-10-15–17 **PASS** (`pin-libp2p-strict-48h`, tag not cut) |
| External firm audit PDF / pen-test | **Org Phase 6** — [FIRM_KICKOFF_CHECKLIST](FIRM_KICKOFF_CHECKLIST.md) |
| Fresh pin libp2p 48h soak | **PASS** 2026-10-15–17 (`pin-libp2p-strict-48h`). Another run only for a clean-commit image bind |

Detailed A–H remediation history for Experimental mid-2026 lives on the Exp tree; this pin tracks **industrial engagement**, not Exp R&D phase letters.

---

## Layer bring-up (after the Exp port, 2026-10-17)

Code for libp2p, EVM, mempool validation, Long-Range, and the council NFT gate is on this pin. Bring-up does not flip prod JSON and does not start a soak.

1. **Lock** — prod `778888` keeps `feature_long_range=false`, `feature_nft=false`, bridge OFF. Long-Range lab profile stays `deployment_mode=dev`, chain `77779`. Gate refuses a lab file that uses `778888`.
2. **Long-Range lab only** — `python scripts/verify_long_range_host.py` runs the three offline labs and checks prod JSON. Committee keys for a later window are already in gitignored `data/long_range_lab_committee/` (3 members, threshold 2). Compose needs `node.long_range.lab.json`, `lab1`, and `lab2`. Do not start `abs-lr-lab` or a soak until that window is ordered. BLS is not in this step.
3. **NFT and council** — `.\scripts\verify_nft_marketplace.ps1 -SkipStaging` re-ran marketplace units and `nft_lab.py` (mint, list, buy, offer, auction, soft escrow). `guarantor_council_lab.py` re-ran the 87-token council. `feature_nft` stays false on prod mesh. Staging `:19080` was closed, so no mint. Not ERC-721. Not L1 security.
4. **EVM and mempool host, mesh unchanged** — `.\scripts\verify_evm_depth_lab.ps1` (no `-WithMesh`) re-ran the six EVM labs, focused units, and `industrial_gate`. CALL / precompiles / host CREATE2 stay **Partial** in `docs/sprouts/EVM_COMPAT_MATRIX.md`. `python scripts/verify_adr0021_phase1.py --require-rust --skip-mesh` re-ran PASS: Rust `mempool_kernel` and `mempool_store`, goldens for accept / nonce / balance / bad deploy, fee sort. Neither starts a soak or requires ports `18180–18182`. Experimental `evm48pass1` / `mempool48pass1` are not pin evidence. Live mesh smoke and `start_soak_evm_mesh_48h_strict.ps1` wait until that window is ordered.
5. **Sprout host** — `.\scripts\verify_sprout_labs.ps1` covers bridge OFF, oracle, cross-shard, NFT, and AI offline. Prod flags for those sprouts stay false. It does not start a soak or a shard docker mesh.
5c. **Cross-chain bridge** — `.\scripts\verify_bridge_off_lab.ps1` re-ran PASS (3/3): audit gate, mesh `bridge_enabled=false`, compose default false. Offline bridge units 89 passed (satoshi, lock/burn refuse, incoming). Not an L1 cutover. Live relayer and `bridge_enabled=true` stay off until a later audited window.
5d. **Sharding** — `.\scripts\verify_cross_shard_lab.ps1` re-ran PASS (3/3): cross-shard ACK, quorum, insufficient-balance refuse. Prod mesh `feature_sharding=false`. A later operator start of `start_shard_devnet.ps1` is a dev lab on `:8080`/`:8081`, not a prod arm.
5e. **Oracles** — `.\scripts\verify_oracle_lab.ps1` re-ran PASS (4/4): HMAC, quorum, dedupe, stale and deviation refuse. Prod mesh `feature_oracles=false`.
5f. **AI** — `python scripts/ai_lab.py` and `python scripts/ai_ops_anomaly.py --offline-only` re-ran PASS. Agents, model port, validator `simulation_only`, MEV, anomaly classifier. Prod mesh keeps `feature_ai_agents`, `feature_ai_validator`, and `feature_mev` false. Not consensus.
5b. **High honesty** — `.\scripts\verify_industrial_high_honesty.ps1` checks slash fail-closed, mempool demote under `require_native`, bridge emit errors, and `libp2p_lab_smoke.py` (dial refuse). It does not probe the live mesh.
6. **Security honesty** — `python scripts/verify_security_honesty.py` checks harness peer-match, testnet/TLS/probe needles, and the unit slice. It does not start a soak. The 2026-10-08 VOID file is only a presence check.
7. **Daily Quick** — `.\scripts\check_all.ps1 -Mode Quick` is waves + `industrial_gate` + ceremony status. It does not start a node. Ceremony `ready=false` until a real pin is set. `-Mode Live` auto-starts `main.py` and is not this step.
8. **Standard and Max** — `.\scripts\check_all.ps1 -Mode Standard` is the offline full gate. `.\scripts\check_all.ps1 -Mode Max` without `-NoAutoStart` auto-starts a local `python main.py` on `:8080` and runs isolated P2P CI. It is not the docker mesh and not a 48h soak. `-NoAutoStart` fails when nothing is listening.
9. **Audit pack** — `.\scripts\export_audit_pack.ps1` is a static export (gates + tracker list). It does not restart the mesh. Pen-test and the firm PDF stay pending.
10. **Engagement prep** — `.\scripts\verify_audit_engagement_prep.ps1` checks the firm docs exist, the six automated checklist rows, and that the two human items stay pending. It does not start a soak and does not mark a firm PASS.
11. **Org** — pen-test and firm PDF. Not a code flag.

## Next 90 days (org / operator)

1. Keep CI + `industrial_gate` green on `master`  
2. Pin libp2p STRICT 48h is PASS (`pin-libp2p-strict-48h`). A new window, only if ordered, is `prepare_48h_soak.ps1` then `start_soak_prod_mesh_48h_strict.ps1`. The non-strict starter stays on disk and is not that bar.  
3. Firm outreach + NDA / scope — [EXTERNAL_AUDIT_ENGAGEMENT.md](EXTERNAL_AUDIT_ENGAGEMENT.md)  
4. Do **not** arm Long-Range or bridge on prod 778888 mesh JSON  

**Related:** [FUND_READINESS.md](FUND_READINESS.md) · [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md) · [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)
