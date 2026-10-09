# Register NotebookLM MCP to start at Windows logon (no terminal needed).
# Run once as admin: powershell -ExecutionPolicy Bypass -File docker/scripts/install-notebooklm-mcp-autostart.ps1

$ErrorActionPreference = "Stop"
$TaskName = "Dify-NotebookLM-MCP"
$ScriptPath = Join-Path $PSScriptRoot "start-notebooklm-mcp-host-background.cmd"

if (-not (Test-Path $ScriptPath)) {
    throw "Missing script: $ScriptPath"
}

$action = New-ScheduledTaskAction -Execute $ScriptPath -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName" -ForegroundColor Green
Write-Host "Starts MCP on http://0.0.0.0:8012 at logon."
Write-Host ""
Write-Host "Start now:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Check log:"
Write-Host "  Get-Content `"$env:LOCALAPPDATA\notebooklm-mcp\mcp-host.log`" -Tail 30"
