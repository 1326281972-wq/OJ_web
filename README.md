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
- g++（可选，仅真实评测机编译选手代码用；纯前端 WASM 演示不需要）

## 启动说明（换机器/隔段时间均可按此跑通）

### 1. 后端（端口 8000）

```bash
cd backend
python -m venv .venv                 # 创建虚拟环境
# Windows PowerShell:  .\.venv\Scripts\Activate.ps1
# Linux/macOS:         source .venv/bin/activate
pip install -r requirements.txt      # 依赖清单安装
copy .env.example .env               # Windows；Linux: cp .env.example .env（可选，默认值可直接运行）
python -m scripts.seed               # 建库 + 演示数据（admin/admin123、demo_user、1001 A+B）
uvicorn app.main:app --reload --port 8000
```

验证：浏览器打开 `http://127.0.0.1:8000/docs`（Swagger），或 `curl http://127.0.0.1:8000/api/v1/health` 返回 `{"code":0,...}`。

### 2. 前端（端口 5173）

```bash
cd frontend
npm install                          # 依赖清单安装（package.json + lock 文件）
npm run dev
```

验证：浏览器打开 `http://127.0.0.1:5173`，页面显示 OJ Web 基线页并显示后端健康状态。

### 3. 评测机

- **当前阶段（第 3~4 天）**：后端内置假评测器（`FAKE_JUDGE=true` 默认开启），无需另起进程即可看到 提交→自动评测→终态 流转；
- **第 4 天起**：按 `judge/README.md` 启动真实演示评测机，并设置环境变量 `FAKE_JUDGE=false`。

### 停止

- 后端/前端：在对应终端按 `Ctrl+C`；
- 端口被占用时先结束占用进程（`netstat -ano | findstr :8000`）。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | dev-only-change-me | JWT 签名密钥，**生产必须改为随机值** |
| `DATABASE_URL` | sqlite:///backend/data/app.db | 数据库地址 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 | token 有效期（分钟） |
| `FAKE_JUDGE` | true | 是否启用后端假评测器（第 4 天起置 false） |
| `VITE_API_BASE` | /api | 前端接口基址（vite proxy 转发到 8000） |

**敏感信息**：`.env` 含本地密钥，不入库（见 .gitignore）；仓库只保留不含秘密的 `.env.example`。新机器：复制 `.env.example` 为 `.env` 并按需修改 `SECRET_KEY` 即可。

## 假实现边界（勿误当成已完成）

| 假实现 | 开关 | 替换日期 |
|--------|------|----------|
| 后端假评测器（自动判 AC/WA） | `FAKE_JUDGE=true` | **第 4 天** → 真实 judge/judge_daemon.py |
| 前端假 WASM 运行（固定输出/固定编译错误） | `VITE_FAKE_WASM=1` | **第 5 天** → 真实 clang.wasm |
