# NotebookLM Google auth on Windows (one-time setup)
# Run: powershell -ExecutionPolicy Bypass -File docker/scripts/setup-notebooklm-auth.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=== NotebookLM - Dang nhap Google (Windows) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Chrome se mo de ban dang nhap Google."
Write-Host "Sau khi xong, restart MCP container:"
Write-Host "  cd docker"
Write-Host "  docker compose --profile notebooklm restart notebooklm-mcp"
Write-Host ""
Write-Host "Data:  $env:LOCALAPPDATA\notebooklm-mcp\Data"
Write-Host "Config: $env:APPDATA\notebooklm-mcp\Config"
Write-Host ""

$dataDir = Join-Path $env:LOCALAPPDATA "notebooklm-mcp\Data"
$configDir = Join-Path $env:APPDATA "notebooklm-mcp\Config"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
New-Item -ItemType Directory -Force -Path $configDir | Out-Null

node "$ScriptDir\run-notebooklm-setup-auth.mjs"
