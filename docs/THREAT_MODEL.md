# Threat model — DUP Protocol (industrial L1)

**Product:** DUP Protocol (DUP Labs) · Formerly Absolute Blockchain Ultimate Hybrid  
**Audience:** external auditors / operators  
**Scope:** single-tip prod-profile chain `778888` (Profile A) · **working-tip prod mesh:** rust-libp2p (ADR 0020); **freeze tag** `v1.3.1339-tip-v2-industrial` reviewed **TCP+TLS** only  
**Out of scope:** shard lab, L2 sandbox, ZK/PQ, bridge ON, Long-Range (`feature_long_range=false`)  
**Updated:** 2026-10-05 (ADR 0020 transport honesty; assets unchanged)

## Assets

| Asset | Why it matters |
|-------|----------------|
| Account balances / nonces (satoshi truth) | Theft / inflation |
| Tip `state_root` (`b_satoshi` when ceremony-armed) | Consensus split |
| Block ancestry / tip-safety window | Long-range / rollback abuse |
| Validator ceremony keys | Equivocation / takeover |
| JWT / RPC API keys | Admin & RPC abuse |
| P2P peer scoring / bans | Eclipse / DoS |

## Trust boundaries

```text
[Wallet/Explorer] --HTTP/RPC+JWT--> [API] --> [Blockchain/StateService]
[Peer] --libp2p Noise/Yamux (/abs/wire) OR TCP+TLS/mTLS (alternate)--> [P2P admit] --> [Dispatcher] --> [Sync/TipSafety/Apply]
[Operator] --secrets/env--> [SecretManager] --> [Node]
[Bridge L1] --OFF on mesh--> (no trust path until audited cutover)
```

Default prod 3-node mesh JSON after ADR 0020: **libp2p** (TLS off). Ceremony / `node.prod.json`: **TCP+TLS** when `feature_libp2p=false`. Profiles are mutually exclusive.

## Adversaries (assumed)

1. **Malicious peer** — forged blocks, bad state_root responses, spam, dual-dial churn.  
2. **Compromised RPC client** — unsigned deploy, rate abuse (mitigated: mempool-only deploy, API keys).  
3. **Operator mistake** — wrong ceremony pin, KeepVolumes across tip encoding flip.  
4. **Supply-chain** — dependency CVEs (cargo/pip audit in CI).

## Controls (in-repo)

| Threat | Control |
|--------|---------|
| Bad tip import | Tip-safety enforce (`TIP_SAFETY_ENFORCE`) on import |
| State root drift | Wire solicit + local root match; tip v2 satoshi leaves |
| Peer spam | Rate limits + soft-refuse + strike/ban |
| Float money drift | Wave C satoshi apply / tip encoding |
| Bridge theft | `bridge_enabled=false` on prod mesh (by design) |
| Secret leakage | SecretManagerPort; rotation runbook |

## Residual risks (honest)

- No Long-Range / tip proof; bounded AncestryWindow only.  
- `finality_quorum_live` remains false until real QC mesh proof.  
- EVM is a **subset**, not a full Ethereum client.  
- pyo3 0.22 held with scoped RUSTSEC ignores until 0.29 migration (PR #7).  
- Historical Jul float 48h soak pre-dates tip-v2; **tip-v2 48h soak PASS** Aug 5–7 2026 (`docs/evidence/runs/375d14f/`) on **TCP+TLS** freeze evidence. **Pin libp2p mesh soak/probe after ADR 0020: not completed.**

## References

- [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md)  
- [AUDIT_SCOPE.md](AUDIT_SCOPE.md)  
- [AUDITS.md](AUDITS.md)  
- ADR 0001 Tip-safety · ADR 0016 Feature sprouts  
