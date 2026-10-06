# ADR 0023 — Absolute-VM opcode map (no silent Yellow Paper remap)

- **Status:** Accepted (experimental + industrial honesty)
- **Date:** 2026-10-01
- **Deciders:** DUP Protocol maintainers
- **Brand:** DUP Labs · DUP Protocol

## Context

The hybrid EVM interpreter (`execution/evm_interpreter.py`) and native kernel
(`native/.../evm_pure_runner.rs`) share an **Absolute** opcode byte map for
comparison/bitwise ops that **differs** from the Ethereum Yellow Paper
(e.g. Absolute `0x10=AND`, `0x16=LT`; Yellow Paper `0x10=LT`, `0x16=AND`).

Audit findings showed this is easy to mis-label as “EVM compatible.” A silent
remap to Yellow Paper would break deployed Absolute bytecode and invalidate
evidence packs without a migration plan.

## Decision

1. **Keep Absolute-VM as the canonical opcode map** for this codebase until an
   explicit migration ADR + lab + evidence pack lands.
2. **Disclose** via `docs/sprouts/EVM_COMPAT_MATRIX.md` and
   `GET /evm/status` → `opcode_map_honesty` (`absolute_native`).
3. **Forbid** silent remapping of opcode bytes to Yellow Paper in prod JSON,
   hot-path kernels, or “compat fixes” without this ADR being superseded.
4. Optional future path (out of scope here): Yellow Paper + revm migration —
   requires breaking-change ADR, bytecode migration story, and new STRICT labs.
   That work is **not** unlocked by this decision.

## Honesty

- Absolute-VM ≠ solc / geth drop-in.
- CREATE2 host string salts are Absolute-hashed before EIP-1014 addressing
  (see matrix row) — not claimed as raw EIP-1014 host API.
- Industrial pin and experimental must both keep the disclosure; experimental
  must not report Yellow Paper compatibility as industrial evidence.

## Consequences

- Phase F remap / revm remains optional later work — not the default.
- Gates and docs that claim opcode compatibility must use Absolute honesty
  vocabulary (`absolute_native` / matrix wording).

## References

- [EVM_COMPAT_MATRIX.md](../sprouts/EVM_COMPAT_MATRIX.md)
- ADR [0010](0010-evm-bridge-boundary.md) (bridge ≠ EVM host)
- [AUDIT_90D_FIX_PLAN.md](../AUDIT_90D_FIX_PLAN.md) Phase F1
