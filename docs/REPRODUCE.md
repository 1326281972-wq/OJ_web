# 第二人复现指南（极简版）

> 面向没接触过命令行的同学：全程只需要**复制粘贴命令**。首次准备约 15 分钟，以后每次启动约 1 分钟。

## 第 0 步：打开"项目命令行"（以后所有命令都贴在这里）

在文件资源管理器打开 `OJ_web` 文件夹 → 点顶部**地址栏**，输入 `powershell` 回车 → 出现黑色窗口，已自动定位到项目，直接复制下面命令即可。

## 第 1 步：一次性准备

**1) 安装两个软件**（都去官网下载安装包，一路"下一步"；Python 安装时务必勾选 `Add python.exe to PATH`）：

- Python 3.11+ → https://www.python.org/downloads/
- Node.js 18+ → https://nodejs.org/

**2) 下载浏览器编译资源**（约 90MB，在项目命令行里粘贴后回车；国内网络下载 GitHub 慢，可先执行 `$env:GH_MIRROR="https://ghfast.top"`）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\fetch_clang_resources.ps1
```

> 一键脚本会自动下载 clang22 / lld22 / sysroot22.tar 并解包，再把 `memfs` 从项目自举留档复制到位；仅当提示"未找到 memfs"时才需向作者索取拷贝。

## 第 2 步：启动（以后每次只做这一步）

再开一个项目命令行窗口，然后两个窗口各贴一条命令：

- **窗口 1**：`powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1`
- **窗口 2**：`backend\.venv\Scripts\python.exe judge\judge_daemon.py`

第一次启动会自动安装依赖、创建数据库，等待 1–3 分钟。**看到窗口 1 出现 `Uvicorn running on 8000` 和 `VITE local: http://localhost:5173`，窗口 2 出现心跳日志，就成功了**。

## 第 3 步：演示主路径

浏览器打开 `http://localhost:5173` → 登录 `demo_user` / `demo123` → 题库 → 打开 1001 → 写代码 → 点"运行"看输出 → 点"提交"看判题结果（绿色 AC=通过，红色 WA=错误并显示差异）。更细的 8 步流程见 `docs\DEMO_GUIDE.md`。

## 第 4 步：停止

两个窗口分别按 `Ctrl+C`。数据库不会丢；实在关不掉就重启电脑。

## 出问题怎么办

| 现象 | 处理 |
|---|---|
| 提示"端口被占用" | 窗口 1 粘贴：`Get-NetTCPConnection -LocalPort 8000,5173 -State Listen | % { Stop-Process -Id $_.OwningProcess -Force }`，再重新启动 |
| 浏览器点"运行"报 404 | 缺 `memfs`，从作者处拷贝到 `frontend\public\clang\` |
| 提交后一直"排队中" | 窗口 2 的评测机没启动 |
| 提交什么都显示"通过" | 检查 `backend\.env` 中 `FAKE_JUDGE` 是否为 `false`（启动脚本已自动处理，正常应为 false） |
| 弹窗提示缺 g++ | 安装 MinGW 或配置 `CXX` 环境变量指向可用 g++（无 g++ 时代码会判"系统错误"，属降级路径） |
