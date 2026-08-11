param(
    [string]$Symbol = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "Phase 0 read-only MT5 evidence collector"
Write-Host "No order, modification, cancellation, close, login, or symbol-selection call exists in the collector."
Write-Host ""
Write-Host "Required MT5 setting: Tools > Options > Expert Advisors >"
Write-Host "  CHECK 'Disable automated trading via external Python API'"
Write-Host "The collector will abort before account/market capture if MT5 does not report that protection as enabled."
Write-Host ""

py -3.12 verify_readonly.py --self-test --verify-manifest PACKAGE_MANIFEST.sha256 --output-json PRE_RUN_VERIFICATION.json
if ($LASTEXITCODE -ne 0) {
    throw "Read-only verification failed. Do not run the collector."
}

& py -3.12 -c "import MetaTrader5"
if ($LASTEXITCODE -ne 0) {
    throw "MetaTrader5 Python package is missing. Install it with: py -3.12 -m pip install --require-hashes -r requirements-win-py312.txt"
}

& py -3.12 -c "import importlib.metadata as m, sys; expected={'MetaTrader5':'5.0.6090','numpy':'2.5.0'}; actual={k:m.version(k) for k in expected}; print('Verified dependencies: ' + ', '.join(f'{k}=={v}' for k,v in actual.items())); sys.exit(0 if actual == expected else 2)"
if ($LASTEXITCODE -ne 0) {
    throw "Installed dependency versions do not match the verified collector lock. Reinstall with: py -3.12 -m pip install --force-reinstall --require-hashes -r requirements-win-py312.txt"
}

$arguments = @("-3.12", "collector.py", "--output-root", "evidence-output")
if ($Symbol -ne "") {
    $arguments += @("--symbol", $Symbol)
}

$resultText = & py @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Collector stopped safely. Read the message above, correct the condition, and rerun."
}
$result = $resultText | ConvertFrom-Json
$evidenceDirectory = $result.output_directory
$archivePath = "$evidenceDirectory.zip"
Compress-Archive -LiteralPath $evidenceDirectory -DestinationPath $archivePath -CompressionLevel Optimal
$archiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$archivePath.sha256" -Encoding ASCII -NoNewline -Value "$archiveHash  $([System.IO.Path]::GetFileName($archivePath))`n"

Write-Host ""
Write-Host "Completed with status: $($result.status)"
Write-Host "Send only these two files; never send an MT5 password or login identifier:"
Write-Host "  $archivePath"
Write-Host "  $archivePath.sha256"
Write-Host "SHA-256: $archiveHash"
