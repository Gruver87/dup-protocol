# Quick status of the active prod mesh soak (no wait).
# Prefer logs/soak_active.json so 5h STRICT and 48h soaks both show.
param(
    [string]$LogGlob = "logs/soak_*h*.log",
    [string]$ReportFile = "logs/soak_report_48h.json"
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$activePath = Join-Path $Root "logs/soak_active.json"
$log = $null
$usingActive = $false
if (Test-Path $activePath) {
    try {
        $active = Get-Content $activePath -Raw | ConvertFrom-Json
        $candidate = Join-Path $Root ($active.log_file -replace '/', '\')
        if (Test-Path $candidate) {
            $log = $candidate
            if ($active.report_file) {
                $ReportFile = $active.report_file
            }
            $usingActive = $true
            Write-Host "Active soak (logs/soak_active.json)" -ForegroundColor Cyan
            Write-Host "  started: $($active.started_at) hours=$($active.hours)" -ForegroundColor DarkGray
        }
    } catch { }
}

# Archives (VOID power-off, stalled, prep) are not the live window.
# Do not resume them and do not pair them with historical soak_report_48h.json.
$archiveName = 'VOID|stalled|prep'
if (-not $log) {
    $prefer48 = Join-Path $Root "logs/soak_48h.log"
    if (-not (Test-Path $prefer48)) {
        $prefer48 = Join-Path $Root "logs/soak_48h_prod_mesh.log"
    }
    $allLogs = @(Get-ChildItem -Path (Join-Path $Root $LogGlob) -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending)
    $liveLogs = @($allLogs | Where-Object { $_.Name -notmatch $archiveName -and $_.Name -notmatch '\.bak' })
    if (Test-Path $prefer48) {
        $log = $prefer48
    } elseif ($liveLogs.Count -gt 0) {
        if ($allLogs.Count -gt 1) {
            Write-Host "WARN: multiple soak logs; showing newest non-archive. Fresh libp2p STRICT: .\scripts\start_soak_prod_mesh_48h_strict.ps1 -SkipRebuild" -ForegroundColor Yellow
            $allLogs | Select-Object -First 8 | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor DarkGray }
        }
        $log = $liveLogs[0].FullName
    } elseif ($allLogs.Count -gt 0) {
        $log = $allLogs[0].FullName
    } else {
        Write-Host "No soak log matching $LogGlob" -ForegroundColor Yellow
        exit 1
    }
}
$logName = [System.IO.Path]::GetFileName($log)
$voidArchive = $logName -match 'VOID'

$lines = Get-Content $log -Encoding UTF8 -ErrorAction SilentlyContinue
$ts = '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
$startLine = ($lines | Select-String -Pattern "$ts health_watch start" | Select-Object -Last 1)
$lastMesh = ($lines | Select-String -Pattern "$ts OK mesh aligned" | Select-Object -Last 1)
$lastFail = ($lines | Select-String -Pattern "$ts FAIL" | Select-Object -Last 1)
$failCount = ($lines | Select-String -Pattern "$ts FAIL").Count
$meshOk = ($lines | Select-String -Pattern "$ts OK mesh aligned").Count
$done = ($lines | Select-String -Pattern "$ts health_watch done" | Select-Object -Last 1)
$monitors = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'soak_monitor\.ps1') })
$alive = $monitors.Count -gt 0

Write-Host "Soak status" -ForegroundColor Cyan
Write-Host "  log: $([System.IO.Path]::GetFileName($log))" -ForegroundColor DarkGray
if ($startLine) { Write-Host "  started: $($startLine.Line)" -ForegroundColor DarkGray }
if ($lastMesh) { Write-Host "  latest:  $($lastMesh.Line)" -ForegroundColor Green }
if ($lastFail -and $failCount -gt 0) { Write-Host "  last_fail: $($lastFail.Line)" -ForegroundColor Yellow }
Write-Host "  mesh_ok_cycles=$meshOk fail_lines=$failCount" -ForegroundColor DarkGray
Write-Host "  monitor: $(if ($alive) { 'ALIVE pid=' + (($monitors | ForEach-Object { $_.ProcessId }) -join ',') } else { 'none' })" -ForegroundColor $(if ($alive) { 'Green' } else { 'Red' })

if ($voidArchive) {
    Write-Host "  state: VOID (host power-off archive - not PASS, do not resume)" -ForegroundColor Red
    Write-Host "  fresh: .\scripts\start_soak_prod_mesh_48h_strict.ps1 -SkipRebuild" -ForegroundColor Yellow
} elseif ($done) {
    Write-Host "  state: FINISHED" -ForegroundColor Green
} elseif ($alive) {
    Write-Host "  state: IN_PROGRESS" -ForegroundColor Yellow
} else {
    Write-Host "  state: DEAD (monitor gone before health_watch done)" -ForegroundColor Red
    Write-Host "  fresh: .\scripts\start_soak_prod_mesh_48h_strict.ps1 -SkipRebuild (Docker Desktop must be running)" -ForegroundColor Yellow
}

# Default ReportFile is the historical Jul TCP+TLS pack. Never attach it to a libp2p or VOID log.
$reportPath = $null
$reportLabel = $null
if ($usingActive -and $ReportFile -and -not $voidArchive) {
    $reportLabel = $ReportFile
    $reportPath = Join-Path $Root ($ReportFile -replace '/', '\')
} elseif (-not $voidArchive -and ($logName -eq "soak_48h.log" -or $logName -eq "soak_48h_prod_mesh.log")) {
    $reportLabel = "logs/soak_report_48h.json"
    $reportPath = Join-Path $Root "logs\soak_report_48h.json"
} elseif (-not $voidArchive -and ($logName -match '^soak_(.+)\.log$')) {
    $derived = "logs/soak_report_$($Matches[1]).json"
    $derivedPath = Join-Path $Root ($derived -replace '/', '\')
    if (Test-Path $derivedPath) {
        $reportLabel = $derived
        $reportPath = $derivedPath
    } else {
        Write-Host "  report: none for this log (logs/soak_report_48h.json is a different historical window, not PASS here)" -ForegroundColor Yellow
    }
}
if ($reportPath -and (Test-Path $reportPath)) {
    try {
        $rep = Get-Content $reportPath -Raw | ConvertFrom-Json
        Write-Host "  report: $reportLabel hours=$($rep.hours_requested) passed=$($rep.passed)" -ForegroundColor DarkGray
    } catch { }
} elseif ($voidArchive) {
    Write-Host "  report: none (VOID is not PASS; logs/soak_report_48h.json passed=true is unrelated Jul TCP+TLS)" -ForegroundColor Yellow
}

exit 0
