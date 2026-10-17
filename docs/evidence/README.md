# Evidence packages (Wave B)

Versioned, hashed mesh/ops artifacts. **Not** a substitute for external audit.

## How to package

```bash
python scripts/package_mesh_evidence.py \
  --out docs/evidence/runs/<commit-or-date> \
  --probe-log logs/probe_prod_mesh.txt \
  --soak-report docs/evidence/runs/pin-libp2p-strict-48h/soak_report_48h_libp2p_strict.json
```

The command above points at the packaged libp2p STRICT report. `logs/soak_report_48h.json` is the July TCP+TLS float tip, a different window. Use it only when packaging that historical report.

`manifest.json` binds `commit` + `sha256` of each file. Missing inputs are recorded as `status=missing` (honest).

## What belongs here

| Artifact | Proves |
|----------|--------|
| Probe log with `/health/ready` PASS ×3 | Mesh ready (Wave A) |
| Soak report `passed=true` | Long-run stability |
| Image digest / compose project id | Reproducible mesh image |

## Honesty

Historical Jul 2026 soak/failover claims in [EVIDENCE_MATRIX.md](../EVIDENCE_MATRIX.md) remain **operator-local** until a package for that SHA is committed or released as a GitHub Actions artifact.

ADR 0020 working-tip mesh: **STRICT 48h PASS** 2026-10-15–17 in [`runs/pin-libp2p-strict-48h/`](runs/pin-libp2p-strict-48h/) (`passed=true`, `hard_fails=0`, not mainnet, tag `v1.3.1340-libp2p-industrial-mesh` not cut). [`runs/pin-libp2p-cutover-pending/README.md`](runs/pin-libp2p-cutover-pending/README.md) stays the **Quick probe** pack. The **48h soak VOID** 2026-10-08 and the 2026-10-11 short window are not PASS.
