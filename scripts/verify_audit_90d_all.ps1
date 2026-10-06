# AUDIT 90D — run all phases A–H in one shot (industrial pin).
# NOT soak / NOT mainnet / NOT firm audit PASS.
#
# Usage (repo root):
#   .\scripts\verify_audit_90d_all.ps1
#   .\scripts\verify_audit_90d_all.ps1 -SkipGate
#   .\scripts\verify_audit_90d_all.ps1 -MeshProbe   # Phase E live mesh only
#
# Thin wrapper around verify_audit_phase.ps1 -Phase All.
param(
    [switch]$SkipGate,
    [switch]$MeshProbe
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "AUDIT 90D All (A-H) via verify_audit_phase.ps1" -ForegroundColor Cyan
& (Join-Path $here "verify_audit_phase.ps1") -Phase All -SkipGate:$SkipGate -MeshProbe:$MeshProbe
exit $LASTEXITCODE
