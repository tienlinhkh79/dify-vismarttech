@echo off
REM Gọi build-web.ps1 với ExecutionPolicy Bypass (máy chặn .ps1 mặc định vẫn chạy được).
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-web.ps1" %*
exit /b %ERRORLEVEL%
