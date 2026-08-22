# 后端一键启动（Windows PowerShell，从仓库根目录运行）
# 用法: powershell -ExecutionPolicy Bypass -File scripts/start_backend.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\backend")

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
$py = ".venv\Scripts\python.exe"

& $py -m pip install --disable-pip-version-check -r requirements.txt
if (-not (Test-Path "data\app.db")) {
    & $py -m scripts.seed
}
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}
& $py -m uvicorn app.main:app --reload --port 8000
