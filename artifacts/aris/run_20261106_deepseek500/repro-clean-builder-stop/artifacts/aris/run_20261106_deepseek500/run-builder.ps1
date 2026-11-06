$ErrorActionPreference = 'Stop'
$studyRun = $PSScriptRoot
$studyRoot = (Resolve-Path -LiteralPath "$studyRun/../../..").Path
Set-Location -LiteralPath $studyRoot
$studyPython = Join-Path $studyRoot '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath "$studyRun/running.lock") { throw 'Inspect the coordinator lock and last journal before resume.' }
if (Get-Process -Name python,pythonw,ollama -ErrorAction SilentlyContinue) { throw 'Inspect existing Python and Ollama processes before starting a worker.' }
$env:OMP_NUM_THREADS = '2'
$env:MKL_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
$env:NUMEXPR_NUM_THREADS = '2'
$env:VECLIB_MAXIMUM_THREADS = '2'
$env:PYTHONUTF8 = '1'
Remove-Item Env:PYTHONOPTIMIZE -ErrorAction SilentlyContinue
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$keyLine = Get-Content -LiteralPath (Join-Path $studyRoot '.env') | Where-Object { $_ -match '^\s*TINYFISH_API_KEY\s*=' } | Select-Object -First 1
$studyTinyFishKey = ($keyLine -split '=',2)[1].Trim().Trim('"').Trim("'")
$wallet = Invoke-RestMethod -Uri 'https://agent.tinyfish.ai/v1/wallet' -Headers @{'X-API-Key'=$studyTinyFishKey} -TimeoutSec 20 -MaximumRedirection 0
$studyRates = @{}
foreach ($product in 'search','fetch') {
    $meter = @($wallet.rates.meters | Where-Object {$_.label -eq "TinyFish $product"})
    if ($meter.Count -ne 1) { throw "Missing wallet $product tariff." }
    $studyRates[$product] = [string]$meter[0].unit_amount
}
@{
    amendment_sha256 = (Get-FileHash -LiteralPath "$studyRun/builder-amendment.json").Hash.ToLowerInvariant()
    checked_at = [DateTime]::UtcNow.ToString('o')
    currency = $wallet.currency
    auto_reload = $wallet.auto_reload.state
    balance = [string]$wallet.available_balance
    rates_as_of = $wallet.rates.as_of
    rates = $studyRates
} | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 -LiteralPath "$studyRun/builder-wallet-current.json"
& $studyPython "$studyRun/builder.py" --verify
if ($LASTEXITCODE -ne 0) { throw 'Builder wallet terms or frozen run verification failed.' }
$studyStamp = [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fffffff')
$studyStarted = [DateTime]::UtcNow
$studyHelper = Start-Process -FilePath 'C:/Users/Axioo Pongo/AppData/Local/Programs/Ollama/ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput "$studyRun/ollama-$studyStamp-out.log" -RedirectStandardError "$studyRun/ollama-$studyStamp-err.log"
try {
    $studyVersion = $null
    for ($i = 0; $i -lt 30; $i++) {
        try { $studyVersion = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -NoProxy -TimeoutSec 2; break }
        catch { Start-Sleep -Milliseconds 250 }
    }
    if ($studyVersion.version -ne '0.34.0') { throw 'The archived Ollama version is unavailable.' }
    $studyAuth = Invoke-WebRequest -Method Post -Uri 'http://127.0.0.1:11434/api/me' -NoProxy -TimeoutSec 15
    if ($studyAuth.StatusCode -ne 200) { throw 'Ollama account authentication is unavailable.' }
    @{
        started_at = $studyStarted.ToString('o')
        coordinator_ready_at = [DateTime]::UtcNow.ToString('o')
        protocol_sha256 = (Get-FileHash -LiteralPath "$studyRun/protocol.json").Hash.ToLowerInvariant()
        launcher_sha256 = (Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()
        ollama_version = $studyVersion.version
        ollama_pid = $studyHelper.Id
        authenticated = $true
    } | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath "$studyRun/launch-$studyStamp.json"
    & $studyPython "$studyRun/builder.py" --run
    if ($LASTEXITCODE -ne 0) { throw 'Coordinator stopped. Inspect the journal before resuming.' }
} finally {
    if (-not $studyHelper.HasExited) { Stop-Process -Id $studyHelper.Id }
}

