$ErrorActionPreference='Stop'
$taskRoot='artifacts/aris/run_20261106_pilot50'
$taskPython=(Resolve-Path -LiteralPath '.venv/Scripts/python.exe').Path
$taskOldWorkers=@(Get-Process -Name python,pythonw,ollama -ErrorAction SilentlyContinue)
if ($taskOldWorkers.Count -gt 0) { throw 'Existing Python/Ollama worker: inspect before launch; no pilot started.' }
$env:OMP_NUM_THREADS='2';$env:MKL_NUM_THREADS='2';$env:OPENBLAS_NUM_THREADS='2';$env:NUMEXPR_NUM_THREADS='2';$env:PYTHONUTF8='1';$env:OLLAMA_HOST='127.0.0.1:11434'
$taskStamp=[DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss')
$taskReceipt=@{started_at_utc=[DateTime]::UtcNow.ToString('o');one_worker=$true;threads=2;max_attempt_seconds=300;pilot_only=$true;protocol_sha256=(Get-FileHash -LiteralPath "$taskRoot/protocol.json").Hash.ToLower();launcher_sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLower();old_workers=0}
$taskReceipt | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/launch-$taskStamp.json" -Encoding utf8
$taskHelper=Start-Process -FilePath 'C:/Users/Axioo Pongo/AppData/Local/Programs/Ollama/ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput "$taskRoot/ollama-$taskStamp-stdout.log" -RedirectStandardError "$taskRoot/ollama-$taskStamp-stderr.log"
try {
    $taskReady=$false
    for ($taskCheck=0;$taskCheck -lt 30;$taskCheck++) {
        try {$taskVersion=Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -NoProxy -TimeoutSec 2;$taskReady=$true;break}
        catch {Start-Sleep -Milliseconds 250}
    }
    if (-not $taskReady) {throw 'Ollama helper unavailable: no inference sent.'}
    $taskVersion | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/ollama-version-$taskStamp.json"
    # Account authentication only; never log account identity or credential material.
    $taskMe=Invoke-WebRequest -Method Post -Uri 'http://127.0.0.1:11434/api/me' -NoProxy -TimeoutSec 15
    @{timestamp_utc=[DateTime]::UtcNow.ToString('o');authenticated=($taskMe.StatusCode -eq 200);http_status=$taskMe.StatusCode} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/auth-$taskStamp.json"
    & $taskPython "$taskRoot/pilot50.py" --verify
    if ($LASTEXITCODE -ne 0) {throw 'Freeze verification failed before inference.'}
    & $taskPython "$taskRoot/pilot50.py"
    $taskExit=$LASTEXITCODE
    & $taskPython "$taskRoot/analyze_pilot50.py"
    if ($LASTEXITCODE -ne 0) {throw 'Pilot report generation failed; raw attempts retained.'}
    if ($taskExit -ne 0) {throw "Pilot worker retained exit $taskExit; inspect records."}
} finally {
    if (-not $taskHelper.HasExited) {Stop-Process -Id $taskHelper.Id}
}
