# D0-R2 PREATTACH ENVIRONMENT SURVEY ONLY — ABSOLUTELY NO MT5 ATTACH.
# No imports of MetaTrader5, no Python interpreter execution, no Git/network,
# no writes, no folder creation, no process/service/task/config changes.
# Safe to review on screen and send result separately.
# Does NOT constitute a new D0 attempt or authorization.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$oldLocation = (Get-Location).Path

Write-Output 'D0_PYTHON_LOCATION_SURVEY_START'
Write-Output ('UTC=' + [DateTime]::UtcNow.ToString('o'))
Write-Output ('WINDOWS_USER=' + [Environment]::UserName)
Write-Output ('CWD=' + $oldLocation)

# Only locate Python files: do NOT launch Python, py.exe or MetaTrader5.
$folders = @(
    (Join-Path $oldLocation '.venv\Scripts'),
    (Join-Path $oldLocation 'venv\Scripts'),
    (Join-Path $oldLocation 'env\Scripts'),
    (Join-Path $env:USERPROFILE 'Desktop\xauusd-autonomous-trading-agent\.venv\Scripts'),
    (Join-Path $env:USERPROFILE 'Desktop\xauusd-autonomous-trading-agent\venv\Scripts'),
    (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python312'),
    (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python313'),
    (Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python\Python311'),
    'C:\Python312',
    'C:\Python311',
    'C:\Program Files\Python312',
    'C:\Program Files\Python311'
)
$possible = [System.Collections.Generic.HashSet[string]]::new(
    [StringComparer]::OrdinalIgnoreCase
)
foreach ($folder in $folders) {
    $file = Join-Path $folder 'python.exe'
    if ([IO.File]::Exists($file)) { $null = $possible.Add([IO.Path]::GetFullPath($file)) }
}
# Discover all executable candidates on PATH, not just the first.
$found = @(Get-Command python.exe -All -ErrorAction SilentlyContinue)
foreach ($one in $found) {
    if ($null -ne $one -and [IO.File]::Exists($one.Source) -and
        $one.Source -notlike '*\WindowsApps\*') {
        $null = $possible.Add([IO.Path]::GetFullPath($one.Source))
    }
}
# Read all available Python registry installation registrations.
foreach ($root in @('HKCU:\Software\Python\PythonCore',
                    'HKLM:\Software\Python\PythonCore',
                    'HKLM:\Software\WOW6432Node\Python\PythonCore')) {
    if (Test-Path -LiteralPath $root) {
        foreach ($version in @(Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue)) {
            $install = Join-Path $version.PSPath 'InstallPath'
            if (Test-Path -LiteralPath $install) {
                $dir = (Get-ItemProperty -LiteralPath $install -ErrorAction SilentlyContinue).'(default)'
                if (-not [string]::IsNullOrWhiteSpace($dir)) {
                    $exe = Join-Path $dir 'python.exe'
                    if ([IO.File]::Exists($exe)) {
                        $null = $possible.Add([IO.Path]::GetFullPath($exe))
                    }
                }
            }
        }
    }
}
Write-Output 'READ_ONLY_PYTHON_CANDIDATES'
foreach ($path in @($possible | Sort-Object)) {
    $base = Split-Path $path -Parent
    $maybeVenvRoot = Split-Path $base -Parent
    $isVenv = [IO.File]::Exists((Join-Path $maybeVenvRoot 'pyvenv.cfg'))
    $sitePackages = if ($isVenv) {
        Join-Path $maybeVenvRoot 'Lib\site-packages'
    } else {
        Join-Path $base 'Lib\site-packages'
    }
    $mt5OnDisk = [IO.Directory]::Exists(
        (Join-Path $sitePackages 'MetaTrader5')
    )
    $mt5Dist = @(Get-ChildItem -LiteralPath $sitePackages -Filter 'MetaTrader5*.dist-info' -Directory -ErrorAction SilentlyContinue).Count -gt 0
    Write-Output ("PYTHON_PATH={0} | VENV={1} | MT5_PACKAGE_DIR={2} | MT5_DIST_INFO={3}" -f
        $path,$isVenv,$mt5OnDisk,$mt5Dist)
}
if ($possible.Count -eq 0) { Write-Output 'NO_FILE_CANDIDATES_SEEN_IN_CHECKED_LOCATIONS' }

Write-Output 'READ_ONLY_PYTHON_PROCESSES'
foreach ($proc in @(Get-Process -Name python,pythonw -ErrorAction SilentlyContinue)) {
    try { Write-Output ("RUNNING_PYTHON_EXE={0}" -f $proc.Path) }
    catch { Write-Output 'RUNNING_PYTHON_PATH_UNAVAILABLE' }
}

Write-Output 'READ_ONLY_TERMINAL_COUNT'
$terms = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
Write-Output ("TERMINAL_COUNT={0}" -f $terms.Count)
foreach ($term in $terms) {
    try { Write-Output ("TERMINAL_PID={0} | EXE={1}" -f $term.Id,$term.Path) }
    catch { Write-Output ("TERMINAL_PID={0} | EXE=UNAVAILABLE" -f $term.Id) }
}
Write-Output 'D0_PYTHON_LOCATION_SURVEY_END__NO_PYTHON_OR_MT5_EXECUTED'
