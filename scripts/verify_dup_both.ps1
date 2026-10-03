# DUP Protocol pin — call Experimental dual-repo suite from the pin tree
#
# Requires sibling Experimental checkout (default Desktop path).
#
#   .\scripts\verify_dup_both.ps1 -Mode Quick
#   .\scripts\verify_dup_both.ps1 -Mode Standard
#   .\scripts\verify_dup_both.ps1 -Mode Full
#   .\scripts\verify_dup_both.ps1 -ExpRoot "C:\Users\vovun\Desktop\Absolute_Blockchain_Experimental"
#
# Pin-only: .\scripts\verify_project.ps1 -Mode Industrial

param(
    [ValidateSet("Quick", "Standard", "Full", "Max")]
    [string]$Mode = "Standard",
    [string]$ExpRoot = "",
    [double]$MinSoakHours = 48,
    [switch]$KeepGoing,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$PinRoot = Split-Path -Parent $PSScriptRoot

if ($Help) {
    Write-Host "verify_dup_both.ps1 - run Experimental verify_dup_suite with this pin"
    Write-Host "  .\scripts\verify_dup_both.ps1 -Mode Quick|Standard|Full|Max"
    exit 0
}

if (-not $ExpRoot) {
    $sibling = Join-Path (Split-Path -Parent $PinRoot) "Absolute_Blockchain_Experimental"
    if (Test-Path $sibling) { $ExpRoot = $sibling }
    else {
        Write-Host "FAIL: set -ExpRoot to dup-protocol-experimental checkout" -ForegroundColor Red
        exit 1
    }
}

$suite = Join-Path $ExpRoot "scripts\verify_dup_suite.ps1"
if (-not (Test-Path $suite)) {
    Write-Host "FAIL: missing $suite" -ForegroundColor Red
    exit 1
}

Write-Host "Pin:  $PinRoot" -ForegroundColor Cyan
Write-Host "Exp:  $ExpRoot" -ForegroundColor Cyan
& $suite -Mode $Mode -PinRoot $PinRoot -MinSoakHours $MinSoakHours -KeepGoing:$KeepGoing
exit $LASTEXITCODE
