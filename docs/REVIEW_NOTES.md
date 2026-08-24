# 问题单（交叉阅读记录）

> 用途：供**第二人**（第 7 天联调人）审阅并发现问题。条目由第 6 天执行者在自测/交叉阅读时留下：**位置（文件:行）、现象、建议、是否已修**。
> 阅读约定：先看"是否已修"，再核对现象与修复是否闭环；发现新问题追加在本表末尾。

## 块 A（真实评测机）问题

| # | 位置 | 现象 | 建议 | 是否已修 |
|---|------|------|------|----------|
| A-1 | `judge/judge_daemon.py` 全部 judge 路径 | 首次自测 `POST /judge/login` 404：路径写 `/{judge/login}` 而契约为 `/api/v1/judge/login`（smoke.py 可证） | 路径统一加 `/api/v1` 前缀，以 api.md §4 为准 | ✅ 已修（replace_all 补前缀） |
| A-2 | `judge/judge_daemon.py` `compile_source` | w64devkit g++ 报 `cannot execute 'as'`：MSYS2 系工具链按 PATH 找 as/ld 等子进程 | 编译子进程环境变量注入 `PATH=<toolchain bin> + 原 PATH` | ✅ 已修 |
| A-3 | `judge/judge_daemon.py` `_peak_ws_kb` | 采样线程异常（ctypes 未设 argtypes/restype，64 位下 HANDLE 被截断） | 规范化 `OpenProcess/GetProcessMemoryInfo/CloseHandle` 的 argtypes/restype；sampler 线程 try 兜底 | ✅ 已修（自测暴露） |
| A-4 | `backend/scripts/smoke.py` | `config.py` 默认 `FAKE_JUDGE` 切 false 后，冒烟脚本依赖的假评测失效 | smoke.py 顶部 `os.environ.setdefault("FAKE_JUDGE","true")` 保持冒烟契约 | ✅ 已修（适配性改动，范围外最小变更） |
| A-5 | `backend/app/api/v1/submissions.py` 5s 限频 | 自测连续提交 5 例触发 42901，全链路测试被迫拉长 | 自测脚本提交后回拨 `submitted_at` 规避（仅测试，接口契约未变） | ✅ 已修（测试侧） |
| A-6 | `judge/judge_daemon.py` 内存采样 | 快速程序（<50ms）峰值内存采样常为 0KB（进程退出早于采样） | 属已知限制：Windows `PeakWorkingSetSize` 依赖进程存活时长；长运行程序采样准确 | ⏳ 未修（记录为限制，非缺陷） |

## 块 B（真实 WASM 编译）问题

| # | 位置 | 现象 | 建议 | 是否已修 |
|---|------|------|------|----------|
| B-1 | `frontend/scripts/verify_clang_wasm.mjs` `runWasm` | Node WASI `stdin` 传 Buffer 报错（仅接受数字 fd） | stdin/stdout/stderr 用临时文件 fd 重定向 | ✅ 已修 |
| B-2 | 同脚本编译调用 | clang 报 `unknown argument '-emit-obj'`：WASI `argv[0]` 必须是程序名（`clang`），否则 driver 把 `-cc1` 当程序名、后续参数当输入 | `argv` 首位补 `'clang'`/`'wasm-ld'` | ✅ 已修 |
| B-3 | 同脚本"语法错误"断言 | clang `-cc1` 模式语法错误时**退出码为 0**，错误仅体现在 stderr | 判据改为 `stderr 含 error`（与浏览器端 CompileError 判定一致） | ✅ 已修 |
| B-4 | `frontend/src/wasm/vendor/compile-worker.js` | 上游资源路径 `../{name}` 指向站点根，与本项目 `/clang/` 自托管不符；`../shared.js` 跨目录 | 路径改为 `/clang/{name}`、`./shared.js`（注释已标注改造点） | ✅ 已修 |
| B-5 | `frontend/public/clang/sysroot/` | sysroot22.tar 内含 macOS AppleDouble 文件（`._*`） | 无害（编译器忽略）；构建期可清理减体积 | ⏳ 未修（P3，构建期优化） |
| B-6 | 浏览器端真实运行 | **未实测**：Vite dev + 题目页点"运行" A+B→3 未在浏览器验证（Node 链路已 6/6 PASS，同一套 clang22/lld22/sysroot + 同参数） | 第 7 天联调：起后端+前端，playwright 走登录→题目→运行；同时验证 exnref 支持（不支持时需自托管 clang22-noeh/lld22-noeh，**当前未提供**） | ⏳ 待联调 |
| B-7 | 资源体积 | clang22 34.4MB + lld22 18.3MB + sysroot22.tar 38MB（未压缩） | brotli 预压缩 + 服务器 `Content-Encoding: br`（PROJECT_MEMO §1 约定） | ⏳ 未修（构建期优化，第 7 天） |

## 穿插小项（G3/G4/G6，未在本日实现）

- **G3 轮询退避**：`SubmissionsView.vue` 仍固定 2s 轮询，未按 2s/4s/8s 递增。
- **G4 v-loading 警告**：提交详情 ElDialog 的 v-loading 警告未处理。
- **G6 前端节流**：提交按钮 5s 倒计时/42901 友好提示未实现。
- 以上三项按计划为"穿插小项"，今日聚焦 A/B 两块未及实施，顺延至第 7 天（联调日可一并处理）。

## 跨块观察（供联调人重点核查）

1. `judge/README.md` 与 `frontend/src/wasm/vendor/README.md` 记录了各自已知限制，建议联调日按表逐条复核。
2. 完整自测 `test_judge_daemon.py`（约 40s）——**第 7 天已通过 `scripts/smoke_e2e.py` 完整复跑并留档：8/8 PASS**（含 T1 正确解 / T2 编译错 / T3 错答 / T4 运行错 / T5 降级，见 DEV_LOG 第 7 天）。

---

## 第 7 天联调新增问题（按 README 图片"现象/期望/日志/相关文件/已尝试/仍失败/修复"模板记录，全部已修；详见 `docs/TROUBLESHOOTING.md`）

| # | 位置 | 现象 | 修复 |
|---|------|------|------|
| C-1 | `backend/scripts/seed.py` 第 53-55 行 | TestCase 只写 1.in/2.in，daemon 拉 1.out → tc=None → 404 → 5/8 FAIL（system_error） | 改为 4 行：1.in + 1.out + 2.in + 2.out（同步加注释） | ✅ |
| C-2 | `README.md` §启动 §3 / §环境变量 / §假实现边界 | 写"第 4 天起 FAKE_JUDGE=false"，但实际第 6 天已完成；新成员按 README 跑会"提交一直 pending" | 三处对齐现状：默认 false/0，假实现表加"第 6 天已替换" | ✅ |
| C-3 | `scripts/` 缺三段串联通检入口 | smoke / judge_daemon / 异常路径分散，联调日拉新人易漏跑 | 新建 `scripts/smoke_e2e.py`（Windows）+ `.sh`（Linux）整合入口 | ✅ |
| C-4 | `backend/scripts/` 缺异常路径子测 | 缺"两端字段不一致、时序、环境、脏数据"四类断点的快速断言 | 新建 `test_anomaly_paths.py` 覆盖 6 条（题目不存在 / 非法 status / 路径穿越 / 角色不匹配 / 重复 checkout / 评测机回传 system_error） | ✅ |
| C-5 | `backend/app/api/v1/judge.py` `judge_problem` | `test_cases` 未过滤，把 `.out` 文件也列为测试点 → daemon 用 `name.replace(".in",".out")` 拉期望输出时，遇 `1.out` 会把期望输出当**输入**喂给程序（静默错判，不报错） | 只返回 `.in` 结尾的 case（加注释）；当日通检 Phase 2 8/8 验证 | ✅ |
| C-6 | `backend/.env.example` | 模板仍写 `FAKE_JUDGE=true`，与 config.py 默认 `false`、README 声明矛盾——新成员复制模板后跑成假评测器模式，真评测链永不触发 | 模板改 `FAKE_JUDGE=false` + 注释"旧 .env 需删除重复制"（本机 `.env` 属本地产物未直改） | ✅ |
| C-7 | `scripts/smoke_e2e.py` Phase 3 | 用 `python scripts/test_anomaly_paths.py` 直跑 → sys.path[0] 是 scripts/，`from app.main import app` 崩 ModuleNotFoundError | 改 `python -m scripts.test_anomaly_paths`（与 smoke 一致） | ✅ |
| C-8 | `scripts/smoke_e2e.py` 顶层 | Windows GBK 控制台打印含 `\u0368` 的日志 → UnicodeEncodeError | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` | ✅ |
