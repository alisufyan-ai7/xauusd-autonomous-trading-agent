[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string]$ReleaseRoot,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9._-]+$")]
    [string]$ReleaseId,
    [string]$InstallRoot = "C:\ProgramData\XAUUSD-Agent",
    [Parameter(Mandatory = $true)]
    [ValidateSet("INSTALL-EXECUTION-DISABLED-CANDIDATE")]
    [string]$ConfirmToken
)

$ErrorActionPreference = "Stop"
$Preflight = Join-Path $ReleaseRoot "deploy\windows\Test-ExecutionDisabledCandidate.ps1"
& $Preflight -ReleaseRoot $ReleaseRoot | Out-Null

$Target = Join-Path (Join-Path $InstallRoot "releases") $ReleaseId
if (Test-Path -LiteralPath $Target) { throw "Release target already exists: $Target" }
if (-not $PSCmdlet.ShouldProcess($Target, "Stage execution-disabled production candidate")) { return }

New-Item -ItemType Directory -Path $Target -Force | Out-Null
Get-ChildItem -LiteralPath $ReleaseRoot -Force | Copy-Item -Destination $Target -Recurse -Force

$ActiveMarker = Join-Path $InstallRoot "active-release.txt"
$BackupMarker = Join-Path $InstallRoot "previous-release.txt"
if (Test-Path -LiteralPath $ActiveMarker -PathType Leaf) {
    Copy-Item -LiteralPath $ActiveMarker -Destination $BackupMarker -Force
}
$TemporaryMarker = Join-Path $InstallRoot "active-release.next"
Set-Content -LiteralPath $TemporaryMarker -Value $ReleaseId -Encoding utf8NoBOM
Move-Item -LiteralPath $TemporaryMarker -Destination $ActiveMarker -Force

[pscustomobject]@{
    status = "STAGED"
    release_id = $ReleaseId
    target = $Target
    service_started = $false
    execution_enabled = $false
} | ConvertTo-Json
