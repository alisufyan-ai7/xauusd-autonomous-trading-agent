param(
  [Parameter(Mandatory=$true)][string]$Output,
  [Parameter(Mandatory=$true)][ValidateSet("BASELINE","DISCONNECT","RECONNECT","PYTHON_RESTART","MT5_RESTART","WINDOWS_RESTART","CLOCK_CHECK","BUILD_CHECK")][string]$Event,
  [Parameter(Mandatory=$true)][string]$ScenarioId,
  [string]$CompatibilitySha256 = ""
)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location -LiteralPath $repo
py -3.12 -m pip install --require-hashes -r "$PSScriptRoot\requirements-win-py312.txt"
if ($LASTEXITCODE -ne 0) { throw "Hash-pinned dependency installation failed." }
py -3.12 -m unittest -v phase0.validation.vps_reliability.test_reliability_oracle phase0.validation.vps_reliability.test_private_probe
if ($LASTEXITCODE -ne 0) { throw "Offline VPS tests failed." }
$private = [System.IO.Path]::GetFullPath($Output)
[System.IO.Directory]::CreateDirectory($private) | Out-Null
$clock = Join-Path $private ("w32tm-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + ".txt")
& w32tm.exe /query /status /verbose | Out-File -LiteralPath $clock -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "Windows Time status capture failed." }
$boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString("o")
$terminal = Get-Process -Name terminal64 -ErrorAction Stop | Sort-Object StartTime | Select-Object -Last 1
$mt5Start = $terminal.StartTime.ToUniversalTime().ToString("o")
$arguments = @("$PSScriptRoot\private_probe.py","--output",$private,"--event",$Event,"--scenario-id",$ScenarioId,"--os-boot-utc",$boot,"--mt5-start-utc",$mt5Start,"--w32tm-status-file",$clock)
if ($CompatibilitySha256) { $arguments += @("--compatibility-sha256",$CompatibilitySha256) }
py -3.12 @arguments
if ($LASTEXITCODE -ne 0) { throw "Private probe failed closed." }
Write-Host "This wrapper only observed the requested state; it did not cause a restart, outage or reconnect."
