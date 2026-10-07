# Secrets — industrial pin

**Never commit** `.env`, wallet keys, RPC keys, or ceremony private material.

## Where secrets live

| Context | Source |
|---------|--------|
| Local / demo mesh | `.env` at repo root (gitignored) |
| Production | `SecretManagerPort` — Vault / K8s (ADR 0015). **File-based secrets refused in production.** |

Logical ids (examples): `node.wallet_private_key`, JWT/RPC material — see [docs/adr/0015-observability-secret-management.md](../docs/adr/0015-observability-secret-management.md).

## Operator docs

- Rotation: [docs/SECRET_ROTATION.md](../docs/SECRET_ROTATION.md)
- Ceremony + genesis hash: [docs/sprouts/CEREMONY_AND_SECRETS.md](../docs/sprouts/CEREMONY_AND_SECRETS.md)
- Commands index: [docs/COMMANDS_REFERENCE.md](../docs/COMMANDS_REFERENCE.md)

## Rules

- Do not disable TLS verification to “make secrets work.”
- Do not hardcode secrets in source, compose, or evidence packs.
- After a suspected leak: rotate via `scripts/rotate_prod_secrets.ps1` and record ops evidence — see SECRET_ROTATION.
