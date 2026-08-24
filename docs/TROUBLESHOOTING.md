# 排错记录（TROUBLESHOOTING）

> 用途：第 7 天联调发现并已修的可复查排错；新增条目请照"现象 / 期望 / 日志 / 相关文件 / 已尝试 / 仍失败 / 修复"模板追加。
> 负责人：刘易桓（独立完成）。

---

## §1 致命·种子缺 1.out / 2.out → daemon 全部 `system_error`

| 字段 | 内容 |
|------|------|
| 现象 | `judge/scripts/test_judge_daemon.py` 跑出 5/8 通过：T1 正确解、T1 真实耗时>0、T3 错答三 FAIL，judged 字典里 sid 1/2/3/5 都是 `system_error` |
| 期望 | T1 → `accepted` 且 `time_used > 0`；T3 → `wrong_answer` |
| 日志 | `INFO: GET /api/v1/judge/testdata/1001/1.out 404 Not Found`；daemon 报 `test data not found: 1.out` → 兜底成 `system_error` 回传 |
| 相关文件 | `backend/scripts/seed.py` 第 53-55 行（早期 TestCase 只写 1.in / 2.in，无 1.out / 2.out）；`backend/app/api/v1/judge.py` 第 172-176 行（testdata endpoint 从 `TestCase.input_file/output_file` 读） |
| 已尝试 | `Get-ChildItem -Recurse` 全仓找 1.in / 1.out / testdata 物理文件：0 命中 → 排除"物理文件丢失"；读 `TestCase` 表 row：`input_file` 有值，`output_file` 全 None |
| 仍失败 | seed.py 创建 TestCase 时只写输入，未补输出 |
| 修复 | seed.py 改为 4 行：1.in + 1.out + 2.in + 2.out（同步加注释指明"daemon 拉 .in 喂数据、.out 比对"）；删 `backend/data/app.db` 重 seed；test_judge_daemon 5/8 → 8/8 |
| 故障层次 | 第 3 层（数据/种子层），不是 API 层或路由层——快速通检拉到 daemon 日志才暴露（前端不会发现） |

---

## §2 拼装·字段不一致（README 图片模板同型）：`POST /api/v1/submissions` 500 "problem_id 外键"

| 字段 | 内容 |
|------|------|
| 现象 | 若 seed 阶段未把 `Problem` 真正 commit 落库，submissions API 接到新请求时数据库触发 `IntegrityError: FOREIGN KEY constraint failed: submission.problem_id`，POST `/api/v1/submissions` 返 **500** |
| 期望 | 返 201 created（happy path），或 40401 "problem not found"（题目确实不存在） |
| 日志 | uvicorn 500 堆栈：`sqlalchemy.exc.IntegrityError: FOREIGN KEY constraint failed: submission.problem_id`；最近一次日志 `已尝试：重启服务；改用约定中的示例 JSON` |
| 相关文件 | `backend/app/models/models.py` `Submission.problem_id` 外键 → `problem.id`；`backend/scripts/seed.py` `db.add(p); db.flush(); db.add_all([...TestCase...])` |
| 已尝试 | 重启服务、清 db 重 seed；把请求 JSON 字段换成约定的 `problem_id` + `language` + `code` 三件套 |
| 仍失败 | seed 写 Problem 时若 `db.commit()` 漏掉、或 `db.flush()` 顺序错，Problem 行的 id 不会落库 → 后端写 submission 时外键悬空 → 500 |
| 修复 | seed.py 主流程加 `db.flush()` 后再 `db.add_all(Submission)`；联调日重置 db + 跑 smoke 验证 17 case 全 2xx/预期失败码，0 个 500 |
| 故障层次 | 第 2 层（持久化层）；症状在第 1 层（HTTP 500）但根因在数据写入路径——直接看错误信息是 SQL 外键就能定位 |

---

## §3 通检·端到端贯通脚本：smoke + judge_daemon + 异常路径 三段串联

| 字段 | 内容 |
|------|------|
| 现象 | 之前跑冒烟靠两段分散：smoke.py 在 backend cwd 跑、test_judge_daemon.py 在 judge cwd 跑。联调日拉新人来跑容易漏跑第二段，或两段用不同 db 路径 |
| 期望 | 一条命令在 OJ_web 根跑完三段：契约 17 case、端到端 8 项、异常路径 6 项；任一 FAIL 立即退出并打尾部日志 |
| 日志 | 见 §1/§2；`scripts/smoke_e2e.py` 整合：Phase 1 backend/smoke → Phase 2 judge/test_judge_daemon → Phase 3 scripts/test_anomaly_paths |
| 相关文件 | `scripts/smoke_e2e.py`（新增）；`backend/scripts/smoke.py`（Phase 1）；`judge/scripts/test_judge_daemon.py`（Phase 2）；`backend/scripts/test_anomaly_paths.py`（新增，Phase 3） |
| 已尝试 | 直接合两段 → TestClient 启动冲突；分两子进程 → OK 但缺异常路径覆盖 |
| 仍失败 | 三段无统一入口；reset_db 与限流缓冲散落 |
| 修复 | 新建 `scripts/smoke_e2e.py`：入口 reset_db（删 db + reseed + 5.2s 限流缓冲）→ 串行调三段 → 全 PASS 打印"可提交/推送"，任一 FAIL 打印尾部 1.5~2KB 上下文并 exit 1；推荐加进 `check_harness.ps1`（已提，TODO） |
| 故障层次 | 工程化层（工作流衔接），非单点 bug——把第 1/2/3 层的检查放在同一开关里，让"今日致命问题是否清完"一条命令即可答 |

---

## §4 环境·端口 8000 被占用：`uvicorn` 启动报 `Only one usage of each socket address`

| 字段 | 内容 |
|------|------|
| 现象 | `cd backend && python -m uvicorn app.main:app --port 8000` 报 `ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)` |
| 期望 | uvicorn 在 8000 端口成功监听；或起在 OJ_PORT 指定的备用端口 |
| 日志 | uvicorn 启动 traceback；`netstat -ano | findstr :8000` 看到旧 PID 仍 LISTENING |
| 相关文件 | `scripts/start_backend.ps1`（默认端口硬编码 8000）；`backend/app/core/config.py`（OJ_PORT env 默认 8000） |
| 已尝试 | 杀占用 PID；改用 `--port 8001`（`OJ_PORT=8001`） |
| 仍失败 | 启动脚本未自动检测端口；评测机 `OJ_BASE_URL` 仍指 8000 → daemon 找不到后端 |
| 修复 | start_backend.ps1 启动前 `netstat -ano | findstr :8000` 给出占用 PID 提示；评测机 `OJ_BASE_URL` 与后端端口必须同步（在 `judge/README.md` 已注明，TODO 把端口同步检查加进 smoke_e2e） |
| 故障层次 | 环境层（OS/进程），与代码无关——纯运维姿势 |

---

## §5 环境·工作目录/依赖：cd backend 时未激活 venv → `ModuleNotFoundError: No module named 'fastapi'`

| 字段 | 内容 |
|------|------|
| 现象 | `cd backend && python -m uvicorn app.main:app` 报 `ModuleNotFoundError: No module named 'fastapi'`，退出 1 |
| 期望 | uvicorn 启动正常监听 |
| 日志 | Python traceback 顶层 ModuleNotFoundError；`where python` 显示系统 Python 而非 venv 内 Python |
| 相关文件 | `backend/.venv/`（存在但未激活）；`backend/requirements.txt`（依赖清单） |
| 已尝试 | `pip install fastapi` 装到系统 Python（污染全局） |
| 仍失败 | 走错解释器 |
| 修复 | 启动脚本统一用 `.\.venv\Scripts\python`（start_backend.ps1 / test_judge_daemon.py 已 OK）；smoke_e2e.py 也用 VENV_PY 拼路径，不依赖 PATH 顺序 |
| 故障层次 | 环境层（解释器/虚拟环境），与代码无关 |

---

## §6 脏数据·提交限流残留：连跑两次 smoke 撞 42901

| 字段 | 内容 |
|------|------|
| 现象 | 第一次跑通 `smoke.py` 全部 17 case 后，紧接着再跑一次，第二次 `submit` 立刻返 `409 {'code': 40901, 'message': 'submit too frequently'}` |
| 期望 | smoke 在干净 db 下能完整跑完 17 case；联调日可重跑 |
| 日志 | `submit 409 40901`；后端 `submissions.py` 检查 `submitted_at` 距今 < 5s 即返 42901 |
| 相关文件 | `backend/app/api/v1/submissions.py` `SUBMIT_INTERVAL_SECONDS=5`；`backend/scripts/seed.py` 写 2 个 pending submission 占位 |
| 已尝试 | 删 `backend/data/app.db` 重 seed；`backdate_submission` 提交后回拨时间（test_judge_daemon 已用此招） |
| 仍失败 | smoke.py 第二次跑时 demo_user 的 5s 限流窗口未过期 |
| 修复 | smoke_e2e.py 入口 `reset_db()` 删 db + reseed + `time.sleep(5.2)` 等限流窗口；smoke.py 本身不动（保持契约） |
| 故障层次 | 数据层（db 残留）→ API 层（限流）表象——快速通检要先 reset 才能"白盒" |

---

## §7 文档·假实现边界表/启动第 3 步过期：他人在新机器按 README 跑不通

| 字段 | 内容 |
|------|------|
| 现象 | README.md 仍写"评测机 第 4 天起置 FAKE_JUDGE=false"、"假实现边界表：后端假评测器 替换日期 第 4 天"、"VITE_FAKE_WASM 替换日期 第 5 天"——实际第 6 天两块均已替换 |
| 期望 | README 反映当前默认：`FAKE_JUDGE=false` / `VITE_FAKE_WASM=0`；保留"假实现"行作为历史参考；启动第 3 步指向 judge/README.md 的真实评测机 |
| 日志 | 无（文档层） |
| 相关文件 | `README.md` §启动 §3、§环境变量、§假实现边界 |
| 已尝试 | 直接读 `backend/app/core/config.py`（FAKE_JUDGE=false）+ `frontend/src/wasm/runtime.ts`（VITE_FAKE_WASM=0） |
| 仍失败 | 文档与现状脱节，新成员按 README 跑会出现"文档说默认 FAKE_JUDGE=true，但实际是 false；后端没自动判，提交一直 pending" |
| 修复 | README 三处修订：1) §3 评测机说明改为"第 6 天起默认 FAKE_JUDGE=false"；2) 环境变量表 FAKE_JUDGE 默认值改 false；3) 假实现边界表加"第 6 天已替换"行，并标注"默认状态即真" |
| 故障层次 | 文档层（与代码层不冲突，但导致他人无法启动）——属于"文档导致的他人无法启动"类致命问题，当日必清 |

---

## 总体：今日清掉的致命问题

| 类别 | 编号 | 严重度 | 状态 |
|------|------|--------|------|
| 数据 | §1 seed 缺 1.out/2.out | 致命（评测机 5/8 → 8/8） | ✅ |
| 文档 | §7 README 假实现边界过期 | 致命（他人无法启动） | ✅ |
| 通检 | §3 三段串联贯通 | 工程化（一条命令验收） | ✅ |
| 环境 | §4 端口被占 / §5 venv 误用 | 阻塞（新人跑不起来） | ✅ 记录+脚本兜底 |
| 脏数据 | §6 5s 限流残留 | 干扰（重跑失败） | ✅ reset_db 兜底 |

明日待补（已写进实验报告07 §7）：
- smoke_e2e 进 `check_harness.ps1` 的"提交前核对"项
- `OJ_BASE_URL` 与后端端口一致性检查

---

## §8 拼装·字段语义：`judge_problem` 把 `.out` 也列为测试点 → daemon 把期望输出当输入喂给程序

| 字段 | 内容 |
|------|------|
| 现象 | `judge.py` 的 `GET /api/v1/judge/problem/{id}` 返回 `test_cases` 时未过滤，把 seed 写入的全部 4 行（1.in / 1.out / 2.in / 2.out）都当成测试点；daemon 对每个 `name` 拉 `name` 和 `name.replace(".in", ".out")`，遇到 `1.out` 时：`fetch_testdata("1.out")` 取的是 `output_file`（即期望输出"3"）→ 作为**输入**喂给程序，程序只读到一个数字，行为未定义 |
| 期望 | `test_cases` 只列 `.in` 文件（daemon 用 `name.replace(".in", ".out")` 自行推导期望输出） |
| 日志 | 无 4xx/5xx，静默通过（A+B 恰巧读入单个数字仍可能输出 3）——**这类字段语义断点不会报错，只能靠代码审查** |
| 相关文件 | `backend/app/api/v1/judge.py` `judge_problem`（`test_cases: [{"name": c.name} for c in cases]`） |
| 已尝试 | 读 `judge_daemon.py` 的拉取循环确认契约：daemon 假定清单只含 `.in` |
| 仍失败 | 后端把 `.out` 混入清单，与 daemon 的时序假设不一致 |
| 修复 | `judge.py` 改为只返回 `.in` 结尾的 case：`test_cases = [{"name": c.name} for c in cases if c.name.endswith(".in")]`（已加注释说明第 7 天联调发现） |
| 故障层次 | 第 1 层（API 契约语义）+ 第 3 层（数据行设计）交界——两端对"测试点清单"的字段含义假设不一致 |

---

## §9 通检·Phase 3 模块导入：`python scripts/test_anomaly_paths.py` → `ModuleNotFoundError: No module named 'app'`

| 字段 | 内容 |
|------|------|
| 现象 | `smoke_e2e.py` 第一次真跑：Phase 1/2 全绿，Phase 3 子进程 stderr `ModuleNotFoundError: No module named 'app'`，退出 1 |
| 期望 | `from app.main import app` 能导入（`app` 包在 `backend/` 下） |
| 日志 | `Traceback ... line 17, in <module> from app.main import app  ^^^^ ModuleNotFoundError` |
| 相关文件 | `backend/scripts/test_anomaly_paths.py` 第 17 行；`scripts/smoke_e2e.py` `run_anomaly()` |
| 已尝试 | 直接用 `python scripts/test_anomaly_paths.py`（sys.path[0] = scripts/ 目录，找不到 backend/app） |
| 仍失败 | 直接跑 .py 时 Python 只把脚本所在目录加入 sys.path |
| 修复 | 改为 `python -m scripts.test_anomaly_paths`（与 smoke 的 `-m scripts.smoke` 一致，cwd=backend，sys.path 含 backend 根） |
| 故障层次 | 工程化层（调用约定），与业务代码无关——通检脚本自身的第一条排错记录 |

---

## §10 通检·Windows GBK 控制台：`UnicodeEncodeError: 'gbk' codec can't encode character '\u0368'`

| 字段 | 内容 |
|------|------|
| 现象 | Phase 3 修好导入后，`smoke_e2e.py` 打印子进程日志尾部时崩 `UnicodeEncodeError: 'gbk' codec can't encode character '\u0368' in position 17` |
| 期望 | 通检脚本在任何 Windows 控制台（默认 GBK）都能打印完整中文/特殊字符日志 |
| 日志 | `print(last[-1])` 处抛 UnicodeEncodeError；`\u0368`（combining double tilde）来自 analysis 结果文本 |
| 相关文件 | `scripts/smoke_e2e.py` 顶部（stdout 未配置）；子进程日志含特殊 Unicode 字符 |
| 已尝试 | 外层 PowerShell `$env:PYTHONIOENCODING="utf-8"`（可缓解但依赖调用方） |
| 仍失败 | 脚本自身不设编码，谁调谁炸 |
| 修复 | 脚本顶部 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`（Python 3.7+，已加），不依赖外层环境变量 |
| 故障层次 | 环境层（Windows 控制台代码页）——通检脚本的第二条排错记录（自举排错） |

---

## 总体：今日清掉的致命问题（更新版）

| 类别 | 编号 | 严重度 | 状态 |
|------|------|--------|------|
| 数据 | §1 seed 缺 1.out/2.out | 致命（评测机 5/8 → 8/8） | ✅ |
| 契约 | §8 judge_problem 把 .out 当测试点 | 致命（字段语义断点，静默错判） | ✅ |
| 文档 | §7 README 假实现边界过期 + `.env.example` 仍 FAKE_JUDGE=true | 致命（他人无法启动/跑错模式） | ✅ |
| 通检 | §3 三段串联 + §9/§10 脚本自修 | 工程化（一条命令验收） | ✅ |
| 环境 | §4 端口被占 / §5 venv 误用 / §10 GBK | 阻塞（新人跑不起来） | ✅ 记录+脚本兜底 |
| 脏数据 | §6 5s 限流残留 | 干扰（重跑失败） | ✅ reset_db 兜底 |

> 当日通检实测：`smoke_e2e.py` 三段全绿（Phase 1 smoke 17 / Phase 2 judge 8 / Phase 3 anomaly 6），见 `docs/DEV_LOG.md` 第 7 天。
