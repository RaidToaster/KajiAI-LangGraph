$ErrorActionPreference = 'Stop'
$study = $PSScriptRoot
$root = (Resolve-Path -LiteralPath "$study/../../..").Path
Set-Location -LiteralPath $root
$python = Join-Path $root '.venv/Scripts/python.exe'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
function Resume-ReconciledFetch {
    $stop = Get-Content -LiteralPath "$study/STOP.json" -Raw | ConvertFrom-Json
    if ($stop.problems.Count -ne 2 -or $stop.problems[1] -ne 'transport failure; no retry') { return $false }
    if ($stop.problems[0] -notmatch '^tinyfish_fetch/([0-9]{3}) unresolved or HTTP failure$') { return $false }
    $number = $Matches[1]
    $attempt = $stop.attempt
    if ($attempt -notmatch '^dev-[0-9]+-deepseek-(baseline|candidate)$') { return $false }
    $meta = Get-Content -LiteralPath "$study/attempts/$attempt/response-$number.json" -Raw | ConvertFrom-Json
    $timeout = $meta.error -eq 'TimeoutError: The read operation timed out'
    $capture = $meta.status -eq 200 -and $meta.error -eq 'RuntimeError: TinyFish HTTP 200; response size 2000001'
    if (-not ($timeout -or $capture)) { return $false }
    for ($tryNumber = 0; $tryNumber -lt 3; $tryNumber++) {
        & $python "$study/archive_recovered_stop.py" | Out-Host
        if ($LASTEXITCODE -eq 0) { return $true }
        if ($LASTEXITCODE -ne 2) { throw 'Reconciliation overlay verification failed.' }
        & $python "$study/reconcile_fetch.py" --attempt $attempt --number ([int]$number) | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Read-only Fetch usage lookup failed.' }
        & $python "$study/archive_recovered_stop.py" | Out-Host
        if ($LASTEXITCODE -eq 0) { return $true }
        if ($LASTEXITCODE -ne 2) { throw 'Reconciliation overlay verification failed.' }
        if ($tryNumber -lt 2) { Start-Sleep -Seconds 25 }
    }
    return $false
}
while ($true) {
    if (Test-Path -LiteralPath "$study/STOP.json") {
        if (-not (Resume-ReconciledFetch)) { throw 'The recorded service stop requires review.' }
    }
    try {
        & "$study/run-builder-paid.ps1"
    } catch {
        if (-not (Test-Path -LiteralPath "$study/STOP.json")) { throw }
        continue
    }
    $status = Get-Content -LiteralPath "$study/status.json" -Raw | ConvertFrom-Json
    if ($status.status -ne 'quota_checkpoint') { break }
    $delay = ([DateTimeOffset]::Parse($status.resume_at) - [DateTimeOffset]::UtcNow).TotalSeconds
    if ($delay -gt 0) { Start-Sleep -Seconds ([Math]::Ceiling($delay)) }
}

