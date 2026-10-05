# Architecture Decision Records

Boundary ADRs for Absolute Blockchain Ultimate Hybrid.  
**Stack claimed in docs:** **0001–0016** · **0018–0020** (libp2p transport + industrial mesh on pin) · **0013 intentionally unused** (number reserved / skipped).

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-tip-safety.md) | Tip safety | Accepted |
| [0002](0002-p2p-transport-boundary.md) | P2P transport boundary | Accepted |
| [0003](0003-sync-consistency.md) | Sync consistency / solicit hub | Accepted |
| [0004](0004-catchup-path-a.md) | Catch-up Path A | Accepted |
| [0005](0005-fork-reconcile.md) | Fork reconcile | Accepted |
| [0006](0006-storage-boundary.md) | StoragePort | Accepted |
| [0007](0007-consensus-boundary.md) | ConsensusPort / Round SM | Accepted |
| [0008](0008-hotpath-wire-codec.md) | Hot-path wire codec | Accepted |
| [0009](0009-optional-native-fallback.md) | Optional native fallback | Accepted |
| [0010](0010-evm-bridge-boundary.md) | EVM / BridgePort | Accepted |
| [0011](0011-rpc-api-boundary.md) | QueryFacade / RPC | Accepted |
| [0012](0012-chaos-injection.md) | Chaos injection | Accepted |
| *0013* | *(intentionally unused)* | — |
| [0014](0014-graceful-shutdown-deep-health.md) | Graceful shutdown / deep ready | Accepted |
| [0015](0015-observability-secret-management.md) | Observability + SecretManager | Accepted |
| [0016](0016-feature-sprouts-profiles.md) | Feature sprouts / profiles | Accepted |
| [0018](0018-libp2p-transport.md) | libp2p transport (dual-stack ports) | Accepted |
| [0019](0019-rust-libp2p-industrial.md) | rust-libp2p industrial path | Accepted |
| [0020](0020-libp2p-industrial-mesh.md) | libp2p industrial mesh cutover (pin) | Accepted |

System map: [ARCHITECTURE.md](../ARCHITECTURE.md) · sprouts: [sprouts/](../sprouts/)

**R&D ADRs primarily on Experimental:** [0017](https://github.com/Gruver87/dup-protocol-experimental/tree/main/docs/adr/0017-long-range-weak-subjectivity.md), [0021](https://github.com/Gruver87/dup-protocol-experimental/tree/main/docs/adr/0021-mempool-validation-rust-phases.md) (Long-Range / mempool phases). **Pin prod 3-node mesh** defaults to **rust-libp2p** (ADR 0020); TCP+TLS remains alternate (`feature_libp2p=false`). `feature_long_range` stays **false**. Tag `v1.3.1339-tip-v2-industrial` = **TCP+TLS** freeze evidence. Pin libp2p 48h soak **pending** — Experimental B1 libp2p PASS is **not** pin proof.
