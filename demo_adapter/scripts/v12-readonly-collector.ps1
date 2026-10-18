#requires -Version 5.1
<#
  NOT APPROVED TO RUN. Frozen future 4h Exness DEMO XAUUSD read-only ONLY.
  Independent source/authenticity and EXACT OWNER FIRST-RUN confirmation required.
  No scheduled task mutation, terminal login, trading enablement or order methods.
  MetaTrader5.initialize may launch a terminal: refuse unless exact terminal.exe
  already runs; operator must separately confirm that attach is acceptable.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepositoryRoot,
    [Parameter(Mandatory=$true)][string]$RegistrationPath,
    [Parameter(Mandatory=$true)][string]$RegistrationSHA256,
    [Parameter(Mandatory=$true)][string]$CollectorSHA256,
    [Parameter(Mandatory=$true)][string]$VerifierSHA256,
    [Parameter(Mandatory=$true)][string]$HostSHA256,
    [Parameter(Mandatory=$true)][string]$ExistingTerminalExe,
    [Parameter(Mandatory=$true)][string]$PrivateOutputPath,
    [Parameter(Mandatory=$true)][string]$OwnerFirstRunConfirmationId
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Assert-FileHash([string]$Path,[string]$Digest,[string]$Label) {
    if ($Digest -cnotmatch '^[a-f0-9]{64}$') { throw "$Label UNVERIFIED_SHA256" }
    if (-not [IO.File]::Exists($Path)) { throw "$Label FILE_MISSING" }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne $Digest) { throw "$Label HASH_MISMATCH" }
}
function Resolve-Existing([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "EXACT_EXISTING_FILE_REQUIRED"
    }
    return [IO.Path]::GetFullPath($Path)
}
if ($OwnerFirstRunConfirmationId -eq "PENDING" -or
    [string]::IsNullOrWhiteSpace($OwnerFirstRunConfirmationId)) {
    throw "OWNER_FIRST_RUN_CONFIRMATION_NOT_RECORDED"
}
$repo = [IO.Path]::GetFullPath($RepositoryRoot)
$registration = Resolve-Existing $RegistrationPath
$script = Resolve-Existing $MyInvocation.MyCommand.Path
$hostPy = Resolve-Existing (Join-Path $repo "demo_adapter\scripts\v12_windows_mt5_readonly_host.py")
$verifier = Resolve-Existing (Join-Path $repo "demo_adapter\scripts\v12-readonly-verifier.ps1")
$terminal = Resolve-Existing $ExistingTerminalExe
$output = [IO.Path]::GetFullPath($PrivateOutputPath)
Assert-FileHash $script $CollectorSHA256 "COLLECTOR"
Assert-FileHash $verifier $VerifierSHA256 "INDEPENDENT_VERIFIER"
Assert-FileHash $hostPy $HostSHA256 "PYTHON_HOST"
Assert-FileHash $registration $RegistrationSHA256 "PROSPECTIVE_REGISTRATION"

# Do not allow private data to be written under any repository or existing file.
if ($output.StartsWith($repo + [IO.Path]::DirectorySeparatorChar,
    [StringComparison]::OrdinalIgnoreCase) -or
    [IO.File]::Exists($output) -or
    -not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($output))) {
    throw "PRIVATE_OUTPUT_MUST_BE_NEW_AND_OUTSIDE_REPOSITORY"
}
$record = Get-Content -LiteralPath $registration -Raw -Encoding UTF8 | ConvertFrom-Json
if ($record.approved_pr13_design_sha -cne
    "847829378956670e8936bf46c82e685de41145fd" -or
    $record.approved_pr14_evidence_sha -cne
    "9d768fcfd160b3ccfc92ecef44fe040da6b77db6" -or
    $record.owner_first_run_confirmation_id -cne $OwnerFirstRunConfirmationId -or
    $record.exact_owner_approval_id -cne $OwnerFirstRunConfirmationId -or
    $record.approval_for_vps_capture -cne "EXPLICIT_OWNER_APPROVED" -or
    $record.collector_ps_sha256 -cne $CollectorSHA256 -or
    $record.verifier_ps_sha256 -cne $VerifierSHA256) {
    throw "NO_EXACT_OWNER_AND_CODE_PINNED_CAPTURE_REGISTRATION"
}
# Program methods are frozen; the other core Python source hashes must be
# pre-registered, as must exact Exness XAUUSD sessions, Event Guard and costs.
$required = @{
 "demo_adapter\scripts\v11_capture_orchestrator.py" = [string]$record.read_only_core_source_sha256
 "demo_adapter\scripts\v11_readonly_collector.py" = [string]$record.read_only_preflight_source_sha256
 "demo_adapter\scripts\v11_quote_coverage.py" = [string]$record.quote_protocol_source_sha256
 "demo_adapter\scripts\v11_windows_mt5_readonly_host.py" = [string]$record.mt5_bound_port_source_sha256
}
foreach ($relative in $required.Keys) {
    Assert-FileHash (Join-Path $repo $relative) $required[$relative] $relative
}
$python = Resolve-Existing (Join-Path $repo ".venv\Scripts\python.exe")
$running = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and
        $_.Path.Equals($terminal,[StringComparison]::OrdinalIgnoreCase) })
if ($running.Count -ne 1 -or [IO.Path]::GetFileName($terminal).ToLowerInvariant() -ne "terminal64.exe") {
    throw "EXACT_SINGLE_EXISTING_MT5_TERMINAL_NOT_CONFIRMED"
}
$initialPid = [int]$running[0].Id
$oldLocation = (Get-Location).Path
$oldBytecode = $env:PYTHONDONTWRITEBYTECODE
try {
    $env:PYTHONDONTWRITEBYTECODE = "1"
    Set-Location (Join-Path $repo "demo_adapter")
    & $python -B -m scripts.v12_windows_mt5_readonly_host `
        --registration $registration `
        --registration-sha256 $RegistrationSHA256 `
        --host-sha256 $HostSHA256 `
        --owner-run-id $OwnerFirstRunConfirmationId `
        --terminal-path $terminal `
        --private-output $output
    if ($LASTEXITCODE -ne 0) {
        throw "READ_ONLY_CAPTURE_REJECTED_NO_ADMISSION"
    }
}
finally {
    Set-Location $oldLocation
    $env:PYTHONDONTWRITEBYTECODE = $oldBytecode
    $post = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and
            $_.Path.Equals($terminal,[StringComparison]::OrdinalIgnoreCase) })
    if ($post.Count -ne 1 -or [int]$post[0].Id -ne $initialPid) {
        Write-Error "TERMINAL_PROCESS_SET_CHANGED_REJECT_CAPTURE_AND_INVESTIGATE"
    }
}
Write-Output "COLLECTION_FINISHED_RAW_HASH_ONLY_INDEPENDENT_VERIFIER_REQUIRED"
