# Build image `web` từ source (Windows). Tránh lỗi BuildKit + symlink trong docker/volumes.
# Nếu Execution Policy chặn .ps1: dùng `build-web.cmd` trong cùng thư mục, hoặc
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\build-web.ps1
# Sau build thành công mặc định chạy lại container `web` (--force-recreate) vì chỉ `up -d web`
# đôi khi không thay image đang chạy nếu Compose không thấy đổi cấu hình.
param(
    [switch]$SkipUp
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:DOCKER_BUILDKIT = '0'
docker compose build web @args
if (-not $SkipUp) {
    docker compose up -d --force-recreate --no-deps web
}

Write-Host ""
Write-Host "If UI still looks unchanged: run .\verify-stack.cmd and read section 5 in docker\RUN.md" -ForegroundColor DarkYellow
