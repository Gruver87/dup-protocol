# Production execution path (honest map)

**Scope:** industrial pin ([`dup-protocol`](https://github.com/Gruver87/dup-protocol)) prod profile `778888` — **default 3-node mesh JSON:** rust-libp2p (ADR 0020, `feature_libp2p=true`, `p2p_tls_enabled=false`). **Alternate:** TCP+TLS via `docker/node.prod.json` / ceremony (`feature_libp2p=false`). Experimental ([`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental)) is a separate tree; `feature_long_range=false`, bridge OFF on prod.

**Honesty:** Freeze tag `v1.3.1339-tip-v2-industrial` + `375d14f` = **TCP+TLS** soak evidence. Pin libp2p mesh soak/probe **pending** (`pin-libp2p-cutover-pending`). Do **not** cite Experimental libp2p soaks (`3c801b87`, `lp2pstrict1`) as pin proof.

This is **not** a mainnet readiness claim. Parallel R&D paths (libp2p, Long-Range, Beacon/Casper demos) exist in-tree but are **off** / lab-only unless an ADR flips them.

## Canonical path (prod profile)

```text
wire ingress
  → semantic validation
  → signature + sender↔pubkey binding
  → mempool
  → block assembly
  → block validation / import
  → state transition
  → state root
  → storage UoW
  → tip / finality view (honest labels)
```

| Stage | Module / entry | Notes |
|-------|----------------|-------|
| HTTP / JSON-RPC ingress | `api/http.py` (`RESTHandler`, `JSONRPCHandler`, `_handle_send_tx_obj`) | Body size + rate limit + RPC API key / JWT where configured |
| P2P wire ingress | `network/p2p_node.py` (libp2p or TLS transport) | Mutually exclusive profiles; soft-refuse / score; not hard-ban default |
| Semantic validation | `middleware/validators.py`, `blockchain/tx_validator.py` | Address / amount / shape |
| Tx identity hash | `core/tx_identity.py` → `Transaction` / mempool `add` | Client `hash` never becomes alternate identity |
| Signature + sender bind | `crypto/wallet.py` (`verify_transaction_signature`, `_transaction_signature_material`) | `derive_address(public_key) == from` |
| Mempool | `blockchain/mempool.py` | Fee-satoshi gate; ECDSA; optional native store |
| Block assembly | `core/blockchain.py` / miner path in `main.py` | Proposer from config / manifest |
| Block validate | `execution/block_validator.py` | Parent link, timestamp, satoshi value, **strict** `tx_root` |
| Import / apply | `core/blockchain.py` (`add_block`), `execution/state_engine.py` | Deterministic state_root |
| State root | native / `crypto/native.py` + StateEngine | Prod refuses tip rewrite when configured |
| Storage UoW | `storage/database.py`, `storage/rocks_store.py` | Atomic where exposed; satoshi twins |
| Tip safety | ADR 0001 / `AncestryWindow` (bounded) | Long-Range **off** until ADR 0017 complete |
| Finality view | `consensus/bft/*` (integer stake quorum) | `quorum_live` may stay false until live finality armed — honesty labels |

## Explicitly non-canonical (do not treat as prod path)

| Surface | Where | Status |
|---------|-------|--------|
| libp2p (when off) | `feature_libp2p=false` | TCP+TLS alternate; mesh JSON defaults **true** after ADR 0020 |
| Long-Range / weak subjectivity | `feature_long_range`, `consensus/long_range/` | Lab-only until ADR 0017 on disk |
| Bridge lock/mint live | `bridge/*` | **OFF** in prod JSON / cutover examples only |
| NFT / AI / MEV sprouts | `features/*` | ADR 0016 Profile C; prod flags **false** |
| Legacy Beacon/Casper demos | historical `consensus/` variants | Not the prod mesh proposer path |

## Operator verify

```powershell
.\scripts\probe_prod_mesh.ps1 -Quick
python scripts/industrial_gate.py
```

Soak PASS requires a real 48h report with `hard_fails=0` — do not infer from this document.
