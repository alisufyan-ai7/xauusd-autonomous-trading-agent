#requires -Version 5.1
<#
Single owner-attended source-pinned deployment for the real Exness DEMO MT5 terminal.
This installer is not a simulation: it prepares, activates, and starts an
ongoing scheduled XAUUSD DE​​MO server trader. NEVER use a LIVE terminal.
No Git checkout in the existing VPS working tree. No repository credentials
or broker history copied to GitHub. Exact SourceCommit is supplied by operator.
To avoid changing unrelated scheduled tasks, refuses to replace an existing task.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[0-9a-f]{40}$')]
    [string]$SourceCommit,
    [string]$RepoPath = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent',
    [string]$TaskName = 'XAUUSD Exness Pro DEMO Autonomous Trader'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Branch = 'integration/real-exness-demo-v2-single-lineage-20261023'
$Root = Join-Path $env:ProgramData 'XAUUSD-DemoAutonomous'
$Versions = Join-Path $Root 'versions'
$Location = Join-Path $Versions $SourceCommit
$Zip = Join-Path $env:TEMP ("xauusd-demo-{0}.zip" -f $SourceCommit)
$Python = Join-Path $Location '.venv\Scripts\python.exe'
$Runner = Join-Path $Root 'run-current.ps1'
$LogFolder = Join-Path $env:LOCALAPPDATA 'XAUUSD-DemoService'
$Account = '{0}\{1}' -f $env:USERDOMAIN,$env:USERNAME

if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) {
    throw 'Expected Git repository does not exist. No change made.'
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw 'Existing autonomous DEMO scheduled task detected. Stop: use an explicit verified upgrade procedure, not a second writer.'
}
if (-not $env:LOCALAPPDATA -or -not $env:ProgramData) {
    throw 'Current Windows user application-data directories unavailable.'
}
if (Test-Path -LiteralPath $Location) {
    throw 'This exact source installation already exists; do not overwrite state.'
}
# Fetch into Git refs only, not the currently running/checked-out worktree.
& git -C $RepoPath fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
$Fetched = (& git -C $RepoPath rev-parse FETCH_HEAD | Out-String).Trim()
& git -C $RepoPath merge-base --is-ancestor $SourceCommit $Fetched
if ($LASTEXITCODE -ne 0) {
    throw 'Pinned reviewed commit is not an ancestor of the remote DEMO branch'
}
$HeadType = (& git -C $RepoPath cat-file -t $SourceCommit | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $HeadType -ne 'commit') {
    throw 'Reviewed source is not a locally fetched Git commit'
}
if (Test-Path -LiteralPath $Zip) { Remove-Item -LiteralPath $Zip -Force }
New-Item -ItemType Directory -Path $Versions -Force | Out-Null
try {
    # Git's short -o option must not be followed by '=...': that would
    # create an invalid '=C:/...' filename on Git for Windows.
    # Pass the documented long option and path as two separate argv tokens.
    & git -C $RepoPath archive --format=zip --output $Zip $SourceCommit
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Zip)) {
        throw 'Pinned source archive unavailable'
    }
    New-Item -ItemType Directory -Path $Location -Force | Out-Null
    Expand-Archive -LiteralPath $Zip -DestinationPath $Location
} finally {
    Remove-Item -LiteralPath $Zip -Force -ErrorAction SilentlyContinue
}
$Entry = Join-Path $Location 'demo_adapter\src\xauusd_demo\run_exness_demo.py'
if (-not (Test-Path -LiteralPath $Entry)) {
    throw 'Pinned source lacks a real DEMO service entrypoint'
}
# Do not assume a per-repository .venv exists. The VPS has previously
# demonstrated Python 3.12. Discover an actual 64-bit Python 3.12 installation
# via the Windows py launcher, PATH, or standard install paths. No installs,
# registry edits or PATH mutations are performed during discovery.
$PythonCandidates = New-Object 'System.Collections.Generic.List[string]'
$PyLauncher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
if ($null -ne $PyLauncher) {
    # A broken/missing optional py launcher must not terminate discovery:
    # Windows PowerShell 5.1 + Stop converts native stderr to an exception.
    try {
        $FromLauncher = @(& $PyLauncher.Source -3.12 -c 'import sys;print(sys.executable)' 2>$null)
        if ($LASTEXITCODE -eq 0) {
            foreach ($Candidate in $FromLauncher) {
                if ($Candidate) { $PythonCandidates.Add([string]$Candidate) }
            }
        }
    } catch {
        Write-Output 'PY_LAUNCHER_UNAVAILABLE__TRY_ALTERNATE_PYTHON'
    }
}
foreach ($Name in @('python.exe','python3.12.exe')) {
    $Found = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -ne $Found) { $PythonCandidates.Add([string]$Found.Source) }
}
$PythonCandidates.Add((Join-Path $RepoPath '.venv\Scripts\python.exe'))
$PythonCandidates.Add('C:\Python312\python.exe')
$PythonCandidates.Add('C:\Program Files\Python312\python.exe')
$PythonCandidates.Add((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'))
$PythonCandidates.Add((Join-Path $env:ProgramFiles 'Python312\python.exe'))
$BasePython = $null
foreach ($Candidate in ($PythonCandidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { continue }
    # NO embedded quotes: PowerShell 5.1's Windows native-argument escaping
    # otherwise changes a Python -c snippet into a SyntaxError.
    # sys.maxsize exactly identifies the required 64-bit interpreter.
    try {
        $VersionProof = @(& $Candidate -c 'import sys;print(sys.version_info.major,sys.version_info.minor,sys.maxsize)' 2>$null)
        if ($LASTEXITCODE -ne 0) { continue }
        if ((($VersionProof | Out-String).Trim()) -eq '3 12 9223372036854775807') {
            $BasePython = $Candidate
            break
        }
    } catch {
        # A broken candidate is not evidence that all installed Python
        # interpreters are absent. Try the next one without altering PATH.
        continue
    }
}
if ([string]::IsNullOrWhiteSpace($BasePython)) {
    throw 'No 64-bit Python 3.12 found via launcher, PATH or common installed locations; source extracted but NOTHING activated.'
}
Write-Output 'PYTHON_312_64BIT_DISCOVERY_PASS'
# Use a dedicated venv; never install packages into another application's Python.
& $BasePython -m venv (Join-Path $Location '.venv')
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Python)) {
    throw 'Isolated Python venv install failed'
}
& $Python -m pip --disable-pip-version-check install --no-input --no-cache-dir -e $Location -e (Join-Path $Location 'demo_adapter') 'tzdata>=2025.2'
if ($LASTEXITCODE -ne 0) { throw 'Python DEMO packages install failed' }
# Python preflight contacts the current terminal strictly read-only. No login switch.
& $Python -u -m xauusd_demo.run_exness_demo --preflight
if ($LASTEXITCODE -ne 0) {
    throw 'Read-only preflight failed. Verify exact Exness Pro DEMO account and MT5 Tools > Options > Expert Advisors external Python setting. NO TASK STARTED.'
}
# Exactly one operator-attended DEMO arm before the perpetual task starts.
& $Python -u -m xauusd_demo.run_exness_demo --activate
if ($LASTEXITCODE -ne 0) { throw 'DEMO activation failed; no task registered' }
New-Item -ItemType Directory -Path $LogFolder -Force | Out-Null
$LogFile = Join-Path $LogFolder 'service-console.log'
$RunnerContent = @'
$ErrorActionPreference = "Stop"
$SourceRoot = "__SRC_ROOT__"
$Python = "__PYTHON_PATH__"
$Log = "__LOGFILE__"
Set-Location -LiteralPath $SourceRoot
try {
    & $Python -u -m xauusd_demo.run_exness_demo --run *>> $Log
    $Code = $LASTEXITCODE
    Add-Content -LiteralPath $Log -Value ("SERVICE_EXIT_CODE={0} UTC={1}" -f $Code,[DateTime]::UtcNow.ToString("o"))
    exit $Code
} catch {
    Add-Content -LiteralPath $Log -Value ("SERVICE_EXCEPTION={0} UTC={1}" -f $_.Exception.GetType().Name,[DateTime]::UtcNow.ToString("o"))
    exit 1
}
'@
$RunnerContent = $RunnerContent.Replace('__SRC_ROOT__',$Location).Replace('__PYTHON_PATH__',$Python).Replace('__LOGFILE__',$LogFile)
Set-Content -LiteralPath $Runner -Value $RunnerContent -Encoding UTF8 -Force
# MT5 is in the interactive Exness DEMO desktop session; RDP disconnect is fine,
# a full Windows logoff will stop an Interactive task until next login.
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $Location -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}"' -f $Runner)
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $Account
$Principal = New-ScheduledTaskPrincipal -UserId $Account -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 4
$State = (Get-ScheduledTask -TaskName $TaskName).State
Write-Output "EXNESS_DEMO_SERVICE_INSTALLATION_COMPLETED"
Write-Output "PINNED_COMMIT=$SourceCommit"
Write-Output "SCHEDULED_TASK=$TaskName"
Write-Output "TASK_STATE=$State"
Write-Output "SCHEDULED_USER=$Account"
Write-Output "SERVICE_CONSOLE_LOG=$LogFile"
Write-Output "CYCLE_LOG=$(Join-Path $LogFolder 'cycles.jsonl')"
Write-Output "NEVER_LIVE__ONLY_PINNED_EXNESS_DEMO"
Write-Output 'To inspect: Get-Content "$env:LOCALAPPDATA\XAUUSD-DemoService\service-console.log" -Tail 60'
Write-Output 'To inspect cycles: Get-Content "$env:LOCALAPPDATA\XAUUSD-DemoService\cycles.jsonl" -Tail 30'
Write-Output 'To stop: Stop-ScheduledTask -TaskName "XAUUSD Exness Pro DEMO Autonomous Trader"'
