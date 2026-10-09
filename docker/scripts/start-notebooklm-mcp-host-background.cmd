@echo off
REM Run NotebookLM MCP on Windows at logon (background, no console window).
cd /d "%~dp0"
set HEADLESS=true
set NOTEBOOKLM_HEADLESS=true
start "" /B cmd /c "npx notebooklm-mcp@latest --transport http --port 8012 --host 0.0.0.0 >> "%LOCALAPPDATA%\notebooklm-mcp\mcp-host.log" 2>&1"
