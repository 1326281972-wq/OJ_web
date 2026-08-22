# 一键启动后端+前端（Windows PowerShell，从仓库根目录运行）
# 后端新开窗口运行并保留日志；前端在当前窗口运行。
$ErrorActionPreference = "Stop"
Start-Process powershell -ArgumentList "-ExecutionPolicy","Bypass","-File","$PSScriptRoot\start_backend.ps1"
Start-Sleep -Seconds 2
Set-Location (Join-Path $PSScriptRoot "..\frontend")

if (-not (Test-Path "node_modules")) {
    npm install
}
npm run dev
