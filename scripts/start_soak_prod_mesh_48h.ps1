# 48h pin prod-mesh soak (dup-protocol / ADR 0020 libp2p). Default scoring, not STRICT.
# passed=true requires health_watch exit 0, hard_fails=0, wall-clock ~48h.
# Harness flakes log WARN (FullHarness). Unreachable nodes are FAIL.
# Does NOT start soak unless operator runs this script explicitly.
param(
    [int]$Hours = 48,
    [int]$IntervalSec = 300,
    [string]$LogFile = "logs/soak_48h_pin_libp2p.log",
    [string]$ReportFile = "logs/soak_report_48h_pin_libp2p.json",
    [switch]$Foreground,
    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

$logDir = Split-Path -Parent $LogFile
if ($logDir -and -not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

Write-Host "48h pin prod mesh soak (default scoring; not STRICT; not mainnet)" -ForegroundColor Cyan
Write-Host "  hours=$Hours interval=${IntervalSec}s FullHarnessEvery=6" -ForegroundColor DarkGray
Write-Host "  pass bar: hard_fails=0, nodes reachable, mesh aligned (1-height WARN ok)" -ForegroundColor DarkGray
Write-Host "  log=$LogFile report=$ReportFile" -ForegroundColor DarkGray

if (-not $SkipPreflight) {
    & (Join-Path $ScriptDir "prepare_48h_soak.ps1") -Hours $Hours -IntervalSec $IntervalSec
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: 48h prepare. Do not start soak." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

& (Join-Path $ScriptDir "stop_soak_monitors.ps1") -Force
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$gitTag = "unknown"
$gitSha = "unknown"
$gitDirty = $false
try {
    $desc = git describe --tags --abbrev=0 2>$null
    if ($desc) { $gitTag = $desc.Trim() }
    $sha = git rev-parse HEAD 2>$null
    if ($sha) { $gitSha = $sha.Trim() }
    $gitDirty = [bool](git status --porcelain 2>$null)
} catch { }

$imageId = ""
try {
    $imageId = (docker inspect abs-blockchain-prod:local --format "{{.Id}}" 2>$null | Out-String).Trim()
} catch { }

$activeMeta = @{
    log_file = $LogFile
    report_file = $ReportFile
    hours = $Hours
    interval_sec = $IntervalSec
    strict = $false
    full_harness = $true
    started_at = (Get-Date -Format "o")
    git_tag = $gitTag
    git_sha = $gitSha
    git_dirty = $gitDirty
    image_id = $imageId
    note = "48h pin libp2p default scoring - not STRICT - not mainnet"
}
$activePath = Join-Path $Root "logs/soak_active.json"
$activeMeta | ConvertTo-Json | Set-Content -Path $activePath -Encoding UTF8

python scripts/record_evidence_run.py `
    --name soak_monitor_48h_pin_libp2p `
    --result IN_PROGRESS `
    --command ".\scripts\start_soak_prod_mesh_48h.ps1" `
    --artifact $LogFile `
    --git-tag $gitTag `
    2>$null | Out-Null

$soakScript = Join-Path $ScriptDir "soak_monitor.ps1"
$soakArgs = @(
    "-Hours", $Hours,
    "-IntervalSec", $IntervalSec,
    "-ProdMesh",
    "-FullHarness",
    "-LogFile", $LogFile,
    "-ReportFile", $ReportFile
)

if ($Foreground) {
    & $soakScript @soakArgs
    exit $LASTEXITCODE
}

$cmdLine = @(
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden",
    "-File `"$soakScript`"",
    "-Hours $Hours",
    "-IntervalSec $IntervalSec",
    "-ProdMesh -FullHarness",
    "-LogFile `"$LogFile`"",
    "-ReportFile `"$ReportFile`""
) -join " "
$created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine      = $cmdLine
    CurrentDirectory = $Root
}
if ($created.ReturnValue -ne 0 -or -not $created.ProcessId) {
    Write-Host "FAIL: could not spawn soak_monitor (Win32 Create=$($created.ReturnValue))" -ForegroundColor Red
    exit 1
}
Start-Sleep -Seconds 3
$alive = Get-CimInstance Win32_Process -Filter "ProcessId=$($created.ProcessId)" -ErrorAction SilentlyContinue
if (-not $alive) {
    Write-Host "FAIL: soak_monitor PID $($created.ProcessId) died immediately" -ForegroundColor Red
    exit 1
}

$activeMeta.pid = [int]$created.ProcessId
$activeMeta | ConvertTo-Json | Set-Content -Path $activePath -Encoding UTF8

Write-Host "OK: 48h soak started PID=$($created.ProcessId) (pin; not yet PASS)" -ForegroundColor Green
Write-Host "  check:  .\scripts\check_soak.ps1" -ForegroundColor DarkGray
Write-Host "  status: .\scripts\soak_status.ps1" -ForegroundColor DarkGray
Write-Host "  stop:   .\scripts\stop_soak_monitors.ps1 -Force" -ForegroundColor DarkGray
Write-Host "  claim PASS only if hours_elapsed>=48 and passed=true" -ForegroundColor Yellow
exit 0
