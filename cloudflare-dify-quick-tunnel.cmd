@echo off
setlocal
title Cloudflare quick tunnel - Dify (127.0.0.1:80)

echo(
echo ============================================================
echo Cloudflare quick tunnel - Dify
echo Origin: http://127.0.0.1:80
echo Uses --config NUL to ignore local .cloudflared config.
echo Keep this window open while tunnel is running.
echo ============================================================
echo(

where cloudflared >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Command "cloudflared" not found.
    echo Install Cloudflare Tunnel CLI and add it to PATH:
    echo https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
    echo(
    pause
    exit /b 1
)

where docker >nul 2>&1
if not errorlevel 1 (
    echo [Docker] Restarting docker-nginx-1...
    docker restart docker-nginx-1 >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Could not restart docker-nginx-1. If tunnel errors, restart it manually.
    )
    timeout /t 3 /nobreak >nul
) else (
    echo [WARN] Docker command not found in PATH. Skipping nginx container restart.
)

cloudflared tunnel --config NUL --url http://127.0.0.1:80 --protocol http2

echo(
echo Tunnel stopped or failed. Press any key to close...
pause >nul
