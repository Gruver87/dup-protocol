# Verify security-honesty waves (cf6d236a / 434c143a). No soak / no Docker.
#
#   .\scripts\verify_security_honesty.ps1
#   .\scripts\verify_security_honesty.ps1 -Gate
#   .\scripts\verify_security_honesty.ps1 -NeedlesOnly

param(
    [switch]$Gate,
    [switch]$NeedlesOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$pyArgs = @("scripts/verify_security_honesty.py")
if ($Gate) { $pyArgs += "--gate" }
if ($NeedlesOnly) { $pyArgs += "--needles-only" }

Write-Host ">>> python $($pyArgs -join ' ')" -ForegroundColor Cyan
& python @pyArgs
exit $LASTEXITCODE
