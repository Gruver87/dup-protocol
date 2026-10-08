# Start 3-node public testnet mesh and verify sync.
param(
    [switch]$SkipBuild,
    [switch]$Rebuild,
    [int]$WaitSec = 180
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

# Image is usually already local after seed/devnet build; rebuild only with -Rebuild.
if (-not $Rebuild) { $SkipBuild = $true }

Write-Host "Starting testnet 3-node mesh (:19080/:19081/:19082)..." -ForegroundColor Cyan
# Hashtable splat — array @("-Mesh3") does NOT bind [switch] params in Windows PowerShell.
$seedArgs = @{ Mesh3 = $true }
if ($SkipBuild) { $seedArgs["SkipBuild"] = $true }
try {
    & (Join-Path $ScriptDir "docker_testnet_seed.ps1") @seedArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} catch {
    Write-Host "FAIL: docker_testnet_seed -Mesh3: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Verifying 3-node mesh (wait=${WaitSec}s)..." -ForegroundColor Cyan
python (Join-Path $ScriptDir "verify_testnet_mesh.py") --mesh3 --wait $WaitSec
exit $LASTEXITCODE
