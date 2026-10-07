param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location -LiteralPath $repo
py -3.12 -m unittest -v phase0.validation.alert_evidence.test_alert_evidence phase0.validation.alert_evidence.test_private_delivery_evidence
if ($LASTEXITCODE -ne 0) { throw "Private alert evidence tests failed." }
py -3.12 "$PSScriptRoot\private_delivery_evidence.py" --output $Output verify
if ($LASTEXITCODE -ne 0) { throw "Private dual-path delivery evidence failed closed." }
Write-Host "A1 delivery evidence passed only within its claim limit. No trading authority was restored."
