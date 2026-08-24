param(
  [Parameter(Mandatory=$true)][string]$Output,
  [Parameter(Mandatory=$true)][ValidateSet("PRE_DRILL","POST_RECOVERY")][string]$Phase
)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location -LiteralPath $repo
py -3.12 -m pip install --require-hashes -r "$PSScriptRoot\..\vps_reliability\requirements-win-py312.txt"
if ($LASTEXITCODE -ne 0) { throw "Hash-pinned dependency installation failed." }
py -3.12 -m unittest -v phase0.validation.exposure_preflight.test_exposure_preflight
if ($LASTEXITCODE -ne 0) { throw "Exposure preflight tests failed." }
py -3.12 "$PSScriptRoot\exposure_preflight.py" --output $Output --phase $Phase
if ($LASTEXITCODE -ne 0) { throw "Exposure preflight failed closed. Do not start or continue the drill." }
Write-Host "Read-only exposure counts passed. No order or broker state was mutated."
