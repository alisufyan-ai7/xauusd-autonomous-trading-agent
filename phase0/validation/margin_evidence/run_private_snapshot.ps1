param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location -LiteralPath $repo
py -3.12 -m pip install --require-hashes -r "$PSScriptRoot\requirements-win-py312.txt"
if ($LASTEXITCODE -ne 0) { throw "Hash-pinned dependency installation failed." }
py -3.12 -m unittest -v phase0.validation.margin_evidence.test_margin_evidence
if ($LASTEXITCODE -ne 0) { throw "Offline M1 evidence tests failed." }
py -3.12 "$PSScriptRoot\capture_private_snapshot.py" --output $Output
if ($LASTEXITCODE -ne 0) { throw "Private snapshot failed closed." }
Write-Host "Keep exact margin/equity inputs outside the repository."

