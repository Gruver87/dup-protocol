# Firm handoff printer (Phase 6 prep) - NOT firm PASS / NOT soak
#
# Usage (repo root):
#   .\scripts\print_firm_handoff.ps1
param(
    [switch]$SkipTracker
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "DUP Protocol - firm handoff snapshot" -ForegroundColor Cyan
Write-Host "  NOT firm audit PASS / NOT pen-test / NOT soak / NOT mainnet" -ForegroundColor DarkGray
Write-Host ""

$pinSha = (git rev-parse HEAD).Trim()
$pinShort = (git rev-parse --short HEAD).Trim()
Write-Host ("Industrial pin tip: {0} ({1})" -f $pinSha, $pinShort)
Write-Host "Industrial pin:   https://github.com/Gruver87/dup-protocol"
Write-Host "Pin tag:          v1.3.1339-tip-v2-industrial"
Write-Host "R&D repo:         https://github.com/Gruver87/dup-protocol-experimental"
Write-Host ""

$docs = @(
    "docs/EXTERNAL_AUDIT_ENGAGEMENT.md",
    "docs/AUDIT_ENGAGEMENT_BRIEF.md",
    "docs/FIRM_KICKOFF_CHECKLIST.md",
    "docs/FIRM_OUTREACH_LETTER.md",
    "docs/DILIGENCE_BRIEF.md",
    "docs/MAINNET_GAP_ANALYSIS.md",
    "docs/THREAT_MODEL.md",
    "docs/evidence/runs/phase6prep1/README.md",
    "SECURITY.md"
)
Write-Host "Artifacts:" -ForegroundColor Cyan
foreach ($rel in $docs) {
    if (Test-Path $rel) {
        Write-Host ("  OK  {0}" -f $rel) -ForegroundColor Green
    } else {
        Write-Host ("  MISS {0}" -f $rel) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "GitHub faces (pin master):" -ForegroundColor Cyan
Write-Host "  https://github.com/Gruver87/dup-protocol/blob/master/docs/FIRM_OUTREACH_LETTER.md"
Write-Host "  https://github.com/Gruver87/dup-protocol/blob/master/docs/FIRM_KICKOFF_CHECKLIST.md"
Write-Host "  https://github.com/Gruver87/dup-protocol/blob/master/docs/EXTERNAL_AUDIT_ENGAGEMENT.md"

if (-not $SkipTracker) {
    Write-Host ""
    Write-Host "==> tracker (expect 6 of 8; 2 human pending)" -ForegroundColor Cyan
    python scripts/external_audit_tracker.py --list
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: tracker" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Next human steps:" -ForegroundColor Cyan
Write-Host "  1. Fill docs/FIRM_OUTREACH_LETTER.md brackets"
Write-Host "  2. Send under NDA to chosen firm"
Write-Host "  3. Do NOT mark tracker human items until real https evidence"
Write-Host ""
Write-Host "RESULT: PASS firm handoff print (prep only)" -ForegroundColor Green
exit 0
