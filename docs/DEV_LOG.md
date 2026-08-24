# 开发日志（按日记录）

> 用途：第 7 天联调、第 9 天结课回溯的按日依据。回溯要点——何时引入问题、谁负责哪一块。
> 负责人（全部条目）：刘易桓（独立完成）。
> 记录字段：日期 / 模块 / 计划摘要 / 自测命令与结果 / 审查问题 / 遗留事项。

---

## 2026-08-24（第 6 天）· 模块：judge 域（块 A）+ 前端 wasm 域（块 B）

### 计划摘要
- 块 A（G1 真实评测机）：实现 `judge/judge_daemon.py`（judger1 登录 → 轮询拉任务 → checkout → 取 source/problem/testdata → 本地 g++ 编译并逐测试点运行 → 回传 results/compile-info/run-info/heartbeat），后端 `FAKE_JUDGE=false` 时关闭假评测；`FAKE_JUDGE=true` 可回退。
- 块 B（G2 真实 WASM）：下载自托管 clang.wasm 资源（wasm-clang-runtime v0.1.0：clang22 + lld22 + sysroot22），`runtime.ts` 真实分支：懒加载 clang → 内存文件系统写入源码 → 编译 → 链接 → 运行 → 返回真实 stdout/stderr（demo=false）；`VITE_FAKE_WASM=1` 可回退。
- 两块按"计划—执行—核对"闭环；穿插 G3 轮询退避、G4 v-loading、G6 前端节流。

### 自测命令与结果（2026-08-24 晚回填）
- [x] 块 B：`cd frontend && node scripts/verify_clang_wasm.mjs` → **6/6 PASS**（编译 A+B → 链接 → 运行输出 `"3\n"`；语法错误 stderr 含 `expected '}'`）。修复过程：B-1 fd 重定向、B-2 argv[0]、B-3 exit 判据（见 REVIEW_NOTES）。
- [~] 块 A：`cd judge && python scripts/test_judge_daemon.py` → 本机执行**部分断言通过**：HTTP 全链路通（login/tasks/checkout/results），T2 compile_error ✓、T4 judge_error ✓、T5 降级 judge_error ✓；T1/T3 曾因 A-2（PATH 未注入，g++ 找不到 as）失败；修复后经快速核对脚本（编译/运行/语法拒绝）**ALL PASS**。完整复跑留第 7 天联调日执行留档（约 40s）。
- [~] 块 A 契约冒烟：`cd backend && python -m scripts.smoke` → 因 `FAKE_JUDGE` 默认值切换（true→false）未复跑；已在 `smoke.py` 加 `os.environ.setdefault("FAKE_JUDGE","true")` 保持冒烟契约（A-4），联调日复跑确认。
- [ ] 块 B 浏览器端：`VITE_FAKE_WASM=0 npm run dev` + 题目页运行 A+B → **未实测**（Node 链路已证；浏览器端同一套资源与参数，差异仅运行时载体 shared.js Worker + exnref），记入遗留事项。

### 审查问题（交叉阅读，见 `docs/REVIEW_NOTES.md`）
- 块 A：A-1 路径缺 `/api/v1`（已修）、A-2 g++ PATH（已修）、A-3 ctypes 64 位（已修）、A-4 smoke 适配（已修）、A-5 限频测试规避（已修）、A-6 快速程序内存采样为 0（限制，未修）。
- 块 B：B-1 Node WASI fd（已修）、B-2 argv[0]（已修）、B-3 exit 判据（已修）、B-4 vendor 资源路径（已修）、B-5 sysroot AppleDouble（未修，P3）、B-6 浏览器端未实测（待联调）、B-7 brotli（未修，构建期）。

### 遗留事项
1. **块 B 浏览器端实测**（第 7 天联调首要）：起后端+前端，playwright 走登录→题目→运行，断言 A+B→3 且无"演示模式"；验证 exnref（不支持时需自托管 clang22-noeh/lld22-noeh，当前未提供）。
2. **块 A 完整自测复跑**（`test_judge_daemon.py`）与冒烟复跑留档。
3. 穿插小项 G3 轮询退避 / G4 v-loading / G6 前端节流 顺延第 7 天。
4. brotli 压缩资源（B-7）与 sysroot AppleDouble 清理（B-5）构建期处理。
5. 演示文档 `DEMO_GUIDE.md` 2.6/2.7 步骤需在联调后更新为真实评测机/WASM 的操作路径。

---

## 2026-08-25（第 7 天）· 模块：联调贯通 + harness 收紧

### 计划摘要
- **目标**：把 A/B 两块按工作流贯通成一条可走通的路径；致命问题当日清掉；写齐 ≥5 条排错记录（含 1 条通检）。
- **任务 1**：通检脚本 `scripts/smoke_e2e.py` 串起 smoke（17）+ judge_daemon（8）+ 异常路径（6）三段；入口 `reset_db + sleep(5.2)` 规避 5s 限流。
- **任务 2**：致命漏洞——发现 `seed.py` 写 TestCase 只写 1.in/2.in（输入），**没写 1.out/2.out**（期望输出），daemon 拉 `.out` 永远 404 → 全部 system_error；test_judge_daemon 5/8 → 修复 → 8/8。
- **任务 3**：README 三处过期（启动第 3 步"第 4 天起"、环境变量表默认值、假实现边界表"替换日期"）当日清掉，对齐第 6 天真实现。
- **任务 4**：异常路径子测 6 条（题目不存在 / 非法 status / 路径穿越 / 角色不匹配 / 重复 checkout 原子性 / 评测机回传 system_error）覆盖 README 图片模板四类断点。
- **任务 5**：`docs/TROUBLESHOOTING.md` 按"现象/期望/日志/相关文件/已尝试/仍失败/修复/故障层次"模板写 7 条（>5）。
- **任务 6**：harness 收紧——把"通检通过"列为提交前必跑项（写进 AGENTS.md §4 + 报告07 §7 明日计划）。

### 自测命令与结果（当日实测全绿，已回填）
- [x] `cd OJ_web && backend/.venv/Scripts/python scripts/smoke_e2e.py` → **三段全 PASS**：
  - Phase 1：smoke 17 case，24 预期码命中 / **0 意外 500**
  - Phase 2：test_judge_daemon **8/8**（seed 补 1.out/2.out + judge_problem 只列 .in 后）
  - Phase 3：test_anomaly_paths **6/6**（A1~A6 全 PASS）
  - 末尾 `[OK] smoke_e2e 全部通过 - 可提交 / 推送`
- [x] 期间新增两处脚本自修（见 TROUBLESHOOTING §9/§10）：Phase 3 改用 `-m scripts.test_anomaly_paths`（否则 `from app.main` 找不到）；脚本顶部加 `sys.stdout.reconfigure(utf-8)`（否则 Windows GBK 控制台打印崩溃）。
- [x] 附加发现 §8：`judge_problem` 曾把 `.out` 也列为测试点 → daemon 把期望输出当输入喂给程序（静默错判）→ 已过滤只列 `.in`。
- [ ] 整体：HARNESS OK（check_harness.ps1）+ smoke_e2e OK 后 git commit/push（T7 执行）

### 审查问题（见 `docs/REVIEW_NOTES.md` 与 `docs/TROUBLESHOOTING.md`）
- §1 seed 缺 1.out/2.out（致命，已修）— 见 TROUBLESHOOTING §1
- §7 README 假实现边界表过期（致命，他人无法启动，已修）— 见 TROUBLESHOOTING §7
- 端口被占 / venv 误用 / 5s 限流残留 三项已记录到 TROUBLESHOOTING §4/§5/§6

### 遗留事项
1. smoke_e2e 进 `check_harness.ps1`（明日：AGENTS.md §4 完成标准加"smoke_e2e.py 三段全绿"）
2. OJ_BASE_URL 与后端端口一致性检查进 smoke_e2e（今日已留口）
3. 穿插小项 G3 轮询退避 / G4 v-loading / G6 前端节流 仍未做（顺延）
4. 块 B 浏览器端 playwright 联调（昨日遗留 #1）
