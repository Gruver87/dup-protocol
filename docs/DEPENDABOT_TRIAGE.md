# Dependabot triage (industrial harden)

**Updated:** 2026-10-02  
**Rule:** no kitchen-sink merges — only bumps that keep CI green and reduce risk.

## Closed on Experimental + pin (2026-10-02)

| Item | Action |
|------|--------|
| pip-audit cryptography / PyJWT / wasmtime | Bumped runtime pins `cryptography==50.0.2`, `PyJWT==2.15.1`, `wasmtime==49.0.0` + hashed `requirements-runtime.lock`; CI audits runtime file |
| Supply-chain ops | Digest-pinned `Dockerfile.prod` bases; cargo-audit ignores owner/expiry; CODEOWNERS on L1 paths |
| `RUSTSEC-2026-0285` rustls | Already on **0.23.45** (prior wave) |

## Closed on Experimental (2026-09-21)

| Item | Action |
|------|--------|
| `RUSTSEC-2026-0285` rustls TLS1.3 handshake | Bumped `rustls` **0.23.42 → 0.23.45** in `native/abs_native` (`Cargo.toml` pin + lock) |
| rustfmt Hybrid Node Checks | `cargo fmt` on `mempool_store` / `amount` / `tx_row` / `receipt_row` |
| experimental-rd.yml | Quoted step name with `:` (YAML parse fail → 0s red badge) |

## Hold (do not merge until migration PR is green)

| PR | Package | Why hold |
|----|---------|----------|
| [#7](https://github.com/Gruver87/dup-protocol/pull/7) | pyo3 0.22→0.29 | Required for pyo3 RUSTSEC clear; ~386 compile breaks (`new_bound` / `with_gil` API). Tracked; interim ignores in [`.cargo/audit.toml`](../.cargo/audit.toml) |
| — | rkyv via rust_decimal | `RUSTSEC-2026-0235` ignored interim (optional feature unused; `default-features=false` + `std` only). Prefer dropping optional lock edges later rather than enabling `rkyv` feature. |
| — | hickory-proto via libp2p-mdns | `RUSTSEC-2026-0119` ignored interim (ADR 0019 opt-in mDNS lab; needs upstream libp2p-mdns → hickory≥0.26). Default prod mesh JSON is libp2p (ADR 0020); TCP+TLS is alternate profile. |
| — | ring 0.16 / rustls-webpki 0.101 via libp2p-tls | `RUSTSEC-2025-0009`, `0098/0099/0104` ignored interim (stale optional tls lock edges; Noise+TCP path only). Prefer lockfile prune or upstream libp2p-tls bump. |
| — | h2 0.3.27 via hyper 0.14 / igd-next | `RUSTSEC-2026-0258` ignored interim (libp2p UPnP lab; patch is h2≥0.4.16 → hyper 1.x). Default prod mesh JSON is libp2p (ADR 0020); TCP+TLS is alternate profile. |
| [#2](https://github.com/Gruver87/dup-protocol/pull/2) | rand 0.8→0.10 | Dev-dep churn; wait for pyo3 wave |
| [#10](https://github.com/Gruver87/dup-protocol/pull/10) | socket2 0.5→0.6 | Native P2P surface; needs soak |
| [#12](https://github.com/Gruver87/dup-protocol/pull/12) | redis major | Mesh rate-limit path |
| [#13](https://github.com/Gruver87/dup-protocol/pull/13) | websockets major | WS RPC path |
| [#11](https://github.com/Gruver87/dup-protocol/pull/11) | serde_json patch | Usually safe — merge after Tests green |
| [#15](https://github.com/Gruver87/dup-protocol/pull/15) | sha2 0.10→0.11 | Native hash surface — after pyo3 |

~~[#8] wasmtime~~ / ~~[#14] cryptography~~ / ~~[#9] pyjwt~~ — closed via runtime pin bump 2026-10-02 (not Dependabot PR merge).

## Safe to merge when Actions CI is green (actions only)

| PR | Action |
|----|--------|
| [#3](https://github.com/Gruver87/dup-protocol/pull/3) | actions/checkout |
| [#5](https://github.com/Gruver87/dup-protocol/pull/5) | actions/setup-python |
| [#4](https://github.com/Gruver87/dup-protocol/pull/4) | docker/login-action |
| [#1](https://github.com/Gruver87/dup-protocol/pull/1) | docker/metadata-action |
| [#6](https://github.com/Gruver87/dup-protocol/pull/6) | softprops/action-gh-release |

Merge order: checkout → setup-python → docker/* → gh-release. Re-run `security-audit.yml` + `test.yml` after each.

## Exit criteria

- `cargo audit` clean **without** pyo3 ignores (pyo3 ≥ 0.29)  
- No open Dependabot PRs older than 30 days without triage note here  
