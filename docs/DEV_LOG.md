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
