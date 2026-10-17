# ADR 0017 — Long-Range lab layer on the pin

- **Status:** Accepted for lab/dev code on this pin. Not a production arm.
- **Date:** 2026-10-17
- **Deciders:** DUP Protocol pin maintainers

## Context

Tip safety on the industrial mesh is the bounded `AncestryWindow` (ADR 0001).
Experimental already has a weak-subjectivity lab: persisted height+hash anchor,
Ed25519 committee certificates, gossip, and miner roll-forward. That tree's
soak packs are not pin evidence. BLS12-381 aggregate checkpoints stay a future
decision and are not implemented here.

## Decision

1. `consensus/long_range/` lives on this pin. The tip-import gate attaches only
   when `long_range_feature_armed` is true.
2. `deployment_mode` `prod` and `staging` hard-off the flag. Env cannot arm
   them. Every prod JSON keeps `feature_long_range: false`.
3. Lab/dev may set `feature_long_range: true` on `node.long_range.lab.json`
   (chain id `77779`, not `778888`) and `docker-compose.long_range.lab.yml`.
   That compose is not the prod mesh project.
4. Armed with an empty checkpoint store refuses tip import (`ws_no_anchor`).
   A history below the persisted anchor is refused.
5. Committee signatures are Ed25519. This ADR does not add BLS.

## Honesty

- Code on the pin is not a pin Long-Range soak and not mainnet proof.
- Experimental packs `lr48pass1` and `lrstrict1` stay on
  `dup-protocol-experimental`.
- Prod mesh proof remains ADR 0001 until a later decision arms this flag on
  `778888`, which this ADR does not do.

## Consequences

- `industrial_gate.py` still errors if a prod JSON sets the flag true.
- A pin lab soak is a separate operator run. It is not started by this ADR.
