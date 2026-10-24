#requires -Version 5.1
<#
Upgrade the EXISTING hidden, interactive Windows ForexVPS Exness Pro DEMO
trader to one source-pinned AI+management release. Never creates another
task, switches accounts, or executes against LIVE. Must be flat at cutover.

OpenAI API key comes from the existing Windows user environment variable.
A previous DPAPI encrypted file is a fallback only. No duplicate key or
interactive prompt is introduced; never echo or upload any secret.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[a-f0-9]{40}$')]
    [string]$SourceCommit,
    [string]$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Branch = 'integration/real-exness-demo-v2-single-lineage-20261023'
$TaskName = 'XAUUSD Exness Pro DEMO Autonomous Trader'
$Root = Join-Path $env:ProgramData 'XAUUSD-DemoAutonomous'
$Location = Join-Path (Join-Path $Root 'versions') $SourceCommit
$OldCommit = 'efab8be64b97cad464932cf7cf6cac034134e800'
$OldLocation = Join-Path (Join-Path $Root 'versions') $OldCommit
$OldPython = Join-Path $OldLocation '.venv\Scripts\python.exe'
$Python = Join-Path $Location '.venv\Scripts\python.exe'
$Runner = Join-Path $Root 'run-current.ps1'
$LogFolder = Join-Path $env:LOCALAPPDATA 'XAUUSD-DemoService'
$LogFile = Join-Path $LogFolder 'service-console.log'
$KeyFile = Join-Path $LogFolder 'openai_key.dpapi'
$Zip = Join-Path $env:TEMP ("xauusd-AI-" + $SourceCommit + ".zip")
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if (
    -not (Test-Path -LiteralPath $OldPython -PathType Leaf) -or
    -not (Test-Path -LiteralPath $Runner -PathType Leaf) -or
    $Task.Actions.Count -ne 1 -or
    $Task.Principal.LogonType -ne 'Interactive' -or
    $Task.Actions[0].WorkingDirectory -ne $OldLocation -or
    $Task.Actions[0].Arguments -notlike '*run-current.ps1*' -or
    $Task.State -ne 'Running'
) {
    throw 'Existing pinned interactive DEMO task not in expected healthy state; no upgrade performed'
}
if (Test-Path -LiteralPath $Location) {
    Write-Host 'EXISTING_PARTIAL_STAGE_FOUND__VERIFY_BEFORE_REUSE'
}
$PreviouslyStaged = Test-Path -LiteralPath $Location
$OriginalAction = $Task.Actions[0]
$OriginalRunner = Get-Content -LiteralPath $Runner -Raw
$OriginalTaskState = $Task.State
if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw 'Expected Git source checkout missing'
}

# Stage the exact reviewed code without changing any running branch.
& git -C $Repo fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'Source fetch failed' }
& git -C $Repo merge-base --is-ancestor $SourceCommit FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Reviewed source no longer in integration lineage' }
if (-not $PreviouslyStaged) {
    New-Item -ItemType Directory -Force -Path $Location | Out-Null
    try {
        & git -C $Repo archive --format=zip --output $Zip $SourceCommit
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Zip)) {
            throw 'Pinned source archive failed'
        }
        Expand-Archive -LiteralPath $Zip -DestinationPath $Location
    } finally {
        Remove-Item -LiteralPath $Zip -Force -ErrorAction SilentlyContinue
    }
} else {
    $OldModule = Join-Path $Location 'demo_adapter\src\xauusd_demo\run_exness_demo.py'
    if (-not (Test-Path -LiteralPath $OldModule)) {
        throw 'Existing staged release incomplete; no task modified'
    }
    $ExpectedModule = @(& git -C $Repo show ("${SourceCommit}:demo_adapter/src/xauusd_demo/run_exness_demo.py"))
    if ($LASTEXITCODE -ne 0) { throw 'Unable to verify staged release' }
    $OnDiskModule = @(Get-Content -LiteralPath $OldModule)
    if (($ExpectedModule -join "`n") -ne ($OnDiskModule -join "`n")) {
        throw 'Existing stage differs from source-pinned Git content'
    }
}
if (-not (Test-Path (Join-Path $Location 'demo_adapter\src\xauusd_demo\run_exness_demo.py'))) {
    throw 'Source release lacks runnable service entrypoint'
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    & $OldPython -m venv (Join-Path $Location '.venv')
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Python)) {
        throw 'New isolated Python environment unavailable'
    }
}
& $Python -m pip --disable-pip-version-check install --no-input --no-cache-dir -e $Location -e (Join-Path $Location 'demo_adapter') 'tzdata>=2025.2'
if ($LASTEXITCODE -ne 0) { throw 'Pinned release dependency install failed' }
& $Python -u -m xauusd_demo.run_exness_demo --preflight
if ($LASTEXITCODE -ne 0) {
    throw 'New source broker account/flat preflight failed; original task remains running'
}

New-Item -ItemType Directory -Force -Path $LogFolder | Out-Null
function Get-ServiceOpenAIKey {
    # An existing Windows user environment variable is the owner's intended
    # credential source. No duplicate DPAPI secret is created or requested.
    $FromUser = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'User')
    if (-not [string]::IsNullOrWhiteSpace($FromUser)) {
        return $FromUser.Trim()
    }
    if (-not [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
        return $env:OPENAI_API_KEY.Trim()
    }
    # Legacy compatibility only: prefer environment variables, never force a
    # new interactive key prompt if the operator already provisioned one.
    if (Test-Path -LiteralPath $KeyFile -PathType Leaf) {
        $Encrypted = (Get-Content -LiteralPath $KeyFile -Raw -ErrorAction Stop).Trim()
        $Secret = ConvertTo-SecureString -String $Encrypted -ErrorAction Stop
        $Pointer = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
        try {
            return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
        } finally {
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer)
        }
    }
    throw 'OPENAI_API_KEY unavailable to current Windows task user; configure its user environment variable'
}
try {
    $env:OPENAI_API_KEY = Get-ServiceOpenAIKey
    if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
        throw 'OPENAI_API_KEY empty'
    }
    Write-Host 'OPENAI_KEY_FOUND_IN_CURRENT_WINDOWS_ACCOUNT__KEY_NOT_PRINTED'
    # For THIS key/project, list available models and test an actual strict
    # Responses API result (small non-trading paid inference). This avoids
    # the previous false 404 from hard-coding /v1/models/gpt-6-luna.
    $ModelProof = @(& $Python -u -m xauusd_demo.run_exness_demo --ai-preflight)
    if ($LASTEXITCODE -ne 0) {
        throw 'OpenAI project-model / strict Responses capability check failed; old task untouched'
    }
    $ModelLines = @($ModelProof | Where-Object {
        [string]$_ -match '^OPENAI_MODEL_READY:[a-zA-Z0-9.-]+
    })
    if ($ModelLines.Count -ne 1) {
        throw 'No single approved model confirmed by OpenAI preflight'
    }
    $SelectedModel = ([string]$ModelLines[0]).Split(':')[1]
    if ($SelectedModel -notin @('gpt-6-luna','gpt-6.1-sol','gpt-5-mini','gpt-4.1-mini')) {
        throw 'Unreviewed model selected'
    }
    Write-Host ('VERIFIED_OPENAI_API_MODEL=' + $SelectedModel)
} finally {
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
}

# Pre-build runner and verify execution before replacing original script.
$RunnerBody = @'
$ErrorActionPreference = 'Stop'
$Location = '__SRC__'
$Python = '__PY__'
$Log = '__LOG__'
$SecretPath = '__SECRET__'
$env:XAUUSD_OPENAI_MODEL = '__MODEL__'
Set-Location -LiteralPath $Location
try {
    $Value = $env:OPENAI_API_KEY
    if ([string]::IsNullOrWhiteSpace($Value)) {
        $Value = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY','User')
    }
    if ([string]::IsNullOrWhiteSpace($Value) -and
        (Test-Path -LiteralPath $SecretPath -PathType Leaf)) {
        $Encrypted = (Get-Content -LiteralPath $SecretPath -Raw).Trim()
        $Secret = ConvertTo-SecureString -String $Encrypted
        $Ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
        try {
            $Value = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($Ptr)
        } finally {
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Ptr)
        }
    }
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw 'OPENAI_API_KEY not visible to scheduled task user'
    }
    $env:OPENAI_API_KEY = $Value.Trim()
    Remove-Variable Value -ErrorAction SilentlyContinue
    if ((Test-Path -LiteralPath $Log) -and
        (Get-Item -LiteralPath $Log).Length -gt 4MB) {
        $Old = $Log + '.1'
        Remove-Item -LiteralPath $Old -Force -ErrorAction SilentlyContinue
        Move-Item -LiteralPath $Log -Destination $Old
    }
    & $Python -u -m xauusd_demo.run_exness_demo --run *>> $Log
    $Code = $LASTEXITCODE
    Add-Content -LiteralPath $Log -Value ("EXIT_CODE={0}" -f $Code)
    exit $Code
} catch {
    Add-Content -LiteralPath $Log -Value ("WORKER_ERROR_TYPE={0}" -f $_.Exception.GetType().Name)
    exit 1
} finally {
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
}
'@
$RunnerBody = $RunnerBody.Replace('__SRC__',$Location).Replace('__PY__',$Python).Replace('__LOG__',$LogFile).Replace('__SECRET__',$KeyFile).Replace('__MODEL__',$SelectedModel)
$NewAction = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $Location -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}"' -f $Runner)
Write-Host 'STOPPING_ONLY_THE_EXISTING_DEMO_TASK_FOR_CONTROLLED_UPGRADE'
Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop
for ($i=0; $i -lt 60; $i++) {
    if ((Get-ScheduledTask -TaskName $TaskName).State -ne 'Running') { break }
    Start-Sleep -Milliseconds 500
}
if ((Get-ScheduledTask -TaskName $TaskName).State -eq 'Running') {
    throw 'Old task refused to stop; upgrade aborted'
}
$Existing = @()
for ($i=0; $i -lt 30; $i++) {
    $Existing = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.ExecutablePath -and
            [string]::Equals([string]$_.ExecutablePath,[string]$OldPython,[StringComparison]::OrdinalIgnoreCase)
        })
    if ($Existing.Count -eq 0) { break }
    Start-Sleep -Milliseconds 500
}
if ($Existing.Count -gt 0) {
    throw 'Old Python broker writer still alive; no second writer started'
}
$Switched = $false
try {
    # Repeat the broker-flat test after stopping the old process to close
    # the race between the first preflight and an unexpected order.
    & $Python -u -m xauusd_demo.run_exness_demo --preflight
    if ($LASTEXITCODE -ne 0) { throw 'Broker not flat at actual upgrade instant' }
    Set-Content -LiteralPath $Runner -Value $RunnerBody -Encoding UTF8
    Set-ScheduledTask -TaskName $TaskName -Action $NewAction -ErrorAction Stop | Out-Null
    $Switched = $true
    $StartedUTC = [DateTime]::UtcNow
    Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    Start-Sleep -Seconds 12
    $Running = Get-ScheduledTask -TaskName $TaskName
    $Health = Join-Path $LogFolder 'health.json'
    if (
        $Running.State -ne 'Running' -or
        -not (Test-Path -LiteralPath $Health) -or
        (Get-Item -LiteralPath $Health).LastWriteTimeUtc -lt $StartedUTC.AddSeconds(-2)
    ) {
        throw 'New DEMO worker failed fresh-health startup; rollback required'
    }
    Write-Host 'EXNESS_AI_DEMO_UPGRADE_RUNNING'
    Write-Host ('PINNED_HEAD=' + $SourceCommit)
    Write-Host ('TASK=' + $TaskName)
    Get-Content -LiteralPath $Health
} catch {
    Write-Host 'UPGRADE_FAILED_RESTORING_PREVIOUS_TASK_CONFIGURATION'
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Set-Content -LiteralPath $Runner -Value $OriginalRunner -Encoding UTF8
    Set-ScheduledTask -TaskName $TaskName -Action $OriginalAction -ErrorAction Stop | Out-Null
    if ($OriginalTaskState -eq 'Running') {
        # A new broker order may have been accepted before startup failed.
        # Never restart the old trader until broker exposure is verified flat.
        # Its durable coordinator still protects against blind duplicate orders.
        & $OldPython -u -m xauusd_demo.run_exness_demo --preflight
        if ($LASTEXITCODE -eq 0) {
            $NewWorkers = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
                Where-Object { $_.ExecutablePath -and
                    [string]::Equals([string]$_.ExecutablePath,[string]$Python,[StringComparison]::OrdinalIgnoreCase)
                })
            if ($NewWorkers.Count -eq 0) {
                Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
            } else {
                Write-Warning 'New Python child remains alive; old task NOT restarted'
            }
        } else {
            Write-Warning 'Account no longer broker-flat; old task NOT restarted'
        }
    }
    throw
}
