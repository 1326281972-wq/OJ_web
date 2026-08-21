# 接口书面约定（仓库内，前后端与评测机共同遵守）

> 本文件是接口的唯一书面约定，写入仓库供前后端共同遵守。**未写明的行为不得各自猜测**，歧义以本文件与服务端实现为准。
> 统一前缀 `/api/v1`；响应统一 `{ "code": 0, "message": "ok", "data": ... }`，成功 `code=0`；失败 `code` 非 0 并伴随 HTTP 状态码。
> 鉴权：除标注"公开"外均需请求头 `Authorization: Bearer <access_token>`。
> 分页：统一查询参数 `page`（从 1 起）、`page_size`（默认 20，最大 100）。

---

## 0. 按用户故事核对请求与响应

| 用户故事 | 所需接口 |
|----------|----------|
| 作为选手，我要注册并登录，以便提交代码 | register / login / me |
| 作为选手，我要浏览题库并查看题目详情，以便编写代码 | problems 列表 / 详情 |
| 作为选手，我要提交代码并看到最终状态（AC/WA），以便知道结果 | submissions 创建 / 状态轮询 / 详情 |
| 作为评测机，我要拉取任务、取源码与数据、回传结果，以便自动评测 | judge/login、tasks、checkout、source、problem、testdata、results、compile-info、run-info、heartbeat |

---

## 1. 认证（公开：register/login）

### 1.1 POST /api/v1/auth/register（公开）

参数（JSON body）：`user_id`(必填≤64)、`password`(必填≥6)、`nickname`(必填)、`email`(可选)。

成功例：
```
POST /api/v1/auth/register
{"user_id":"alice","password":"123456","nickname":"Alice","email":"a@x.com"}
→ 201 {"code":0,"message":"ok","data":{"id":1,"user_id":"alice","nickname":"Alice","role":"contestant"}}
```

失败例（用户名已存在）：
```
→ 400 {"code":41001,"message":"user_id already exists","data":null}
```

### 1.2 POST /api/v1/auth/login（公开）

参数（JSON body）：`user_id`、`password`。

成功例：
```
POST /api/v1/auth/login
{"user_id":"admin","password":"admin123"}
→ 200 {"code":0,"data":{"access_token":"<jwt>","token_type":"bearer","user":{"user_id":"admin","role":"admin","nickname":"Admin"}}}
```

失败例（密码错误）：
```
→ 401 {"code":40101,"message":"invalid user_id or password","data":null}
```

### 1.3 GET /api/v1/auth/me（需鉴权）

```
GET /api/v1/auth/me
Authorization: Bearer <jwt>
→ 200 {"code":0,"data":{"id":1,"user_id":"alice","role":"contestant","nickname":"Alice"}}
```

## 2. 题目

### 2.1 GET /api/v1/problems（需登录；分页）

参数（query）：`page=1`、`page_size=20`；可选 `keyword`（标题模糊）。

```
GET /api/v1/problems?page=1&page_size=20
→ 200 {"code":0,"data":{"total":2,"items":[
     {"id":1001,"title":"A+B Problem","time_limit":1000,"memory_limit":256,"spj":0},
     {"id":1002,"title":"Guess the Number","time_limit":1000,"memory_limit":256,"spj":2}]}}
```

### 2.2 GET /api/v1/problems/{id}（需登录）

```
GET /api/v1/problems/1001
→ 200 {"code":0,"data":{"id":1001,"title":"A+B Problem","description":"...","input":"...","output":"...",
    "sample_input":"1 2","sample_output":"3","time_limit":1000,"memory_limit":256,"spj":0,"defunct":false}}
```

失败例（不存在/隐藏）：
```
→ 404 {"code":40401,"message":"problem not found","data":null}
```

## 3. 提交

### 3.1 POST /api/v1/submissions（需登录）

参数（JSON body）：`problem_id`(必填)、`language`(默认 "cpp")、`code`(必填，≤64KB)。

成功例：
```
POST /api/v1/submissions
{"problem_id":1001,"language":"cpp","code":"#include <bits/stdc++.h>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b;}"}
→ 201 {"code":0,"data":{"id":52001,"status":"pending","submitted_at":"2026-08-21T10:00:00Z"}}
```

失败例（未登录 / 题目不存在 / 频率限制）：
```
→ 401 {"code":40101,"message":"not authenticated","data":null}
→ 404 {"code":40401,"message":"problem not found","data":null}
→ 429 {"code":42901,"message":"submit too frequent, retry in 5s","data":null}
```

### 3.2 GET /api/v1/submissions（需登录；分页）

参数（query）：`page`、`page_size`、可选 `problem_id`、`status`。列表**不返回 code**（code=null）。

```
GET /api/v1/submissions?page=1&page_size=20
→ 200 {"code":0,"data":{"total":3,"items":[
     {"id":52001,"problem_id":1001,"language":"cpp","status":"accepted","time_used":12,"memory_used":1024,"submitted_at":"..."}]}}
```

### 3.3 GET /api/v1/submissions/status?ids=52001,52002（批量状态，前端指数退避轮询用）

参数（query）：`ids`(逗号分隔，≤50)。

```
GET /api/v1/submissions/status?ids=52001,52002
→ 200 {"code":0,"data":[{"id":52001,"status":"running"},{"id":52002,"status":"wrong_answer"}]}
```

### 3.4 GET /api/v1/submissions/{id}（详情，需登录，本人或管理员）

返回 `code`、`compile_info`、`run_info`（无则为 null）。

```
GET /api/v1/submissions/52003
→ 200 {"code":0,"data":{"id":52003,"problem_id":1001,"language":"cpp","status":"compile_error",
    "code":"...","compile_info":"main.cpp:3:1: error: expected ';' after expression","run_info":null}}
```

## 4. 评测机接口（需 judger 角色鉴权）

### 4.1 POST /api/v1/judge/login
参数：`user_id`、`password`（judger 账号）→ 成功返回 `access_token`，同 1.2 结构。

### 4.2 POST /api/v1/judge/tasks
参数（JSON body）：`mod`(默认0)、`total`(默认1)、`max_running`(默认2)。
成功例：
```
POST /api/v1/judge/tasks {"mod":0,"total":1,"max_running":2}
→ 200 {"code":0,"data":[{"id":52001,"problem_id":1001,"language":"cpp","status":"pending"}]}
```

### 4.3 POST /api/v1/judge/tasks/{sid}/checkout
原子检出，仅 status='pending' 可检出；已被抢返回 ok=false。
```
→ 200 {"code":0,"data":{"ok":true,"judger":"judger1","judge_time":"2026-08-21T10:00:01Z"}}
```

### 4.4 GET /api/v1/judge/tasks/{sid}/source → `{"code":0,"data":{"code":"...","language":"cpp"}}`

### 4.5 GET /api/v1/judge/tasks/{sid}/problem → 题目限制与测试数据清单（含 interactor 信息，交互题时）

### 4.6 GET /api/v1/judge/testdata/{pid}/{filename} → 文件流 application/octet-stream；文件名白名单校验。

### 4.7 POST /api/v1/judge/results
参数（JSON body）：`submission_id`、`status`、`time_used`、`memory_used`、`run_info`(可选)。
```
POST /api/v1/judge/results {"submission_id":52001,"status":"accepted","time_used":12,"memory_used":1024,"run_info":null}
→ 200 {"code":0,"message":"ok"}
```

### 4.8 POST /api/v1/judge/results/{sid}/compile-info、/run-info
参数：`{"info":"<错误全文>"}` → `{"code":0,"message":"ok"}`

### 4.9 POST /api/v1/judge/heartbeat
参数：`{"name":"judge-node-1","mod":0,"total":1}` → 更新 last_heartbeat → `{"code":0,"message":"ok"}`

---

## 5. 临时假实现（第 4~5 天演示可用，须标注并按时替换）

| 假实现 | 行为（固定返回/自动判定） | 支撑谁 | 替换为真实实现 |
|--------|---------------------------|--------|----------------|
| 假评测器（后端内置，`services/fake_judge.py`） | 评测机未启动时：checkout 后服务端 sleep 2s 自动写终态（seed 标记为 AC 的提交→accepted，标记 WA→wrong_answer）；`/judge/heartbeat` 恒返回 ok | 第 3~4 天前端提交-轮询联调 | **第 4 天**：切换真实 Python 演示评测机 daemon（judge/judge_daemon.py），假评测器停用 |
| 假 WASM 运行（前端 `wasm/runtime.ts` 降级分支） | clang.wasm 未就绪时：点"运行"按题目固定返回样例输出（或固定一段编译错误文案），界面标注"演示模式" | 第 4~5 天本地演示不被资源下载卡住 | **第 5 天**：替换为真实 clang.wasm 编译运行 |
| 假登录后门（不开） | 不提供；注册/登录当天即为真实实现 | — | — |

> 边界规则：**假实现必须有开关与标注**（后端配置 `FAKE_JUDGE=true`，前端环境变量 `VITE_FAKE_WASM=1`），替换日期到点后开关默认关闭；任何假实现不得影响评测机真实接口的契约（协议不变，只是"谁在回传结果"不同）。
