param([string]$PrivateDirectory = "C:\Gate0Private\AlertSender-R34")
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location -LiteralPath $repo
$privateFull = [IO.Path]::GetFullPath($PrivateDirectory)
if ($privateFull.Equals($repo.Path, [StringComparison]::OrdinalIgnoreCase) -or
    $privateFull.StartsWith($repo.Path + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Private sender directory must be outside the repository."
}
$PrivateDirectory = $privateFull

$email = Read-Host "Primary Gmail address"
$telegramUser = (Read-Host "Telegram username (without @)").TrimStart("@")
$tokenSecure = Read-Host "Dedicated Telegram bot token" -AsSecureString
$gmailSecure = Read-Host "Dedicated Gmail app password" -AsSecureString

New-Item -ItemType Directory -Path $PrivateDirectory -Force | Out-Null
$acl = New-Object System.Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true, $false)
$current = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
foreach ($identity in @($current, "NT AUTHORITY\SYSTEM")) {
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $identity, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $PrivateDirectory -AclObject $acl

$tokenCipher = ConvertFrom-SecureString $tokenSecure
$gmailCipher = ConvertFrom-SecureString $gmailSecure
[IO.File]::WriteAllText((Join-Path $PrivateDirectory "telegram_token.dpapi"), $tokenCipher)
[IO.File]::WriteAllText((Join-Path $PrivateDirectory "gmail_app_password.dpapi"), $gmailCipher)

$tokenPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($tokenSecure)
$gmailPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($gmailSecure)
try {
    $tokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPtr)
    $gmailPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($gmailPtr)
    @($email, $telegramUser, $tokenPlain, $gmailPlain) |
        & py -3.12 -m phase0.validation.alert_sender.sender_setup --output $PrivateDirectory
    if ($LASTEXITCODE -ne 0) { throw "Private sender setup failed closed." }
} finally {
    $tokenPlain = $null; $gmailPlain = $null
    if ($tokenPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPtr) }
    if ($gmailPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($gmailPtr) }
}
Write-Host "Configured and preflight-verified. No canary was sent."
