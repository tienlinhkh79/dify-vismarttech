param(
    [string]$TunnelUrl,
    [switch]$SkipRestart
)

$ErrorActionPreference = 'Stop'

function Get-TryCloudflareUrlFromText {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    $pattern = 'https://[a-z0-9-]+\.trycloudflare\.com'
    $match = [regex]::Match($Text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($match.Success) {
        return $match.Value.TrimEnd('/')
    }

    return $null
}

function Set-OrAppendEnvVar {
    param(
        [string]$Content,
        [string]$Key,
        [string]$Value
    )

    $escapedKey = [regex]::Escape($Key)
    $line = "$Key=$Value"

    if ($Content -match "(?m)^$escapedKey=.*$") {
        return [regex]::Replace($Content, "(?m)^$escapedKey=.*$", $line)
    }

    if ($Content -notmatch "(\r?\n)$") {
        $Content += [Environment]::NewLine
    }
    return $Content + $line + [Environment]::NewLine
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$dockerDir = Join-Path $repoRoot 'docker'
$envFile = Join-Path $dockerDir '.env'

if (-not (Test-Path $envFile)) {
    throw "Cannot find docker env file: $envFile"
}

$resolvedUrl = $TunnelUrl
if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
    try {
        $clipboardText = Get-Clipboard -Raw
        $resolvedUrl = Get-TryCloudflareUrlFromText -Text $clipboardText
    }
    catch {
        $resolvedUrl = $null
    }
}

if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
    throw "No tunnel URL found. Pass -TunnelUrl `"https://xxxx.trycloudflare.com`" or copy URL to clipboard first."
}

$uri = [Uri]$resolvedUrl
$baseUrl = "$($uri.Scheme)://$($uri.Host)"

Write-Host "Using tunnel URL: $baseUrl" -ForegroundColor Cyan
Write-Host "Updating docker/.env: console URLs, NEXT_PUBLIC_API_PREFIX, 9Pay return, billing stubs..." -ForegroundColor Cyan

$apiPrefix = "$baseUrl/console/api"
$ninepayReturn = "$baseUrl/billing/9pay-return"
$checkoutStub = "$baseUrl/billing/checkout"
$invoicesStub = "$baseUrl/account"

$envContent = Get-Content -Raw -Path $envFile
$envContent = Set-OrAppendEnvVar -Content $envContent -Key 'CONSOLE_API_URL' -Value $baseUrl
$envContent = Set-OrAppendEnvVar -Content $envContent -Key 'CONSOLE_WEB_URL' -Value $baseUrl
$envContent = Set-OrAppendEnvVar -Content $envContent -Key 'APP_API_URL' -Value $baseUrl
$envContent = Set-OrAppendEnvVar -Content $envContent -Key 'NEXT_PUBLIC_API_PREFIX' -Value $apiPrefix
$envContent = Set-OrAppendEnvVar -Content $envContent -Key 'NINEPAY_RETURN_URL_BASE' -Value $ninepayReturn
$envContent = Set-OrAppendEnvVar -Content $envContent -Key 'BILLING_CHECKOUT_BASE_URL' -Value $checkoutStub
$envContent = Set-OrAppendEnvVar -Content $envContent -Key 'BILLING_INVOICES_URL' -Value $invoicesStub
Set-Content -Path $envFile -Value $envContent -Encoding UTF8

Write-Host "Updated $envFile (no example.com for billing stubs)." -ForegroundColor Green

if (-not $SkipRestart) {
    Write-Host "Restarting web, nginx, billing_saas..." -ForegroundColor Cyan
    Push-Location $dockerDir
    try {
        docker compose up -d --force-recreate --no-deps web nginx billing_saas
    }
    finally {
        Pop-Location
    }
    Write-Host "Done. Reload browser to apply new API prefix." -ForegroundColor Green
}
else {
    Write-Host "SkipRestart enabled. Run restart manually when ready." -ForegroundColor Yellow
}
