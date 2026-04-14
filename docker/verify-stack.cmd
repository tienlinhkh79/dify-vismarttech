@echo off
REM In docker/: show compose services and which image web uses.
cd /d "%~dp0"
echo === docker compose ps ===
docker compose ps
echo.
echo === docker compose images web (if supported) ===
docker compose images web 2>nul
if errorlevel 1 echo (compose images skipped - older Docker CLI)
echo.
echo === local image dify-web:local ===
docker images dify-web:local
exit /b 0
