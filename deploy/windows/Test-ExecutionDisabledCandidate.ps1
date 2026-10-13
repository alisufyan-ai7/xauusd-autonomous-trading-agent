[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string]$ReleaseRoot
)

$ErrorActionPreference = "Stop"
$SettingsPath = Join-Path $ReleaseRoot "deploy\windows\candidate.settings.json"
if (-not (Test-Path -LiteralPath $SettingsPath -PathType Leaf)) {
    throw "Candidate settings file is missing"
}

$Settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
if ($Settings.execution_enabled -ne $false) { throw "Execution must be disabled" }
if ($Settings.execution_mode -ne "DISABLED_NO_ADAPTER") { throw "Execution adapter must be absent" }
if ([int]$Settings.broker_action_count_limit -ne 0) { throw "Broker action limit must be zero" }
if ($Settings.analyst_transport_enabled -ne $false) { throw "Analyst transport requires separate approval" }
if ($Settings.alert_delivery_enabled -ne $false) { throw "Alert delivery requires separate approval" }

$ManifestPath = Join-Path $ReleaseRoot "release-manifest.json"
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Release manifest is missing"
}
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if ($Manifest.execution_enabled -ne $false) { throw "Manifest permits execution" }
if ([int]$Manifest.broker_action_count_limit -ne 0) { throw "Manifest broker action limit is not zero" }
foreach ($Entry in $Manifest.files) {
    if ([System.IO.Path]::IsPathRooted([string]$Entry.path) -or [string]$Entry.path -match "(^|[\\/])\.\.([\\/]|$)") {
        throw "Manifest contains an unsafe path"
    }
    $FilePath = Join-Path $ReleaseRoot ([string]$Entry.path)
    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) { throw "Manifest file missing: $($Entry.path)" }
    $File = Get-Item -LiteralPath $FilePath
    if ([int64]$File.Length -ne [int64]$Entry.size) { throw "Manifest size mismatch: $($Entry.path)" }
    $Digest = (Get-FileHash -LiteralPath $FilePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Digest -ne ([string]$Entry.sha256).ToLowerInvariant()) { throw "Manifest hash mismatch: $($Entry.path)" }
}

$ForbiddenPatterns = @(
    "order" + "_send\(",
    "TRADE" + "_ACTION_DEAL",
    "TRADE" + "_ACTION_PENDING",
    "position" + "_close\(",
    "order" + "_delete\("
)
$Sources = Get-ChildItem -LiteralPath $ReleaseRoot -Recurse -File |
    Where-Object { $_.Extension -in @(".py", ".ps1", ".psm1", ".json", ".toml", ".yaml", ".yml") }
foreach ($Pattern in $ForbiddenPatterns) {
    $Matches = $Sources | Select-String -Pattern $Pattern -CaseSensitive:$false
    if ($Matches) { throw "Forbidden capability detected: $Pattern" }
}

[pscustomobject]@{
    status = "PASS"
    execution_enabled = $false
    broker_action_count_limit = 0
    checked_utc = [DateTimeOffset]::UtcNow.ToString("o")
} | ConvertTo-Json
