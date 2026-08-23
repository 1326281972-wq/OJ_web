# 主路径演示说明（DEMO GUIDE）

> 用途：让第二人按本说明独立复现主路径：**注册/登录 → 题库 → 题目详情 → WASM 运行 → 提交 → 轮询 → 终态**。
> 依据：接口约定见 `docs/api.md`；临时假实现边界见 `docs/PROJECT_MEMO.md` 第 3 节。
> 更新记录：v1（2026-08-23，第 5 天）按实机走通路径撰写；任何"步骤不生效"请先核对本节末尾的失败检查。

---

## 0. 环境前提

| 项 | 要求 | 说明 |
|----|------|------|
| 操作系统 | Windows / Linux 均可 | 以下命令以 Windows PowerShell 为例，Linux 等价命令见括号 |
| Node.js | ≥ 18 | 前端 Vite 要求 |
| Python | ≥ 3.10 | 后端 FastAPI 要求 |
| 依赖 | `frontend/node_modules`、`backend/.venv` 已装 | 未装则先执行下方"首次安装" |
| 端口 | 8000（后端）、5173（前端）空闲 | 冲突时先停旧进程（见失败检查 F1） |
| 演示账号 | `admin / admin123`（管理员）、`demo_user / demo123`（选手）、`judger1 / judger123`（评测机） | 由 `python -m scripts.seed` 创建 |
| 数据 | `backend/data/app.db` | 不存在或想重置时执行 seed（见首次安装 0.2） |

### 0.1 首次安装依赖

```powershell
# 后端（Windows）
cd backend
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 前端
cd ..\frontend
npm install
```

### 0.2 建库（仅首次或重置时）

```powershell
cd backend
Remove-Item data\app.db -ErrorAction SilentlyContinue   # 可选：删库重置
.\.venv\Scripts\python -m scripts.seed
# 预期输出：seed 完成：admin/admin123、demo_user/demo123、judger1/judger123、题目 1001、示例提交 x2
```

---

## 1. 启动（两条进程）

### 步骤 1.1 启动后端

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- **预期现象**：日志出现 `Uvicorn running on http://127.0.0.1:8000`。
- **验证**：浏览器开 `http://127.0.0.1:8000/docs` 出现 Swagger 文档；或执行
  `curl http://127.0.0.1:8000/api/v1/health`，返回 `{"code":0,...}`。

### 步骤 1.2 启动前端

```powershell
cd frontend
npm run dev
```

- **预期现象**：日志出现 `Local: http://localhost:5173/`。
- **验证**：`curl http://localhost:5173/api/v1/health` 经 vite 代理返回 `{"code":0,...}`。

> 也可用一键脚本 `scripts\start_all.ps1`（Windows）或 `bash scripts/start_all.sh`（Linux）同时拉起两者（自动建库并装依赖）。

---

## 2. 主路径演示步骤

> 浏览器统一使用 http://localhost:5173。以下步骤均为实测走通路径。

### 步骤 2.1 打开首页，未登录被重定向

1. 浏览器访问 `http://localhost:5173/`。
2. **预期现象**：自动跳转到 `http://localhost:5173/login?redirect=/problems`，显示"登录 / 注册"卡片与演示账号提示。
3. **失败检查**：停在空白页或报错 → 见 F2（前端没起）、F3（代理不通）。

### 步骤 2.2 登录（或注册）

- 方式 A（推荐，演示账号）：输入 `demo_user` / `demo123`，点"登 录"。
- 方式 B（新账号）：切"注册"页签，填用户名/昵称/密码/邮箱，点"注册并登录"（注册成功即自动登录）。
- **预期现象**：跳转 `http://localhost:5173/problems`，右上角显示当前用户名；方式 B 额外出现绿色提示"注册成功，已自动登录"。
- **失败检查**：提示"invalid user_id or password" → 密码/账号错（F5）；提示"submit too frequent"仅对提交生效，登录无此限制。

### 步骤 2.3 浏览题库列表

1. 页面显示题库表格。
2. **预期现象**：表格出现题目 **1001 A+B Problem**，列为编号/标题/时间限制 1000 ms/内存限制 256 MB/类型"普通题"，右侧有"做题"按钮；底部"Total 1"。
3. **失败检查**：列表为空 → 数据未 seed（重新执行 0.2）。

### 步骤 2.4 查看题目详情

1. 点击 1001 行右侧"做题"按钮。
2. **预期现象**：跳转 `http://localhost:5173/problems/1001`，页面分左右两栏：左栏题目描述（描述/输入格式/输出格式/样例输入 `1 2`/样例输出 `3`），右栏语言选择" C++ (GCC17)" + 代码框 + "运行（WASM 演示）"和"提交评测"按钮。
3. **失败检查**：提示"problem not found" → 题目 ID 不存在或未 seed（F4）。

### 步骤 2.5 浏览器内运行（WASM 演示）

1. 在右栏代码框输入任意代码（如 A+B 代码），点"运行（WASM 演示）"。
2. **预期现象**：代码框下方出现"运行结果"区块，标注黄色标签"演示模式"，输出为样例输入 `1 2` 的回显。
3. **说明**：此步当前为**临时假实现**（`frontend/.env.development` 中 `VITE_FAKE_WASM=1`），仅演示交互与布局；真实 clang.wasm 替换见差距清单 G2（第 6 天）。**标注"演示模式"即表示此步不是真实编译**，不得误报为真实运行。
4. **失败检查**：无"运行结果"出现 → 前端未加载最新代码（重启 `npm run dev`）；出现报错弹窗 → 见 F3。

### 步骤 2.6 提交代码

1. 在代码框填入 A+B 正确解：

```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){ int a,b; cin>>a>>b; cout<<a+b<<endl; return 0; }
```

2. 点"提交评测"。
3. **预期现象**：出现提示"已提交 #N，等待评测"，自动跳转 `http://localhost:5173/submissions?focus=N`，"我的提交"表格高亮刚提交的行，状态列显示 **通过 AC**（假评测器同步判定）。
4. **失败检查**：提示"请先编写代码" → 代码框为空；提示"submit too frequent" → 距上次提交不足 5 秒（后端 42901 频率限制，等 5 秒再提交）；提示未认证 → 重新登录（F5）。

### 步骤 2.7 查看终态与详情

1. 在"我的提交"表格中点刚提交那行的"详情"。
2. **预期现象**：弹出"提交详情"对话框，显示编号 #N、题目 P1001、语言 C++、状态"通过 AC"，下方完整展示代码；表格轮询逻辑每 2 秒刷新进行中的提交状态（当前假评测器同步返回，故提交即终态）。
3. **失败检查**：对话框空白 → 见 F3；他人账号看不到该记录属正常（权限按本人隔离）。

---

## 3. 停止

- 两个终端分别按 `Ctrl+C`。
- 端口被占用：`netstat -ano | findstr :8000` 找到 PID 后 `taskkill /PID <pid> /F`（5173 同理）。

---

## 4. 失败检查索引（F1–F5）

| 编号 | 现象 | 原因与处理 |
|------|------|-----------|
| F1 | 端口占用，进程起不来 | 先停旧进程（见第 3 节）再启动 |
| F2 | 前端页面打不开/空白 | 确认 1.2 前端进程在跑、日志无报错；`npm install` 后再 `npm run dev` |
| F3 | 接口返回 500 / 代理不通 | 后端未启动或异常：看后端终端日志；确认 8000 端口为 uvicorn 进程 |
| F4 | 题目/数据缺失 | 重新执行 0.2 建库 seed |
| F5 | 登录失败 401 | 核对账号密码（0 环境前提）；忘记密码可重置数据库（0.2） |

---

## 5. 当前边界与差距（完整清单见实验报告 05 第 X 节 / docs/gap_list.md）

- G1 真实评测机未接入（假评测器 `FAKE_JUDGE=true` 兜底）——阻塞主路径真实性，第 6 天替换。
- G2 真实 WASM 编译未接入（`VITE_FAKE_WASM=1` 演示模式）——第 6 天替换 clang.wasm。
- 细粒度权限、管理端、前端节流提示、轮询退避等为后续天任务，见差距清单。
