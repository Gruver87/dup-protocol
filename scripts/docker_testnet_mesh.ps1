# Start 2-node public testnet mesh (seed + validator) and verify sync.
param(
    [switch]$SkipBuild,
    [switch]$Rebuild,
    [int]$WaitSec = 120
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

if (-not $Rebuild) { $SkipBuild = $true }

Write-Host "Starting testnet 2-node mesh (seed :19080 + validator :19081)..." -ForegroundColor Cyan
# Hashtable splat — array @("-WithValidator") does NOT bind [switch] params.
$seedArgs = @{ WithValidator = $true }
if ($SkipBuild) { $seedArgs["SkipBuild"] = $true }
try {
    & (Join-Path $ScriptDir "docker_testnet_seed.ps1") @seedArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} catch {
    Write-Host "FAIL: docker_testnet_seed -WithValidator: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Verifying testnet mesh (wait=${WaitSec}s)..." -ForegroundColor Cyan
python (Join-Path $ScriptDir "verify_testnet_mesh.py") --mesh --wait $WaitSec
exit $LASTEXITCODE
