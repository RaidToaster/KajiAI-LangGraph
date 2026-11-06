$ErrorActionPreference = 'Stop'
$study = $PSScriptRoot
$root = (Resolve-Path -LiteralPath "$study/../../..").Path
Set-Location -LiteralPath $root
$python = Join-Path $root '.venv/Scripts/python.exe'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
function Resume-RetrievalFault {
    $stop = Get-Content -LiteralPath "$study/STOP.json" -Raw | ConvertFrom-Json
    if ($stop.problems.Count -ne 2 -or $stop.problems[1] -ne 'transport failure; no retry') { return $false }
    if ($stop.problems[0] -notmatch '^(tinyfish_search|tinyfish_fetch)/([0-9]{3}) unresolved or HTTP failure$') { return $false }
    $service = $Matches[1]
    $number = $Matches[2]
    $attempt = $stop.attempt
    if ($attempt -notmatch '^dev-[0-9]+-deepseek-(baseline|candidate)$') { return $false }
    $meta = Get-Content -LiteralPath "$study/attempts/$attempt/response-$number.json" -Raw | ConvertFrom-Json
    if ($null -eq $meta.status -and $meta.error -like '*getaddrinfo failed*') {
        for ($tryNumber = 0; $tryNumber -lt 4; $tryNumber++) {
            & $python "$study/archive_recovered_stop.py" --carry-dns | Out-Host
            if ($LASTEXITCODE -eq 0) { return $true }
            if ($LASTEXITCODE -ne 2) { throw 'DNS reservation verification failed.' }
            if ($tryNumber -lt 3) { Start-Sleep -Seconds 20 }
        }
        return $false
    }
    if ($service -ne 'tinyfish_fetch') { return $false }
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
    if ($timeout) {
        & $python "$study/archive_recovered_stop.py" --carry-unknown-fetch | Out-Host
        if ($LASTEXITCODE -eq 0) { return $true }
        if ($LASTEXITCODE -ne 2) { throw 'Unknown Fetch reservation verification failed.' }
    }
    return $false
}
while ($true) {
    if (Test-Path -LiteralPath "$study/PAUSE_REQUESTED.json") { break }
    if (Test-Path -LiteralPath "$study/STOP.json") {
        if (-not (Resume-RetrievalFault)) { throw 'The recorded service stop requires review.' }
    }
    try {
        & "$study/run-hobby.ps1"
    } catch {
        if (-not (Test-Path -LiteralPath "$study/STOP.json")) { throw }
        continue
    }
    $status = Get-Content -LiteralPath "$study/status.json" -Raw | ConvertFrom-Json
    if ($status.status -ne 'quota_checkpoint') { break }
    $delay = ([DateTimeOffset]::Parse($status.resume_at) - [DateTimeOffset]::UtcNow).TotalSeconds
    while ($delay -gt 0) {
        if (Test-Path -LiteralPath "$study/PAUSE_REQUESTED.json") { return }
        Start-Sleep -Seconds ([Math]::Min(15, [Math]::Ceiling($delay)))
        $delay = ([DateTimeOffset]::Parse($status.resume_at) - [DateTimeOffset]::UtcNow).TotalSeconds
    }
}

