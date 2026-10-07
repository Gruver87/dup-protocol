# NFT marketplace + related DX self-check (operator).
# NOT soak / NOT firm PASS / NOT mainnet / NOT prod feature_nft enable.
#
# Usage (repo root industrial pin):
#   .\scripts\verify_nft_marketplace.ps1
#   .\scripts\verify_nft_marketplace.ps1 -SkipStaging
#   .\scripts\verify_nft_marketplace.ps1 -WithAiLab
param(
    [switch]$SkipStaging,
    [switch]$WithAiLab
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$fail = 0

Write-Host "NFT marketplace verify (lab/DX)" -ForegroundColor Cyan
Write-Host "  NOT soak / NOT firm PASS / NOT mainnet / feature_nft stays false on prod" -ForegroundColor DarkGray
Write-Host ""

function Step([string]$name) {
    Write-Host "==> $name" -ForegroundColor Cyan
}

# --- prod flag freeze ---
Step "prod mesh feature_nft=false"
$meshes = @(
    "docker\node.prod.mesh1.json",
    "docker\node.prod.mesh2.json",
    "docker\node.prod.mesh3.json"
)
foreach ($rel in $meshes) {
    if (-not (Test-Path $rel)) {
        Write-Host "FAIL: missing $rel" -ForegroundColor Red
        $fail++
        continue
    }
    $j = Get-Content $rel -Raw | ConvertFrom-Json
    if ($j.feature_nft -ne $false) {
        Write-Host "FAIL: $rel feature_nft=$($j.feature_nft) (must be false)" -ForegroundColor Red
        $fail++
    } else {
        Write-Host "OK: $rel feature_nft=false" -ForegroundColor Green
    }
}

# --- unit (pin: no dup_sdk package) ---
Step "pytest NFT harden + UoW + marketplace wave"
python -m pytest -q `
    tests/unit/test_nft_marketplace_harden.py `
    tests/unit/test_nft_uow.py `
    tests/unit/test_wave46_nft_persistence.py `
    tests/unit/test_ai_nft_marketplace_wave.py `
    --tb=line
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: pytest" -ForegroundColor Red
    $fail++
} else {
    Write-Host "OK: pytest" -ForegroundColor Green
}

# --- labs ---
Step "nft_lab.py"
python scripts/nft_lab.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: nft_lab" -ForegroundColor Red
    $fail++
} else {
    Write-Host "OK: nft_lab" -ForegroundColor Green
}

if ($WithAiLab) {
    Step "ai_lab.py + ai_ops_anomaly offline"
    python scripts/ai_lab.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: ai_lab" -ForegroundColor Red
        $fail++
    }
    python scripts/ai_ops_anomaly.py --offline-only
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: ai_ops_anomaly" -ForegroundColor Red
        $fail++
    }
}

# --- optional staging HTTP ---
if (-not $SkipStaging) {
    Step "optional staging :19080 /nft/stats"
    $open = $false
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect("127.0.0.1", 19080, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(400)
        if ($ok -and $tcp.Connected) { $open = $true }
        $tcp.Close()
    } catch {
        $open = $false
    }
    if (-not $open) {
        Write-Host "SKIP: staging :19080 not open (Profile C optional)" -ForegroundColor DarkYellow
    } else {
        try {
            $stats = Invoke-RestMethod -Uri "http://127.0.0.1:19080/nft/stats" -TimeoutSec 5
            Write-Host ("OK: staging nft/stats total_tokens={0} tier={1}" -f $stats.total_tokens, $stats.tier) -ForegroundColor Green
        } catch {
            Write-Host "WARN: staging /nft/stats failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
if ($fail -gt 0) {
    Write-Host ("RESULT: FAIL ({0} checks)" -f $fail) -ForegroundColor Red
    exit 1
}
Write-Host "RESULT: PASS verify_nft_marketplace" -ForegroundColor Green
Write-Host "  Honesty: NOT soak / NOT firm PASS / NOT prod feature_nft flip" -ForegroundColor DarkGray
exit 0
