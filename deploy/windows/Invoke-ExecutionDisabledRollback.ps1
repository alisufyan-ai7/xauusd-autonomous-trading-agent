[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$InstallRoot = "C:\ProgramData\XAUUSD-Agent",
    [Parameter(Mandatory = $true)]
    [ValidateSet("ROLLBACK-EXECUTION-DISABLED-CANDIDATE")]
    [string]$ConfirmToken
)

$ErrorActionPreference = "Stop"
$PreviousMarker = Join-Path $InstallRoot "previous-release.txt"
if (-not (Test-Path -LiteralPath $PreviousMarker -PathType Leaf)) { throw "Previous release marker missing" }
$PreviousRelease = (Get-Content -LiteralPath $PreviousMarker -Raw).Trim()
if ($PreviousRelease -notmatch "^[A-Za-z0-9._-]+$") { throw "Previous release identifier is invalid" }
$PreviousRoot = Join-Path (Join-Path $InstallRoot "releases") $PreviousRelease
$Preflight = Join-Path $PreviousRoot "deploy\windows\Test-ExecutionDisabledCandidate.ps1"
& $Preflight -ReleaseRoot $PreviousRoot | Out-Null

$ActiveMarker = Join-Path $InstallRoot "active-release.txt"
if (-not $PSCmdlet.ShouldProcess($ActiveMarker, "Repoint to verified execution-disabled release $PreviousRelease")) { return }
$TemporaryMarker = Join-Path $InstallRoot "active-release.rollback"
Set-Content -LiteralPath $TemporaryMarker -Value $PreviousRelease -Encoding utf8NoBOM
Move-Item -LiteralPath $TemporaryMarker -Destination $ActiveMarker -Force

[pscustomobject]@{
    status = "ROLLED_BACK_MARKER"
    release_id = $PreviousRelease
    service_restarted = $false
    reconciliation_required = $true
} | ConvertTo-Json
