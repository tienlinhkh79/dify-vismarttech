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

set "SCRIPT_PATH=%~dp0run-cloudflare-and-sync.ps1"
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] Missing script: "%SCRIPT_PATH%"
    echo Please ensure file "run-cloudflare-and-sync.ps1" exists in this folder.
    echo(
    pause
    exit /b 1
)

echo [INFO] Starting one-click mode...
echo [INFO] Auto-detect tunnel URL, update docker/.env (API prefix, 9Pay return, billing URLs — no example.com), restart web + nginx + billing_saas.
echo(
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_PATH%" -OriginUrl "http://127.0.0.1:80"

echo(
echo Tunnel stopped or failed. Press any key to close...
pause >nul
