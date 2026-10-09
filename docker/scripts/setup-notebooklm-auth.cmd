@echo off
echo.
echo === NotebookLM - Dang nhap Google ===
echo Chrome se mo trong vai giay. Hay dang nhap tai khoan Google cua ban.
echo.
cd /d "%~dp0"
node setup-auth-sdk.mjs
echo.
if errorlevel 1 (
  echo That bai. Thu lai hoac lien he support.
) else (
  echo.
  echo Buoc tiep theo:
  echo   cd c:\chatbot\dify\docker
  echo   docker compose --profile notebooklm restart notebooklm-mcp
)
echo.
pause
