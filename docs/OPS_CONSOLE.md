# DUP Protocol Ops Console (industrial pin)

Same-origin industrial UI for pin nodes (DUP Labs).  
**Repo:** [`dup-protocol`](https://github.com/Gruver87/dup-protocol)

## URLs

| Path | What |
|------|------|
| `/` or `/console` | Ops console (default) |
| `/console/assets/*` | CSP-bound JS/CSS |
| `/explorer` | Legacy feature explorer |

## Panels

| View | Live sources |
|------|----------------|
| Overview | `/status?probe=1`, sparklines, feature badges |
| Mesh & Sync | `/sync/status`, `/p2p/topology`, `/p2p/security`, `/p2p/peer-score`, `POST /p2p/reconnect` |
| Live Metrics | `GET /metrics` |
| Mempool | `/mempool`, store demote honesty |
| Chain | `/blocks` |
| EVM | `/evm/status`, `/evm/supported-opcodes` |
| Features | `/features`, `/native/crypto`, `/chain/genesis/ceremony` |
| Evidence | Sealed pack index (honesty only — not live soak) |
| Wallets | EIP-1193 + watchlist |
| Markets | `/market/snapshot`, `/market/fx` (ops orientation only) |
| Security | CSP / non-goals |

Council / Exp-only panels: if present in static assets, treat as **watch-only** — not pin industrial evidence. Prefer [DEMO_RUNBOOK_PIN.md](DEMO_RUNBOOK_PIN.md) for diligence demos.

## Security

- `Content-Security-Policy`: `default-src 'self'` (no CDN, no inline scripts)
- Path resolve via realpath allowlist under `web/console` + `web/explorer` only
- No private-key forms that POST to the node
- EIP-1193 connect + `wallet_switchEthereumChain` / `wallet_addEthereumChain` + `eth_sendTransaction`
- Session watchlist is sessionStorage only; theme in localStorage
- CORS still allow-list only

## Wallets

1. Set REST base (http_port) and JSON-RPC (rpc_port, auto-derived from `/status`).
2. Connect injected wallet → **Switch to DUP** (uses node `chain_id`).
3. Send ABS via wallet-signed `eth_sendTransaction` (wei, 18 decimals).

## Markets

`GET /market/snapshot` and `GET /market/fx` are **ops orientation only** (not consensus / not L1 oracle).

## Launcher

```powershell
.\scripts\open_ops_console.ps1          # solo + ONE main tab /
.\scripts\open_ops_console.ps1 -OpenOnly
.\scripts\open_ops_console.ps1 -AllTabs # multi-tab tour
```

## Honesty

Console may name sealed packs — **does not** claim live soak PASS. Quick probe ≠ 48h soak. Tip-v2 TCP+TLS pack ≠ pin libp2p 48h (deferred).

## Operator check

```powershell
python -m pytest -q tests/unit/test_web_console_static.py --tb=line
# with a node up:
# open http://127.0.0.1:<http_port>/
```

Not soak evidence. Not mainnet.
