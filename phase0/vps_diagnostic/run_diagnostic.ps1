param([string]$Symbol = "XAUUSD", [int]$Hours = 24)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
Write-Host "Gate 0 READ-ONLY XAUUSD diagnostic v0.2.3"
Write-Host "Keep MT5 > Tools > Options > Expert Advisors > Disable automated trading via external Python API CHECKED."
py -3.12 verify_package.py
if ($LASTEXITCODE -ne 0) { throw "Safety verification failed. Stop." }
py -3.12 -m pip install --require-hashes -r requirements-win-py312.txt
if ($LASTEXITCODE -ne 0) { throw "Verified dependency installation failed. Stop." }
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$folder = "evidence-$stamp"
py -3.12 diagnostic.py --output $folder --symbol $Symbol --duration-seconds ($Hours * 3600) --interval-seconds 5
if ($LASTEXITCODE -ne 0) { throw "Diagnostic stopped safely. Do not send a partial run unless requested." }
Compress-Archive -LiteralPath $folder -DestinationPath "$folder.zip" -CompressionLevel Optimal
$zip = Get-Item -LiteralPath "$folder.zip"
$hash = (Get-FileHash -LiteralPath $zip.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$sidecar = "$($zip.FullName).sha256"
$line = "$hash  $($zip.Name)"
[System.IO.File]::WriteAllText($sidecar, $line + [Environment]::NewLine, [System.Text.Encoding]::ASCII)
Write-Host "Completed. Return only $folder.zip and $folder.zip.sha256"
