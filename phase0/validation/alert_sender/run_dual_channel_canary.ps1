param(
    [string]$PrivateSenderDirectory = "C:\Gate0Private\AlertSender-R34",
    [string]$PrivateEvidenceRoot = "C:\Gate0Private"
)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location -LiteralPath $repo
py -3.12 -m unittest -v phase0.validation.alert_sender.test_alert_sender
if ($LASTEXITCODE -ne 0) { throw "Offline sender tests failed closed; nothing was sent." }

$config = Join-Path $PrivateSenderDirectory "PRIVATE_SENDER_CONFIG.json"
$tokenFile = Join-Path $PrivateSenderDirectory "telegram_token.dpapi"
$gmailFile = Join-Path $PrivateSenderDirectory "gmail_app_password.dpapi"
foreach ($path in @($config, $tokenFile, $gmailFile)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Private sender is incomplete; nothing was sent." }
}
$output = Join-Path $PrivateEvidenceRoot ("Alert-R34-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ"))
$tokenSecure = ConvertTo-SecureString ([IO.File]::ReadAllText($tokenFile))
$gmailSecure = ConvertTo-SecureString ([IO.File]::ReadAllText($gmailFile))
$tokenPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($tokenSecure)
$gmailPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($gmailSecure)
try {
    $tokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPtr)
    $gmailPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($gmailPtr)
    @($tokenPlain, $gmailPlain) |
        & py -3.12 -m phase0.validation.alert_sender.dual_channel_canary --config $config --output $output
    if ($LASTEXITCODE -ne 0) { throw "G0-09 failed closed. Preserve the private output for diagnosis." }
} finally {
    $tokenPlain = $null; $gmailPlain = $null
    if ($tokenPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPtr) }
    if ($gmailPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($gmailPtr) }
}
Write-Host "G0-09 PASS_SPEC_ONLY. No trading authority was restored."
