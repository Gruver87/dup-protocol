# Audit scope letter — industrial L1

**Product:** DUP Protocol (DUP Labs)  
**Formerly:** Absolute Blockchain Ultimate Hybrid (same pin)  
**Repo:** https://github.com/Gruver87/dup-protocol  
**Chain under review:** prod-profile `778888` (Docker 3-node mesh / future mainnet-v1)  
**Date:** 2026-10-05 (ADR 0020 transport note; freeze tag unchanged)  
**Release pin:** tag **`v1.3.1339-tip-v2-industrial`** (`0531995`; **TCP+TLS** historical evidence) · working tip mesh = **rust-libp2p** per [ADR 0020](adr/0020-libp2p-industrial-mesh.md) (pin libp2p soak **pending**)  
**Phase status:** Phase 2 tip-v2 48h PASS (**TCP+TLS**, `375d14f`) · Phase 3 ops dry-run PASS · Phase 4 audit binder READY · Exp→pin honesty CLOSED (units+gate) · ADR 0020 mesh cutover (**no** new pin libp2p soak) — external firm engagement pending

## In scope

1. **Consensus tip path** — block import, tip-safety enforce, Path A catch-up, fork reconcile.  
2. **State / money** — satoshi storage dual-write; tip encoding v2 `b_satoshi` (ceremony-armed); StateService apply / fees / gas / reward.  
3. **P2P** — **Working tip:** rust-libp2p industrial mesh (Noise, Yamux, `/abs/wire`) when reviewing post–ADR 0020 HEAD; **freeze tag:** TCP+TLS/mTLS mesh. Rate limits, soft-refuse, state_root solicit honesty apply to both profiles (mutually exclusive).  
4. **API / RPC** — JWT admin, API keys, mempool-only contract deploy in prod.  
5. **Persistence** — RocksDB prod path, reorg index purge, DR rehearsal scripts.  
6. **Native crypto** — `abs_native` kernels on hot path (`ABS_REQUIRE_NATIVE_CRYPTO`).  
7. **Ops gates** — `industrial_gate`, `prod_gate`, `bridge_off_audit_gate`, evidence packs under `docs/evidence/runs/`.

## Explicitly out of scope

| Module | Reason |
|--------|--------|
| Shard lab (Profile E) | Separate mesh/DB; `feature_sharding=false` on prod |
| Plasma / Lightning / WASM / ZK / PQ | R&D; prod FEATURE_* false |
| Bridge ON / L1 lock-mint | Disabled until separate audited cutover |
| NFT / app staging | Profile C; not L1 trust path |
| Public mainnet ops / legal / listing | Organizational, not code audit of this tree |
| Full Ethereum client compatibility | EVM subset only |
| Tip proof / Long-Range | Not claimed — Long-Range R&D in [dup-protocol-experimental](https://github.com/Gruver87/dup-protocol-experimental); `feature_long_range=false` on pin prod |
| Experimental-only libp2p soak evidence | Not pin proof — e.g. `3c801b87` / `lp2pstrict1` on Experimental; pin libp2p 48h **pending** (`pin-libp2p-cutover-pending`) |

## Deliverables expected from auditor

- Written report with severity ratings  
- Reproduction notes against tagged commit  
- Clear statement whether tip-v2 + apply path were in the reviewed build  

## Firm engagement

Placeholder — replace when contracted:

- Firm: _TBD_  
- SOW URL: _TBD_  
- Tracker: `scripts/external_audit_tracker.py` (do not mark complete until PDF lands in `audits/<firm>/`)

## References

- [THREAT_MODEL.md](THREAT_MODEL.md)  
- [AUDITS.md](AUDITS.md)  
- [STATE_ROOT_ENCODING_MIGRATION.md](STATE_ROOT_ENCODING_MIGRATION.md)  
- [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)  
