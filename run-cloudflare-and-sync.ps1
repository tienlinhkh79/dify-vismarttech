param(
    [string]$OriginUrl = 'http://127.0.0.1:80'
)

$ErrorActionPreference = 'Stop'
$script:RepoRoot = $PSScriptRoot

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

function Update-DockerEnvWithTunnelUrl {
    param([string]$TunnelBaseUrl)

    $dockerDir = Join-Path $script:RepoRoot 'docker'
    $envFile = Join-Path $dockerDir '.env'

    if (-not (Test-Path $envFile)) {
        throw "Cannot find docker env file: $envFile"
    }

    $apiPrefix = "$TunnelBaseUrl/console/api"
    $ninepayReturn = "$TunnelBaseUrl/billing/9pay-return"
    $checkoutStub = "$TunnelBaseUrl/billing/checkout"
    $invoicesStub = "$TunnelBaseUrl/account"

    $envContent = Get-Content -Raw -Path $envFile
    $envContent = Set-OrAppendEnvVar -Content $envContent -Key 'CONSOLE_API_URL' -Value $TunnelBaseUrl
    $envContent = Set-OrAppendEnvVar -Content $envContent -Key 'CONSOLE_WEB_URL' -Value $TunnelBaseUrl
    $envContent = Set-OrAppendEnvVar -Content $envContent -Key 'APP_API_URL' -Value $TunnelBaseUrl
    $envContent = Set-OrAppendEnvVar -Content $envContent -Key 'NEXT_PUBLIC_API_PREFIX' -Value $apiPrefix
    $envContent = Set-OrAppendEnvVar -Content $envContent -Key 'NINEPAY_RETURN_URL_BASE' -Value $ninepayReturn
    $envContent = Set-OrAppendEnvVar -Content $envContent -Key 'BILLING_CHECKOUT_BASE_URL' -Value $checkoutStub
    $envContent = Set-OrAppendEnvVar -Content $envContent -Key 'BILLING_INVOICES_URL' -Value $invoicesStub
    Set-Content -Path $envFile -Value $envContent -Encoding UTF8

    Write-Host "Updated docker/.env (tunnel + NEXT_PUBLIC_API_PREFIX + billing stubs, no example.com)." -ForegroundColor Green

    Push-Location $dockerDir
    try {
        Write-Host "Restarting web, nginx, billing_saas..." -ForegroundColor Cyan
        docker compose up -d --force-recreate --no-deps web nginx billing_saas
    }
    finally {
        Pop-Location
    }
    Write-Host "Restart completed. Browser can be reloaded." -ForegroundColor Green
}

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw 'cloudflared command not found in PATH.'
}

Write-Host "Starting Cloudflare quick tunnel for $OriginUrl" -ForegroundColor Cyan
Write-Host "Waiting for trycloudflare URL, then auto-sync docker/.env..." -ForegroundColor Cyan

$logDir = Join-Path $script:RepoRoot '.tmp'
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logFile = Join-Path $logDir "cloudflared-quick-tunnel-$timestamp.log"

$argList = @(
    'tunnel'
    '--config'
    'NUL'
    '--url'
    $OriginUrl
    '--protocol'
    'http2'
    '--loglevel'
    'info'
    '--logfile'
    $logFile
)

$process = Start-Process -FilePath 'cloudflared' -ArgumentList $argList -PassThru -WindowStyle Hidden

$synced = $false
$pattern = 'https://[a-z0-9-]+\.trycloudflare\.com'
$waitedSeconds = 0

while (-not $process.HasExited) {
    if (Test-Path $logFile) {
        $logContent = Get-Content -Raw -Path $logFile
        if (-not $synced) {
            $m = [regex]::Match($logContent, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if ($m.Success) {
                $url = $m.Value.TrimEnd('/')
                $uri = [Uri]$url
                $baseUrl = "$($uri.Scheme)://$($uri.Host)"
                Write-Host "Detected tunnel URL: $baseUrl" -ForegroundColor Green
                Update-DockerEnvWithTunnelUrl -TunnelBaseUrl $baseUrl
                $synced = $true
            }
        }
    }

    if (-not $synced) {
        if (($waitedSeconds % 5) -eq 0) {
            Write-Host "Waiting for tunnel URL... ${waitedSeconds}s" -ForegroundColor DarkYellow
        }
        if ($waitedSeconds -ge 90) {
            Write-Host "Still waiting after 90s. Please check internet/VPN/firewall, then retry." -ForegroundColor Yellow
            break
        }
    }

    Start-Sleep -Seconds 1
    $waitedSeconds++
}

Write-Host "cloudflared stopped (exit code: $($process.ExitCode))." -ForegroundColor Yellow
if (-not $synced) {
    if (Test-Path $logFile) {
        Write-Host "Tunnel URL was not detected. Check log: $logFile" -ForegroundColor Yellow
    }
    else {
        Write-Host 'Tunnel URL was not detected, and no log file was created.' -ForegroundColor Yellow
    }
}
