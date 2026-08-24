# OJ Web 在线测评系统

XCPC/ACM 场景的在线测评系统 Web 端。选手在浏览器中做题、编写并提交 C++ 代码、查看评测状态；管理员发布题目与评测数据；评测机（程序）自动拉取任务并回传结果。

> 配套文档见 `docs/`：建设方案、模块图与选型比对、数据模型（data-model.md）、接口约定（api.md）、项目备忘（PROJECT_MEMO.md）。
>
> **仓库约束（Harness，第 6 天起）**：改动前先读 [`AGENTS.md`](AGENTS.md)（能改/禁改/密钥与依赖禁令/完成标准）；提交前跑 `powershell -File scripts/check_harness.ps1` 确认 `HARNESS OK`。

## 目录结构（代码 / 文档 / 脚本 / 数据分区）

```
OJ_web/
├─ README.md                 # 本文件：启动说明
├─ .gitignore                # 忽略规则（含原因注释）
├─ docs/                     # 文档分区：方案/接口/数据模型/备忘/实验报告
│  ├─ api.md  data-model.md  PROJECT_MEMO.md
│  └─ plans/                 # 当日计划
├─ backend/                  # 代码分区：FastAPI 后端
│  ├─ app/                   #   应用（main/core/models/schemas/api/services）
│  ├─ scripts/               #   建库 seed、冒烟测试
│  ├─ data/                  #   数据分区：SQLite 文件（git 忽略，seed 重建）
│  ├─ requirements.txt       # 依赖清单（勿提交依赖树本身）
│  └─ .env.example           # 环境变量示例（复制为 .env）
├─ frontend/                 # 代码分区：Vue3 前端
│  ├─ src/                   #   源码
│  ├─ index.html  vite.config.ts  package.json
│  └─ .env.example           # VITE_API_BASE 示例
├─ judge/                    # 代码分区：评测机（第 4 天实现，见 judge/README.md）
└─ scripts/                  # 脚本分区：启动脚本
   ├─ start_backend.ps1 / start_backend.sh
   └─ start_all.ps1 / start_all.sh
```

## 环境要求

- Python 3.11+（后端）
- Node.js 18+（前端）
- g++（真实评测机编译选手代码必需；默认工具链在 `judge/toolchain/w64devkit/bin/g++.exe`，可用 `CXX` 覆盖）

## 安装（新机器首次，一次性）

1. **后端依赖**：`cd backend && python -m venv .venv` → 激活虚拟环境（Windows: `.\.venv\Scripts\Activate.ps1`；Linux/macOS: `source .venv/bin/activate`）→ `pip install -r requirements.txt`。
2. **前端依赖**：`cd frontend && npm install`。
3. **评测机工具链**：确认 g++ 可用（`judge/toolchain/w64devkit/bin/g++.exe` 存在，或 `CXX` 指向任意可用 g++）。

## 配置

1. **后端环境变量**：`cd backend && copy .env.example .env`（Windows）/ `cp .env.example .env`（Linux/macOS）；不配置也可直接运行（用默认值）。生产环境务必修改 `SECRET_KEY`。
2. **前端环境变量**：`cd frontend && copy .env.example .env`，默认 `VITE_API_BASE=/api`（vite proxy 转发到 8000），一般无需改。
3. **建库与题库**：`cd backend && python -m scripts.seed`，生成 `backend/data/app.db`，内置账号 `admin/admin123`、`demo_user/demo123`、`judger1/judger123`，题目 **1001~1021 共 21 道**（1001 演示题 + 1002~1021 简单/中等题，每题 2 组测试点）。如需重置：删除 `backend/data/app.db` 后重跑 seed。

## 启动

### 方式 A：一键启动（推荐，Windows）

```bash
cd OJ_web
powershell -ExecutionPolicy Bypass -File scripts/start_all.ps1
```

该脚本新开窗口启动后端（保留日志）、当前窗口启动前端。**评测机需单独启动**：另开终端按 `judge/README.md` 运行 `judge/judge_daemon.py`（或临时设 `FAKE_JUDGE=true` 用假评测器）。Linux/macOS 对应 `scripts/start_all.sh`。

### 方式 B：分步启动

**1. 后端（端口 8000）**：`cd backend && python -m uvicorn app.main:app --reload --port 8000`
- 验证：`curl http://127.0.0.1:8000/api/v1/health` 返回 `{"code":0,...}`，或浏览器打开 `http://127.0.0.1:8000/docs`。

**2. 前端（端口 5173）**：`cd frontend && npm run dev`
- 验证：浏览器打开 `http://127.0.0.1:5173`，页面显示 OJ Web 基线页并显示后端健康状态。

**3. 评测机（真实评测必需）**：默认 `FAKE_JUDGE=false`，须另起 `judge_daemon.py`（见 `judge/README.md`）；纯后端演示可临时设 `FAKE_JUDGE=true` 用假评测器（此时无需 daemon）。
- 联调时若提交一直 `pending`：评测机没起或 `OJ_BASE_URL` 指向别的实例——按排错 `docs/TROUBLESHOOTING.md` §3。

## 停止

- 后端/前端/评测机：各自在对应终端按 `Ctrl+C`；
- 端口被占用：`netstat -ano | findstr :8000`（或 `:5173`）找到 PID → `taskkill /PID <pid> /F`；
- 一键脚本方式：关闭启动窗口即全部停止（或按脚本输出提示逐个停止）。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | dev-only-change-me | JWT 签名密钥，**生产必须改为随机值** |
| `DATABASE_URL` | sqlite:///backend/data/app.db | 数据库地址 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 | token 有效期（分钟） |
| `FAKE_JUDGE` | false | 第 6 天起默认 false：开启则后端内置假评测器自动判，关闭须另起 `judge_daemon.py` 真实评测 |
| `VITE_API_BASE` | /api | 前端接口基址（vite proxy 转发到 8000） |

**敏感信息**：`.env` 含本地密钥，不入库（见 .gitignore）；仓库只保留不含秘密的 `.env.example`。新机器：复制 `.env.example` 为 `.env` 并按需修改 `SECRET_KEY` 即可。

## 假实现边界（勿误当成已完成）

> 第 6 天起，所有"假实现"已被真实实现替换，**默认状态即真**：后端 `FAKE_JUDGE=false` 走 `judge_daemon.py` 真实评测；前端 `VITE_FAKE_WASM=0` 走自托管 `clang.wasm` 真实编译。下方表格保留为历史参考。

| 假实现 | 开关 | 现状 |
|--------|------|------|
| 后端假评测器 | `FAKE_JUDGE=true` | **第 6 天**已被 `judge_daemon.py` 替换；默认 `false` |
| 前端假 WASM 编译 | `VITE_FAKE_WASM=1` | **第 6 天**已被自托管 `clang22/lld22/sysroot22.tar` 替换；默认 `0` |

## 快速通检与回归（第 7/8 天起）

- **快速通检（一条命令，三段 31 项）**：`cd OJ_web && backend\.venv\Scripts\python scripts\smoke_e2e.py`
  - Phase 1 契约 17 项（`backend/scripts/smoke.py`）→ Phase 2 真实评测端到端 8 项（`judge/scripts/test_judge_daemon.py`）→ Phase 3 异常路径 6 项（`backend/scripts/test_anomaly_paths.py`）。
- **回归（全库标准解真评测）**：`cd backend && .venv\Scripts\python -m scripts.verify_problems` —— 对 1001~1021 全库 21 道题提交标准解并真实编译运行，断言全部 `accepted`（题目数据 + 评测链路双重回归，第 8 天起）。
- 提交前跑 `powershell -File scripts/check_harness.ps1` 确认 `HARNESS OK`。
