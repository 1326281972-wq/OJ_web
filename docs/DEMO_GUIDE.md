# 主路径演示说明（DEMO GUIDE）

> 用途：让第二人按本说明独立复现主路径：**注册/登录 → 题库 → 题目详情 → WASM 运行 → 提交 → 轮询 → 终态**。
> 依据：接口约定见 `docs/api.md`；临时假实现边界见 `docs/PROJECT_MEMO.md` 第 3 节。
> 更新记录：v1（2026-08-23，第 5 天）按实机走通路径撰写；v2（2026-08-26，第 8 天）升级为**真实评测机 + 真实 WASM 编译**，题库扩展到 21 道；任何"步骤不生效"请先核对末尾的失败检查。

---

## 0. 环境前提

| 项 | 要求 | 说明 |
|----|------|------|
| 操作系统 | Windows / Linux 均可 | 以下命令以 Windows PowerShell 为例，Linux 等价命令见括号 |
| Node.js | ≥ 18 | 前端 Vite 要求 |
| Python | ≥ 3.10 | 后端 FastAPI 要求 |
| g++ | `judge/toolchain/w64devkit/bin/g++.exe` 存在，或 `CXX` 指向可用 g++ | 真实评测机编译必需 |
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

# 评测机工具链（无系统 g++ 时）
cd ..\judge\toolchain
curl -L -o w64devkit.7z.exe "https://ghfast.top/https://github.com/skeeto/w64devkit/releases/download/v2.9.1/w64devkit-x64-2.9.1.7z.exe"
w64devkit.7z.exe -y
```

### 0.2 建库（仅首次或重置时）

```powershell
cd backend
Remove-Item data\app.db -ErrorAction SilentlyContinue   # 可选：删库重置
.\.venv\Scripts\python -m scripts.seed
# 预期输出：seed 完成：admin/admin123、demo_user/demo123、judger1/judger123、题目 1001~1021 共 21 道、示例提交 x2
```

---

## 1. 启动（三条进程）

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

### 步骤 1.3 启动真实评测机

```powershell
cd judge
python judge_daemon.py          # 默认 OJ_BASE_URL=http://localhost:8000，judger1/judger123
```

- **预期现象**：日志显示登录成功并开始轮询任务（`OJ_POLL_INTERVAL=2s`）。
- **验证**：不做此步则提交会一直 `pending`（见 F6）。

> 也可用一键脚本 `scripts\start_all.ps1`（Windows）或 `bash scripts/start_all.sh`（Linux）同时拉起前后端（自动建库并装依赖）；评测机仍需单独启动。

---

## 2. 主路径演示步骤

> 浏览器统一使用 http://localhost:5173。以下步骤均为实测走通路径（对应第 5 天工作流程 8 步）。

### 步骤 2.1 打开首页，未登录被重定向

1. 浏览器访问 `http://localhost:5173/`。
2. **预期现象**：自动跳转到 `http://localhost:5173/login?redirect=/problems`，显示"登录 / 注册"卡片与演示账号提示。
3. **失败检查**：停在空白页或报错 → 见 F2（前端没起）、F3（代理不通）。

### 步骤 2.2 登录（或注册）

- 方式 A（推荐，演示账号）：输入 `demo_user` / `demo123`，点"登 录"。
- 方式 B（新账号）：切"注册"页签，填用户名/昵称/密码/邮箱，点"注册并登录"（注册成功即自动登录）。
- **预期现象**：跳转 `http://localhost:5173/problems`，右上角显示当前用户名；方式 B 额外出现绿色提示"注册成功，已自动登录"。
- **失败检查**：提示"invalid user_id or password" → 密码/账号错（F5）。

### 步骤 2.3 浏览题库列表

1. 页面显示题库表格。
2. **预期现象**：表格出现题目 **1001 A+B Problem** 与 **1002~1021 补充题**（简单/中等题），列为编号/标题/时间限制/内存限制/类型"普通题"，右侧有"做题"按钮；底部"Total 21"。
3. **失败检查**：列表为空 → 数据未 seed（重新执行 0.2）。

### 步骤 2.4 查看题目详情

1. 点击 1001 行右侧"做题"按钮（也可选 1002~1021 任意一道新题）。
2. **预期现象**：跳转 `http://localhost:5173/problems/1001`，页面分左右两栏：左栏题目描述（描述/输入格式/输出格式/样例输入 `1 2`/样例输出 `3`），右栏语言选择" C++ (GCC17)" + 代码框 + "运行（WASM 演示）"和"提交评测"按钮。
3. **失败检查**：提示"problem not found" → 题目 ID 不存在或未 seed（F4）。

### 步骤 2.5 浏览器内运行（WASM 真实编译）

1. 在右栏代码框输入 A+B 代码，点"运行（WASM 演示）"。
2. **预期现象**：代码框下方出现"运行结果"区块，输出为样例输入 `1 2` 的真实运算结果 `3`（第 6 天起为浏览器内 clang22 真实编译，非假实现）。
3. **失败检查**：提示资源加载失败 → 检查 `frontend/public/clang/` 三件套（见 `judge/README.md` 块 B）；无输出 → 重启 `npm run dev`。

### 步骤 2.6 提交代码

1. 在代码框填入 A+B 正确解：

```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){ int a,b; cin>>a>>b; cout<<a+b<<endl; return 0; }
```

2. 点"提交评测"。
3. **预期现象**：出现提示"已提交 #N，等待评测"，自动跳转 `http://localhost:5173/submissions?focus=N`，"我的提交"表格高亮刚提交的行，状态先显示"运行中"再变为 **通过 AC**（真实评测机 2s 轮询，通常 5~10 秒内出终态）。
4. **失败检查**：提示"submit too frequent" → 距上次提交不足 5 秒（后端 42901 频率限制，等 5 秒再提交）；状态一直"运行中" → 评测机未启动（F6）。

### 步骤 2.7 查看终态与详情

1. 在"我的提交"表格中点刚提交那行的"详情"。
2. **预期现象**：弹出"提交详情"对话框，显示编号 #N、题目 P1001、语言 C++、状态"通过 AC"、耗时/内存，下方完整展示代码；表格轮询逻辑每 2 秒刷新进行中的提交状态。
3. **失败检查**：对话框空白 → 见 F3；他人账号看不到该记录属正常（权限按本人隔离）。

### 步骤 2.8 验证新题（第 8 天补充）

1. 回到题库列表，选一道新题（如 **1016 数组排序**）。
2. 输入标准解：

```cpp
#include <bits/stdc++.h>
using namespace std;
int main(){int n;cin>>n;vector<int>a(n);for(auto&x:a)cin>>x;sort(a.begin(),a.end());for(int i=0;i<n;i++)cout<<(i?" ":"")<<a[i];cout<<endl;return 0;}
```

3. 点"提交评测" → **预期现象**：终态 **通过 AC**（题目测试数据与评测链路均被第 8 天回归 `verify_problems.py` 验证过）。

---

## 3. 停止

- 三个终端分别按 `Ctrl+C`（前端、后端、评测机）。
- 端口被占用：`netstat -ano | findstr :8000` 找到 PID 后 `taskkill /PID <pid> /F`（5173 同理）。

---

## 4. 失败检查索引（F1–F6）

| 编号 | 现象 | 原因与处理 |
|------|------|-----------|
| F1 | 端口占用，进程起不来 | 先停旧进程（见第 3 节）再启动 |
| F2 | 前端页面打不开/空白 | 确认 1.2 前端进程在跑、日志无报错；`npm install` 后再 `npm run dev` |
| F3 | 接口返回 500 / 代理不通 | 后端未启动或异常：看后端终端日志；确认 8000 端口为 uvicorn 进程 |
| F4 | 题目/数据缺失 | 重新执行 0.2 建库 seed |
| F5 | 登录失败 401 | 核对账号密码（0 环境前提）；忘记密码可重置数据库（0.2） |
| F6 | 提交一直 pending | 评测机未启动或 `OJ_BASE_URL` 指向别的实例：确认 1.3 在跑；排错 `docs/TROUBLESHOOTING.md` §3 |

---

## 5. 当前边界与差距（完整清单见 docs/gap_list.md）

- G1 真实评测机：**已接入**（第 6 天），第 8 天回归全库 21 题标准解全 AC。
- G2 真实 WASM 编译：**已接入**（第 6 天，clang22/lld22/sysroot22）。
- G3 通信题（spj=2）评测机暂不支持（检出即回传 judge_error）；前端 WASM 交互演示待做。
- G4/G6 管理端交互题管理、第二人独立复现验证：待后续天完成，见 gap_list。
