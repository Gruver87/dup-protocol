# Shared health_watch helpers (Wave G mempool demote soft-WARN).

function Get-MempoolDemotedFlag {
    # Wave G: soft honesty from /status?probe=1 or /health/ready informational fields.
    param($Probe, $ReadyBody)
    try {
        if ($null -ne $Probe -and $null -ne $Probe.mempool_store) {
            return [bool]$Probe.mempool_store.store_demoted
        }
    } catch { }
    try {
        if ($null -ne $ReadyBody -and $null -ne $ReadyBody.mempool_store) {
            return [bool]$ReadyBody.mempool_store.store_demoted
        }
    } catch { }
    return $false
}
