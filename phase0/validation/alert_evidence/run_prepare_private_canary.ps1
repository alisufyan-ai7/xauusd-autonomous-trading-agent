param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location -LiteralPath $repo
py -3.12 -m unittest -v phase0.validation.alert_evidence.test_alert_evidence
if ($LASTEXITCODE -ne 0) { throw "Offline alert verifier tests failed." }
py -3.12 "$PSScriptRoot\prepare_private_canary.py" --output $Output
if ($LASTEXITCODE -ne 0) { throw "Canary preparation failed closed." }
Write-Host "Nothing was sent. Keep both generated files private."
