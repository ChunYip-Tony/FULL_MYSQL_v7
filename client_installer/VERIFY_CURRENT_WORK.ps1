param(
    [Parameter(Mandatory=$true)][string]$Api,
    [Parameter(Mandatory=$true)][string]$Token,
    [string]$Session = "",
    [string]$ExpectedVersion = "",
    [string]$FocusUpc = "74709410002"
)

$ErrorActionPreference = "Stop"
$headers = @{ Authorization = "Bearer $Token" }

function Get-ApiJson {
    param([string]$Path)
    return Invoke-RestMethod -Method GET -Uri "$Api$Path" -Headers $headers
}

Write-Host "=== FULL MYSQL CURRENT WORK VERIFICATION ==="

$health = Get-ApiJson "/healthz"
Write-Host ("Health: ok={0} version={1}" -f $health.ok, $health.version)
if (-not $health.ok) { throw "HEALTH_CHECK_FAILED" }
if ($ExpectedVersion -and $health.version -ne $ExpectedVersion) {
    throw "VERSION_MISMATCH expected=$ExpectedVersion actual=$($health.version)"
}

$neg = Get-ApiJson "/v1/app/inventory/negative-stock?limit=500"
if ($neg.queue_grain -ne "INVENTORY_OWNER") {
    throw "NEGATIVE_QUEUE_GRAIN_INVALID actual=$($neg.queue_grain)"
}

$duplicateOwners = @(
    $neg.rows |
        Group-Object inventory_owner_key |
        Where-Object { $_.Count -gt 1 }
)
if ($duplicateOwners.Count -gt 0) {
    $keys = ($duplicateOwners | ForEach-Object { $_.Name }) -join ","
    throw "NEGATIVE_QUEUE_DUPLICATE_OWNER keys=$keys"
}

$pending = Get-ApiJson "/v1/app/dumping/pending"
$pendingRows = @($pending.rows)

$focus = $null
if ($FocusUpc) {
    $focus = Get-ApiJson "/v1/app/quick-check/$FocusUpc"
    if ($null -ne $focus.item.current_oh) {
        $oh = [decimal]$focus.item.current_oh
        if ($oh -lt 0) {
            if ($focus.item.stock_status -ne "NEGATIVE") {
                throw "FOCUS_NEGATIVE_STOCK_STATUS_MISMATCH upc=$FocusUpc"
            }
            if ($null -ne $focus.item.dos -and [decimal]$focus.item.dos -ne 0) {
                throw "FOCUS_NEGATIVE_DOS_NOT_ZERO upc=$FocusUpc dos=$($focus.item.dos)"
            }
        }
    }
}

$qa = $null
if ($Session) {
    $qa = Get-ApiJson "/v1/batches/$Session/qa-summary"
}

$summary = [pscustomobject]@{
    version                       = $health.version
    negative_queue_count          = [int]$neg.count
    candidate_upc_count           = [int]$neg.candidate_upc_count
    inventory_owner_count         = [int]$neg.inventory_owner_count
    actionable_owner_count        = [int]$neg.actionable_owner_count
    suppressed_by_true_stock      = [int]$neg.suppressed_by_true_stock_count
    blocked_owner_count           = [int]$neg.blocked_owner_count
    duplicate_owner_keys          = $duplicateOwners.Count
    pending_dumping_count         = $pendingRows.Count
    focus_upc                     = $FocusUpc
    focus_current_oh              = if ($focus) { $focus.item.current_oh } else { $null }
    focus_current_oh_uom          = if ($focus) { $focus.item.current_oh_uom } else { $null }
    focus_dos                     = if ($focus) { $focus.item.dos } else { $null }
    focus_stock_status            = if ($focus) { $focus.item.stock_status } else { $null }
    focus_quick_check_status      = if ($focus) { $focus.item.quick_check_status } else { $null }
    current_active_rows           = if ($qa) { $qa.quick_check_scope.current_active_rows } else { $null }
    current_ready_rows            = if ($qa) { $qa.quick_check_scope.current_ready_rows } else { $null }
    current_hold_rows             = if ($qa) { $qa.quick_check_scope.current_hold_rows } else { $null }
    hold_reason_row_parity        = if ($qa) { $qa.quick_check_scope.hold_reason_row_parity } else { $null }
}

Write-Host ""
Write-Host "=== SUMMARY ==="
$summary | Format-List *

Write-Host ""
Write-Host "=== NEGATIVE STOCK ACTIONS ==="
$neg.rows |
    Select-Object inventory_owner_key,main_article_number,representative_upc,related_upc_count,
        effective_oh,effective_oh_uom,stock_status,action_upc,action_code |
    Format-Table -AutoSize

if ($qa) {
    Write-Host ""
    Write-Host "=== QUICK CHECK HOLD REASONS ==="
    $qa.quick_check_reason_counts | Format-List *
}

Write-Host ""
Write-Host "VERIFY_CURRENT_WORK: PASS"
