# External audit engagement prep (Phase H / org Phase 6).
# NOT a firm audit PASS. NOT soak. NOT mainnet.
#
# Usage (repo root):
#   .\scripts\verify_audit_engagement_prep.ps1
#   .\scripts\verify_audit_phase.ps1 -Phase H
param(
    [switch]$SkipSync
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$fail = 0

Write-Host "AUDIT engagement prep (Phase H)" -ForegroundColor Cyan
Write-Host "  NOT firm audit PASS / NOT soak / NOT mainnet" -ForegroundColor DarkGray

$required = @(
    "docs/EXTERNAL_AUDIT_ENGAGEMENT.md",
    "docs/DILIGENCE_BRIEF.md",
    "docs/EVIDENCE_MATRIX.md",
    "docs/MAINNET_GAP_ANALYSIS.md",
    "docs/adr/0001-tip-safety.md",
    "docs/adr/0023-absolute-vm-opcode-map.md",
    "docs/DEMO_RUNBOOK.md",
    "docs/CEREMONY_DRY_RUN.md",
    "docs/INCIDENT_RESPONSE.md",
    "docs/FIRM_KICKOFF_CHECKLIST.md",
    "docs/AUDIT_ENGAGEMENT_BRIEF.md",
    "docs/FIRM_OUTREACH_LETTER.md"
)
foreach ($rel in $required) {
    if (-not (Test-Path $rel)) {
        Write-Host "FAIL: missing $rel" -ForegroundColor Red
        $fail++
    } else {
        Write-Host "OK: $rel" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "==> automated checklist (live)" -ForegroundColor Cyan
if (-not $SkipSync) {
    python scripts/external_audit_tracker.py --sync-automated
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: --sync-automated" -ForegroundColor Red
        $fail++
    }
}
python scripts/external_audit_tracker.py --show-automated
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: --show-automated" -ForegroundColor Red
    $fail++
}

Write-Host ""
Write-Host "==> unit: live evaluate" -ForegroundColor Cyan
python -m pytest -q tests/unit/test_external_audit_live_automated.py --tb=line
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: live evaluate unit" -ForegroundColor Red
    $fail++
}

Write-Host ""
Write-Host "==> remaining human firm items (must stay pending)" -ForegroundColor Cyan
python -c @"
from runtime.external_audit import evaluate, HUMAN_REQUIRED_AUDIT_ITEMS
w, c, s = evaluate()
pending_human = [i for i in s['items'] if i['label'] in HUMAN_REQUIRED_AUDIT_ITEMS and not i['done']]
print('pending_human:', len(pending_human))
for i in pending_human:
    print(' -', i['label'])
assert len(pending_human) == len(HUMAN_REQUIRED_AUDIT_ITEMS), 'human firm items must remain pending without evidence'
print('OK: human firm items still pending (honest)')
"@
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: human pending honesty" -ForegroundColor Red
    $fail++
}

Write-Host ""
if ($fail -gt 0) {
    Write-Host ("RESULT: FAIL ({0} checks)" -f $fail) -ForegroundColor Red
    exit 1
}
Write-Host "RESULT: PASS engagement prep" -ForegroundColor Green
Write-Host "  Firm kickoff still org: schedule + NDA + evidence URLs for 2 human items." -ForegroundColor DarkGray
exit 0
