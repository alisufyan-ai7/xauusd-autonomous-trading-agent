param(
  [Parameter(Mandatory=$true)][string]$Output,
  [Parameter(Mandatory=$true)][string]$BoundaryId,
  [Parameter(Mandatory=$true)][ValidateSet("BEFORE","INSIDE","AFTER")][string]$Phase
)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location -LiteralPath $repo
py -3.12 -m pip install --require-hashes -r "$PSScriptRoot\requirements-win-py312.txt"
if ($LASTEXITCODE -ne 0) { throw "Hash-pinned dependency installation failed." }
py -3.12 -m unittest -v phase0.validation.session_evidence.test_session_evidence
if ($LASTEXITCODE -ne 0) { throw "Offline session verifier tests failed." }
py -3.12 "$PSScriptRoot\capture_private_boundary.py" --output $Output --boundary-id $BoundaryId --phase $Phase
if ($LASTEXITCODE -ne 0) { throw "Boundary capture failed closed." }

