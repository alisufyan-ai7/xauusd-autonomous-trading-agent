# PROPOSED OWNER-ATTENDED OS-ONLY READ-ONLY PREFLIGHT.
# Requires separate owner approval to run on VPS. NEVER invokes MT5 Python API.
# Does not create/delete files, change tasks/settings, stage or capture anything.
& {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'

    if ($PSVersionTable.PSVersion.Major -ne 5 -or
        $PSVersionTable.PSVersion.Minor -ne 1) {
        throw 'V11_OS_PREFLIGHT_WINDOWS_PS51_ONLY'
    }

    $Stage = Join-Path $env:LOCALAPPDATA 'XAUUSD-DEMO-V11-READONLY'
    $ExpectedManifest = 'b0abedcf7fd86dd93ee2ea959f279453bbf80f19d96de619a385f8799edf5b7f'
    $Expected = @{
        'v11_policy_a_source_bridge.py' = '1d772ba2c7c28dcdbea0193aba56e83c996be144f2abbef69503ca1558cb458e'
        'v11_quote_coverage.py' = '0c679a7c92d5dd6c131569eb48565dc4cea92f0c8322070dc7838ff1d4ee2aba'
        'v11_readonly_collector.py' = 'ca81f62362d56b74fb7f4b9ab5768f44913498da3a4dc861fbad0d8824d6833d'
        'v11_windows_readonly_capture.ps1' = '99d71cfbf7432817d320395e162d2793b2aa9c97863bf0701530704d5f89ee2c'
        'v11_windows_readonly_host.py' = '5062645291bd2768d133c9b37fa2a469c3fdacbc30ae38987ebe30e148d55e7a'
    }

    Write-Output ('V11_OS_UTC_NOW=' + ([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')))
    $Terminal = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    Write-Output ('V11_TERMINAL_PROCESS_COUNT=' + $Terminal.Count)
    if ($Terminal.Count -ne 1) {
        throw 'V11_TERMINAL_SINGLETON_NOT_ESTABLISHED'
    }
    $P = $Terminal[0]
    Write-Output ('V11_TERMINAL_PID=' + $P.Id)
    Write-Output ('V11_TERMINAL_EXE=' + $P.Path)
    Write-Output ('V11_TERMINAL_START_UTC=' + $P.StartTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))
    if (-not [string]::Equals($P.Path,'C:\Program Files\MetaTrader 5\terminal64.exe',
                              [StringComparison]::OrdinalIgnoreCase)) {
        throw 'V11_TERMINAL_PATH_NOT_MATCHING_FROZEN_RUNNER'
    }

    $Marker = Join-Path $Stage 'EXECUTION_OFF__NO_CAPTURE_AUTHORIZED'
    $Manifest = Join-Path $Stage 'source-manifest.json'
    if (-not [IO.File]::Exists($Marker) -or -not [IO.File]::Exists($Manifest)) {
        throw 'V11_EXECUTION_OFF_STAGE_MARKER_OR_MANIFEST_MISSING'
    }
    if ([IO.File]::ReadAllText($Marker).Trim() -cne 'NO_CAPTURE_NO_BROKER_ACTIONS_NO_REAL_MONEY') {
        throw 'V11_EXECUTION_OFF_MARKER_CHANGED'
    }
    $ManifestSHA = (Get-FileHash -LiteralPath $Manifest -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Output ('V11_STAGE_MANIFEST_SHA256=' + $ManifestSHA)
    if ($ManifestSHA -cne $ExpectedManifest) {
        throw 'V11_STAGE_MANIFEST_HASH_CHANGED'
    }
    foreach ($Name in ($Expected.Keys | Sort-Object)) {
        $Path = Join-Path (Join-Path $Stage 'scripts') $Name
        if (-not [IO.File]::Exists($Path)) {
            throw ('V11_STAGE_COMPONENT_MISSING=' + $Name)
        }
        $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($Actual -cne $Expected[$Name]) {
            throw ('V11_STAGE_COMPONENT_HASH_CHANGED=' + $Name)
        }
    }
    Write-Output 'V11_FIVE_COMPONENTS_AND_STAGE_MARKER_VERIFIED'
    $Python = 'C:\Program Files\Python312\python.exe'
    Write-Output ('V11_PINNED_PYTHON_FILE_EXISTS=' + [IO.File]::Exists($Python))
    Write-Output 'V11_MT5_NOT_IMPORTED_NO_INITIALIZE_NO_ACCOUNT_OR_TICK_READ'
    Write-Output 'V11_NO_VPS_MUTATION_NO_TRADING_NO_CAPTURE'
    Write-Output 'V11_OS_PREFLIGHT_COMPLETE_SOURCE_ONLY'
}
