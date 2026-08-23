param(
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$packageRoot = [System.IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\') + '\'
$privateOutput = [System.IO.Path]::GetFullPath($Output)
if ($privateOutput.StartsWith($packageRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Private capture output must be outside the repository."
}

Write-Host "Gate 0 Event Guard: install hash-pinned Windows trust and timezone dependencies"
& py -3.12 -m pip install --disable-pip-version-check --require-hashes -r requirements-win-py312.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed; tests and capture were not run."
}

Write-Host "Gate 0 Event Guard: run offline conformance tests"
& py -3.12 -m unittest -v test_event_guard.py test_source_conformance.py
if ($LASTEXITCODE -ne 0) {
    throw "Offline conformance failed; private capture was not run."
}

Write-Host "Gate 0 Event Guard: capture read-only official-source evidence"
Write-Host "Private output must not be committed, emailed, or published: $privateOutput"
& py -3.12 .\capture_official_sources.py --output $privateOutput
$captureExit = $LASTEXITCODE
if ($captureExit -ne 0) {
    Write-Warning "Capture returned fail-closed status. Review its private JSON before continuing."
}

Write-Host "Gate 0 Event Guard: normalize captured schedules and prove horizon locally"
& py -3.12 .\normalize_private_capture.py --output $privateOutput
$normalizationExit = $LASTEXITCODE
if ($normalizationExit -ne 0) {
    Write-Warning "Normalization returned fail-closed status. Review the private normalized report."
}
if ($captureExit -ne 0) {
    exit $captureExit
}
exit $normalizationExit
