@echo off
set HEADLESS=true
set NOTEBOOKLM_HEADLESS=true
echo Starting NotebookLM MCP on http://0.0.0.0:8012 (Docker proxy uses host.docker.internal:8012)
npx notebooklm-mcp@latest --transport http --port 8012 --host 0.0.0.0
