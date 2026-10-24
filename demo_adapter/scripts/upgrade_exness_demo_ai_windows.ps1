#requires -Version 5.1
<#
Upgrade the EXISTING hidden, interactive Windows ForexVPS Exness Pro DEMO
trader to one source-pinned AI+management release. Never creates another
task, switches accounts, or executes against LIVE. Must be flat at cutover.

OpenAI API key is collected privately on this VPS through SecureString,
stored encrypted with current Windows user's DPAPI, and injected only into
the child service process. No GitHub/raw key storage or echoed secrets.
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
    throw 'Target pinned version directory already exists. No overwrite or second writer.'
}
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
if (-not (Test-Path (Join-Path $Location 'demo_adapter\src\xauusd_demo\run_exness_demo.py'))) {
    throw 'Source release lacks runnable service entrypoint'
}
& $OldPython -m venv (Join-Path $Location '.venv')
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Python)) {
    throw 'New isolated Python environment unavailable'
}
& $Python -m pip --disable-pip-version-check install --no-input --no-cache-dir -e $Location -e (Join-Path $Location 'demo_adapter') 'tzdata>=2025.2'
if ($LASTEXITCODE -ne 0) { throw 'Pinned release dependency install failed' }
& $Python -u -m xauusd_demo.run_exness_demo --preflight
if ($LASTEXITCODE -ne 0) {
    throw 'New source broker account/flat preflight failed; original task remains running'
}

New-Item -ItemType Directory -Force -Path $LogFolder | Out-Null
if (-not (Test-Path -LiteralPath $KeyFile -PathType Leaf)) {
    Write-Host 'Enter the OpenAI API key locally. It is NOT printed or pushed to GitHub.'
    $Key = Read-Host 'OpenAI API key (secure prompt)' -AsSecureString
    $Cipher = ConvertFrom-SecureString -SecureString $Key
    Set-Content -LiteralPath $KeyFile -Value $Cipher -Encoding ASCII
    # Remove inherited ACL entries; only the interactive account can read.
    $CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $Acl = Get-Acl -LiteralPath $KeyFile
    $Acl.SetAccessRuleProtection($true,$false)
    foreach ($Rule in @($Acl.Access)) { [void]$Acl.RemoveAccessRuleAll($Rule) }
    $Access = New-Object System.Security.AccessControl.FileSystemAccessRule($CurrentUser,'FullControl','Allow')
    $Acl.AddAccessRule($Access)
    Set-Acl -LiteralPath $KeyFile -AclObject $Acl
}
function Get-LocalOpenAIKey {
    $Encrypted = Get-Content -LiteralPath $KeyFile -Raw
    $Secret = ConvertTo-SecureString $Encrypted
    $Address = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
    try {
        return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($Address)
    } finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Address)
    }
}
try {
    $env:OPENAI_API_KEY = Get-LocalOpenAIKey
    & $Python -u -m xauusd_demo.run_exness_demo --ai-preflight
    if ($LASTEXITCODE -ne 0) {
        throw 'OpenAI model/key auth preflight failed; old task untouched'
    }
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
Set-Location -LiteralPath $Location
try {
    $Encrypted = Get-Content -LiteralPath $SecretPath -Raw
    $Secret = ConvertTo-SecureString $Encrypted
    $Address = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
    try {
        $env:OPENAI_API_KEY = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($Address)
    } finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Address)
    }
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
$RunnerBody = $RunnerBody.Replace('__SRC__',$Location).Replace('__PY__',$Python).Replace('__LOG__',$LogFile).Replace('__SECRET__',$KeyFile)
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
