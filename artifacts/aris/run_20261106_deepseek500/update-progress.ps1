param([switch]$Watch)
$ErrorActionPreference = 'Stop'
$study = $PSScriptRoot
$target = Join-Path $study 'PROGRESS.md'
$schedule = Get-Content "$study/schedule.json" -Raw | ConvertFrom-Json
$reused = Get-Content "$study/reused.json" -Raw | ConvertFrom-Json -AsHashtable
$selected = (Get-Content "$study/selection.json" -Raw | ConvertFrom-Json).pilot_order
$lastContent = ''

do {
    $terminal = @{}
    $untouched = @()
    $started = @()
    foreach ($task in $schedule) {
        $id = "$($task.case)-$($task.model)-$($task.arm)"
        $stratum = if ($task.case -in $selected) { 'Selected 50' } else { 'Other 450' }
        $key = "$stratum $($task.arm)"
        if ($reused.ContainsKey($id) -or (Test-Path -LiteralPath "$study/attempts/$id/job.json")) {
            $terminal[$key] = 1 + [int]$terminal[$key]
        } elseif (Test-Path -LiteralPath "$study/attempts/$id") {
            $started += $id
        } else {
            $untouched += $id
        }
    }
    $done = $schedule.Count - $untouched.Count - $started.Count
    $left = $schedule.Count - $done
    $status = Get-Content "$study/status.json" -Raw | ConvertFrom-Json
    $worker = if ($started.Count) { $started -join ', ' } else { 'None' }
    $next = if ($untouched.Count) { $untouched[0] } else { 'None' }
    $state = if ($status.status -eq 'provider_rate_wait') {
        'Provider wait through ' + ([DateTimeOffset]::Parse($status.resume_at).ToOffset([TimeSpan]::FromHours(7))).ToString('yyyy-MM-dd HH:mm:ss') + ' WIB'
    } else { $status.status.Replace('_', ' ') }
    $finished = if ($left -eq 0) { '[x]' } else { '[ ]' }
    $lines = @(
        '# DeepSeek study checklist', '',
        "**$done / $($schedule.Count) runs accounted for · $left left**", '',
        "- $($reused.Count) reused pilot runs and $($done - $reused.Count) fresh terminal runs",
        "- $($started.Count) started without a terminal record and $($untouched.Count) untouched",
        "- Started without a terminal record: $worker",
        "- Next untouched: $next",
        "- Coordinator: $state", '',
        '| Cases | Arm | Terminal | Remaining |',
        '|---|---|---:|---:|'
    )
    foreach ($group in @(@('Selected 50', 50), @('Other 450', 450))) {
        foreach ($arm in 'baseline', 'candidate') {
            $count = [int]$terminal["$($group[0]) $arm"]
            $lines += "| $($group[0]) | $arm | $count / $($group[1]) | $($group[1] - $count) |"
        }
    }
    $lines += @('', '- [x] Verify the 107-run checkpoint and old worker state',
        '- [x] Verify zero-rated Hobby retrieval and resume the frozen schedule',
        "- $finished Account for all 1,000 runs",
        '- [ ] Rebuild the results and audit the paper',
        '- [ ] Verify the clean paper build and reproducibility archive', '',
        'Terminal runs include workflow failures and timeouts. Counts come from the frozen schedule, reused references and terminal job journals.')
    $content = $lines -join [Environment]::NewLine
    if ($content -ne $lastContent) {
        $temporary = "$target.tmp"
        Set-Content -Encoding utf8 -LiteralPath $temporary -Value $content
        [System.IO.File]::Move($temporary, $target, $true)
        $lastContent = $content
    }
    if ($Watch -and $left -gt 0) { Start-Sleep -Seconds 15 }
} while ($Watch -and $left -gt 0)
