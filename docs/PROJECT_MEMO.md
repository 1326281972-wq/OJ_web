# 项目备忘（PROJECT MEMO）v0.1

> **为什么写这份备忘**：对话越长，助手（项目助手）越容易丢掉早先约定，或混入已经作废的结论；一次能阅读的对话与文件有限，装不下全部历史。因此把**相对稳定**的约定放在仓库里，供每次新任务开始前阅读。过时条目由负责人删除或标注失效，不在此追加无价值信息。

---

## 1. 技术栈（稳定约定，改动需更新本备忘）

- 前端：Vue 3 + Vite + Pinia + Vue Router + Element Plus + CodeMirror 6
- 后端：Python FastAPI + SQLAlchemy 2.0 + Pydantic v2
- 数据库：SQLite（零配置，单文件）
- 认证：JWT（Bearer token，24h 有效期）+ bcrypt 密码哈希
- 浏览器内编译：C++（clang→WASM，预编译资源 + 懒加载 + brotli 压缩；Go 已排除）。资源自托管 `frontend/public/clang/`（clang22 34.4MB + lld22 18.3MB + sysroot22.tar 38MB），运行时源码自托管 `frontend/src/wasm/vendor/`（来源 `cppstudio-io/wasm-clang-runtime` v0.1.0，Apache-2.0，零 npm 依赖；第 6 天定稿）
- 评测机：真实 Python daemon `judge/judge_daemon.py`，HTTP 轮询后端 `/api/v1/judge/*`，本机编译器 `judge/toolchain/w64devkit/bin/g++.exe`（便携 GCC 16.2，`CXX` 可覆盖）
- 字段命名：**全链路 snake_case**（库表=接口 JSON=前端 API 层），禁止前端转 camelCase
- 响应约定：`{code,message,data}`，成功 code=0；分页参数 `page`/`page_size`

## 2. 主路径接口索引（详见 docs/api.md）

主路径：登录 → 题库 → 题目详情 → WASM 运行（纯前端）→ 提交 → 轮询 → 评测机评测 → 终态。

| 顺序 | 接口 | 说明 |
|------|------|------|
| 1 | POST /api/v1/auth/login | 登录拿 token（选手） |
| 2 | GET /api/v1/problems?page=&page_size= | 题库列表（分页） |
| 3 | GET /api/v1/problems/{id} | 题目详情（样例供 WASM 自测） |
| 4 | POST /api/v1/submissions | 创建提交 → id + status=pending |
| 5 | GET /api/v1/submissions/status?ids= | 批量状态轮询（指数退避 2s/4s/8s） |
| 6 | POST /api/v1/judge/tasks + checkout + source/problem/testdata | 评测机取任务与数据 |
| 7 | POST /api/v1/judge/results (+compile-info/run-info) | 回传终态 |

## 3. 临时假实现边界（替换日期固定）

| 假实现 | 开关 | 替换日期（状态） |
|--------|------|------------------|
| 假评测器（服务端自动判 AC/WA） | 后端 `FAKE_JUDGE=true` | **第 6 天已替换**：真实 `judge/judge_daemon.py` 落地，`FAKE_JUDGE` 默认 false；`FAKE_JUDGE=true` 保留为回退（冒烟依赖，见 REVIEW_NOTES A-4） |
| 假 WASM 运行（固定输出/固定编译错误） | 前端 `VITE_FAKE_WASM=1` | **第 6 天已替换**：真实 clang.wasm 链路落地（Node 自测 6/6 PASS），`VITE_FAKE_WASM` 默认 0；浏览器端实测待第 7 天联调 |

规则：假实现仅用于演示与联调，不改变接口契约；到点后开关默认关闭。

## 4. 待解决问题列表

- [x] **WASM 资源来源**：第 6 天已定稿——自托管 `cppstudio-io/wasm-clang-runtime` v0.1.0（clang22/lld22/sysroot22.tar，浏览器运行时代码见 `frontend/src/wasm/vendor/README.md`），不引入 npm 依赖；
- [ ] **浏览器端真实运行实测**（第 7 天联调）：Vite dev + 题目页点运行 A+B→3；exnref 不支持时需补 clang22-noeh/lld22-noeh 自托管；brotli 压缩资源（B-7）；
- [ ] **交互器双实现一致性**：前端 JS 交互器 vs 正式 C++ 交互器，逻辑一致性方案——第 7 天前确认；
- [ ] **卡死回收与频率限制参数**：900s 回收已按默认落地；5s 提交间隔后端已实现（42901），前端节流提示待补（G6）；
- [x] 提交状态枚举完整清单与前端徽章配色映射——第 4 天已定稿（全称枚举 + statusMeta 映射）。

## 5. 失效/过时记录（负责人填写）

- 2026-08-24：`FAKE_JUDGE`/`VITE_FAKE_WASM` 默认值由开（true/1）改为关（false/0），对应假实现条目见 §3 已替换状态。

## 6. 常用命令（第 6 天起）

| 用途 | 命令 |
|------|------|
| 后端启动 | `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000`（FAKE_JUDGE 默认 false） |
| 评测机启动 | `cd judge && python judge_daemon.py`（venv 下：`../backend/.venv/Scripts/python judge_daemon.py`） |
| 块 A 自测（约 40s） | `cd judge && python scripts/test_judge_daemon.py` |
| 块 B 自测（Node，~10s） | `cd frontend && node scripts/verify_clang_wasm.mjs` |
| 后端冒烟 | `cd backend && python -m scripts.smoke`（内部强制 FAKE_JUDGE=true） |
| 前端启动 | `cd frontend && npm run dev`（VITE_FAKE_WASM=0） |
