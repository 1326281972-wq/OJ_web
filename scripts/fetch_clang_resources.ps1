# scripts/fetch_clang_resources.ps1
# 一键获取浏览器 WASM 编译资源：clang22 / lld22 / sysroot22.tar（+ 解包 sysroot）+ memfs（本地留档复制）
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts\fetch_clang_resources.ps1
# 可选：先执行 $env:GH_MIRROR="https://ghfast.top" 切换镜像（国内网络下载 GitHub 慢时用）

$ErrorActionPreference = "Stop"

$Root     = Split-Path -Parent $PSScriptRoot
$ClangDir = Join-Path $Root "frontend\public\clang"
$BuildBak = Join-Path $Root ".tmp-memfs-build\memfs"   # 自举留档，供 memfs 离线复制

if (-not (Test-Path $ClangDir)) { New-Item -ItemType Directory -Force -Path $ClangDir | Out-Null }

$Base    = if ($env:GH_MIRROR) { $env:GH_MIRROR.TrimEnd('/') } else { "https://github.com" }
$Release = "$Base/cppstudio-io/wasm-clang-runtime/releases/download/v0.1.0"

function Get-ClangFile {
    param([string]$Name)
    $target = Join-Path $ClangDir $Name
    if ((Test-Path $target) -and ((Get-Item $target).Length -gt 0)) {
        Write-Host "[skip] $Name already exists"
        return
    }
    Write-Host "[get ] $Name"
    curl.exe -L --fail --silent --show-error -o $target "$Release/$Name"
    if (-not (Test-Path $target)) {
        throw "Download failed: $Name (if network issue, retry after setting env GH_MIRROR, e.g. https://ghfast.top)"
    }
}

Push-Location $ClangDir
try {
    Get-ClangFile "clang22"
    Get-ClangFile "lld22"
    Get-ClangFile "sysroot22.tar"
    if (-not (Test-Path "sysroot")) {
        Write-Host "[ext ] sysroot22.tar"
        tar -xf sysroot22.tar
    }
}
finally { Pop-Location }

# memfs (about 95KB) has no public download source: copy from local bootstrap archive if present
$memfsTarget = Join-Path $ClangDir "memfs"
if (Test-Path $memfsTarget) {
    Write-Host "[skip] memfs already exists"
} elseif (Test-Path $BuildBak) {
    Copy-Item $BuildBak $memfsTarget
    Write-Host "[copy] memfs from .tmp-memfs-build\memfs"
} else {
    Write-Host "[WARN] memfs not found: please copy it from the author into $ClangDir (browser Run would 404 without it)"
}

Write-Host ""
Write-Host "Done. frontend\public\clang contents:"
Get-ChildItem $ClangDir | Select-Object Name, Length
