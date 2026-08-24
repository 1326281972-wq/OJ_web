# 差距清单（GAP LIST）

> 第 5 天（2026-08-23）主路径贯通后记录：今日已走通、但**尚未真正可用**的事项。每条按四要素（约束/需求/范围/输出）写成可验收任务；阻塞主路径真实可用的事项最先做（P0）。
> 负责人均为：刘易桓（独立完成）。计划天数：D6=第 6 天（2026-08-24），以此类推。

## P0（阻塞主路径真实可用，第 6 天优先）

### G1 真实评测机未接入（假评测器兜底）

- **描述**：主路径第 6 环"评测机评测"目前由后端假评测器（`services/fake_judge.py`，`FAKE_JUDGE=true`）同步判定兜底；`judge/judge_daemon.py` 未实现，真实评测链路不存在。演示提交即得终态，但结果非真实编译运行产出。
- **约束**：不改 `api.md` §4 judge/* 接口契约；评测机以 HTTP 轮询与后端交互；沿用 5s 提交间隔、代码 ≤64KB、状态枚举；替换后 `FAKE_JUDGE` 默认关。
- **需求**：实现 `judge_daemon.py`：judger1 登录 → 轮询 `POST /judge/tasks` 拉任务 → checkout → 取 source/problem/testdata → 本地真实编译（g++）并运行全部测试数据 → `POST /judge/results` 回传终态（含真实 time_used/memory_used）、失败时回传 compile-info/run-info 与 judge_error。
- **范围**：新增 `judge/judge_daemon.py`；后端 `FAKE_JUDGE=false` 时禁用自动判定；更新 `judge/README.md` 启动方式。
- **输出**：`FAKE_JUDGE=false` 下按演示文档步骤 2.6/2.7 复跑：A+B 正确解→accepted 且耗时/内存为真实值；错误解→wrong_answer；评测机日志可见真实编译运行记录。
- **状态（第 6 天）**：🟡 **已实现，联调待确认**。`judge/judge_daemon.py` 落地（login→tasks→checkout→source/problem/testdata→g++ 编译→逐点运行→results/compile-info/run-info/heartbeat，含 judge_error 降级）；`FAKE_JUDGE` 默认改 false；自测：HTTP 全链路断言通过（T2/T4/T5）、编译运行快速核对 ALL PASS；完整复跑 `test_judge_daemon.py` 与演示文档 2.6/2.7 复跑留第 7 天联调（见 REVIEW_NOTES A-1~A-6）。

### G2 真实 WASM 编译未接入（演示模式兜底）

- **描述**：主路径第 4 环"WASM 运行"为假实现（`VITE_FAKE_WASM=1`，`wasm/runtime.ts` 固定回显样例输入并标注"演示模式"），浏览器内编译能力未落地。
- **约束**：不改 `runCode` 签名与 `RunResult` 结构；clang.wasm 预编译资源懒加载 + brotli 压缩（PROJECT_MEMO §1）；替换后 `VITE_FAKE_WASM` 默认关。
- **需求**：懒加载预编译 clang.wasm，浏览器内编译用户 C++ 源码并执行，返回真实 stdout/stderr；编译失败展示真实错误文本；资源加载有进度/失败提示。
- **范围**：`frontend/src/wasm/runtime.ts` 真实分支；clang.wasm 资源落地（docs 记录来源与构建脚本）；`.env.development` 开关置 0。
- **输出**：前端点"运行"输入 A+B 代码输出 `3`（非样例回显）且无"演示模式"标签；输入含语法错误代码时展示真实编译错误；运行失败分支有提示。
- **状态（第 6 天）**：🟡 **已实现，浏览器端待实测**。资源自托管 `frontend/public/clang/`（clang22/lld22/sysroot22.tar），运行时代码自托管 `frontend/src/wasm/vendor/`（Apache-2.0，零 npm 依赖）；`runtime.ts` 真实分支接入（懒加载 Worker + 错误翻译），`VITE_FAKE_WASM` 默认 0；Node 自测 `verify_clang_wasm.mjs` **6/6 PASS**（编译 A+B→链接→运行输出 3；语法错误诊断）。浏览器端实测（Vite dev + 题目页运行、exnref 降级、brotli）留第 7 天联调（见 REVIEW_NOTES B-1~B-7）。

## P1（第 6~7 天）

### G3 提交轮询退避未按契约

- **描述**：`api.md` §3.3 约定前端指数退避 2s/4s/8s，实现为固定 2s（`SubmissionsView.vue` poll）。
- **约束**：沿用 `getSubmissionStatus` 批量接口与轮询上限（60 次）；不改列表交互。
- **需求**：轮询间隔按 2s/4s/8s 递增循环，超上限停止。
- **范围**：`SubmissionsView.vue` 轮询定时器。
- **输出**：间隔序列符合契约（代码可读/日志可观测），提交后到终态的轮询不产生额外压力。

### G5 细粒度权限与管理端缺失

- **描述**：路由守卫仅区分登录态；admin 无管理页面；管理能力未在 web 端暴露（后端已有 role 字段与权限校验）。
- **约束**：沿用 `User.role`（admin/contestant/judger）；不改现有接口契约。
- **需求**：admin 题库管理页（新增/编辑/隐藏题目，仅 admin 可调用）；选手访问管理路由被拒。
- **范围**：新前端管理页 + 路由守卫 role 校验 + 后端管理接口（若缺则补齐）。
- **输出**：admin 登录可新增/隐藏题目；选手访问管理路由被拒；选手提交列表互不可见（实测验证）。

### G6 前端提交节流提示缺失

- **描述**：后端已有 5s 提交频率限制（42901），前端无前置节流，连续提交才看到 429 错误。
- **约束**：后端限制不变。
- **需求**：提交后 5s 内按钮禁用并显示倒计时；429 错误友好转译。
- **范围**：`ProblemDetailView.vue` 提交逻辑 + api 错误处理。
- **输出**：5s 内二次提交被阻止且按钮有倒计时提示（实测）。

## P2（第 6~8 天，可穿插）

### G4 ElDialog v-loading 警告

- **描述**：控制台 4 条 Vue warn（`Runtime directive used on component with non-element root node`），来自提交详情 ElDialog 上的 v-loading。
- **约束**：对话框行为与样式不变。
- **需求**：移除 ElDialog 上的 v-loading（loading 态改由对话框内容区承载）。
- **范围**：`SubmissionsView.vue`。
- **输出**：打开详情时控制台 0 条该警告。

### G7 前端自动化测试缺失

- **描述**：前端仅手工验证，无单测/e2e 骨架。
- **约束**：不引入重型框架，沿用 Vitest；e2e 用现有 playwright-cli 能力。
- **需求**：router/auth store/status 映射单测 + 主路径 e2e 脚本入仓。
- **范围**：`frontend` 测试目录与脚本。
- **输出**：`npm test` 通过，覆盖主路径关键断言。

### G8 favicon 404

- **描述**：控制台 favicon.ico 404。
- **约束**：无。
- **需求**：补 `public/favicon.svg` 或改 index.html 引用。
- **范围**：`frontend/public`。
- **输出**：控制台无 404。

---

## 第 6 天并行两块（按"计划—执行—核对"推进）

| 块 | 任务 | 域 | 依赖 |
|----|------|----|------|
| A | G1 真实评测机接入 | 后端 + judge | 无（接口契约已就绪） |
| B | G2 真实 WASM 编译 | 前端 + 资源 | 无（与 G1 完全独立） |

A/B 互不依赖可并行；G3/G4 为小改可穿插在等待间隙。每块按：**计划**（拆步骤+验收断言）→ **执行**（编码+实机验证）→ **核对**（对照差距清单输出项打勾）。

### 第 6 天执行结果（2026-08-24 晚回填）

- ✅ 块 A：G1 代码完成 + 工具链落地（w64devkit GCC 16.2 → judge/toolchain/）+ HTTP 链路自测通过；`FAKE_JUDGE` 默认 false。
- ✅ 块 B：G2 代码完成 + 资源/运行时落地（clang22/lld22/sysroot22 → public/clang/，vendor 自托管）+ Node 自测 6/6 PASS；`VITE_FAKE_WASM` 默认 0。
- ⏳ 待第 7 天：A/B 完整自测复跑留档、浏览器端实测（B-6）、G3/G4/G6 穿插项、brotli（B-7）。
