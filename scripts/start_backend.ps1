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
# .env 处理：不存在时复制模板；若残留第 4 天旧假评测配置 FAKE_JUDGE=true，
# 删除后由模板重建（模板 FAKE_JUDGE=false）——否则提交一律判 accepted 且不报原因。
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
} elseif (Select-String -Path ".env" -SimpleMatch 'FAKE_JUDGE=true' -Quiet) {
    Remove-Item ".env" -Force
    Copy-Item ".env.example" ".env"
    Write-Host "[warn] backend/.env 含旧 FAKE_JUDGE=true，已删除并由 .env.example 重建（FAKE_JUDGE=false）。如需自定义 SECRET_KEY 请重新编辑 .env。"
}
& $py -m uvicorn app.main:app --reload --port 8000
