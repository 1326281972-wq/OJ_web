# 项目备忘（PROJECT MEMO）v0.1

> **为什么写这份备忘**：对话越长，助手（项目助手）越容易丢掉早先约定，或混入已经作废的结论；一次能阅读的对话与文件有限，装不下全部历史。因此把**相对稳定**的约定放在仓库里，供每次新任务开始前阅读。过时条目由负责人删除或标注失效，不在此追加无价值信息。

---

## 1. 技术栈（稳定约定，改动需更新本备忘）

- 前端：Vue 3 + Vite + Pinia + Vue Router + Element Plus + CodeMirror 6
- 后端：Python FastAPI + SQLAlchemy 2.0 + Pydantic v2
- 数据库：SQLite（零配置，单文件）
- 认证：JWT（Bearer token，24h 有效期）+ bcrypt 密码哈希
- 浏览器内编译：C++（clang→WASM，预编译资源 + 懒加载 + brotli 压缩；Go 已排除）
- 评测机：Python 演示 daemon，HTTP 轮询后端 `/api/v1/judge/*`
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

| 假实现 | 开关 | 替换日期 |
|--------|------|----------|
| 假评测器（服务端自动判 AC/WA） | 后端 `FAKE_JUDGE=true` | **第 4 天** → 真实 judge_daemon.py |
| 假 WASM 运行（固定输出/固定编译错误） | 前端 `VITE_FAKE_WASM=1` | **第 5 天** → 真实 clang.wasm |

规则：假实现仅用于演示与联调，不改变接口契约；到点后开关默认关闭。

## 4. 待解决问题列表

- [ ] **WASM 资源来源**：采用预编译 clang.wasm（优先），是否自建交叉编译工具链——第 4 天前定稿；
- [ ] **交互器双实现一致性**：前端 JS 交互器 vs 正式 C++ 交互器，逻辑一致性方案——第 7 天前确认；
- [ ] **卡死回收与频率限制参数**：900s 回收、5s 提交间隔是否按默认值落地——第 6 天前确认；
- [ ] 提交状态枚举完整清单与前端徽章配色映射——第 4 天前定稿。

## 5. 失效/过时记录（负责人填写）

- （暂无）
