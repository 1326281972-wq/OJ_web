# AGENTS.md — 本仓库约束（Harness，第 6 天起）

对人、对 AI 助手**同时生效**。动任何文件前先读本节；验收以本文件"完成标准"与 `docs/` 契约为准。
配套可执行核对：`scripts/check_harness.ps1`（提交前跑一遍，见 §4）。

## 1. 允许改的地方（绿区）

| 路径 | 说明 |
|------|------|
| `backend/app/**` | 后端源码（main/core/config/models/schemas/api/services） |
| `backend/scripts/**` | seed、冒烟、契约测试 |
| `frontend/src/**` | 前端源码；`src/wasm/vendor/` 为自托管第三方运行时，改造须以 `[改造·YYYY-MM-DD]` 注释标明 |
| `judge/*.py`、`judge/scripts/**`、`judge/README.md` | 评测机 |
| `scripts/start_*.ps1 / .sh` | 启动脚本 |
| `docs/**`、`实验报告*.md`、`README.md`、`AGENTS.md`、`.gitignore` | 文档与规则 |

## 2. 禁止动的地方（红区）

- **契约文件**：`docs/api.md`、`docs/data-model.md` 是定稿契约，不得单方面改；确需变更必须先改契约并同步全部调用方。
- **他人/历史模块大改**：`backend/app/api/`、`frontend/src/` 已有页面组件只做最小必要改动，不重写、不重构（除非任务明确要求）。
- **不绕过安全边界**：不改权限校验、不伪造 token、不把假实现伪装成已完成；假实现须在文档与 UI 明示（`FAKE_JUDGE`/`VITE_FAKE_WASM`）。
- **不直接编辑本地产物**：`.env`、`*.db`、`*.sqlite`、日志、构建产物——重建用 seed/构建命令。

## 3. 禁令（密钥与依赖）

- **密钥**：`SECRET_KEY`、口令、token、私钥一律不入库；仓库只保留无秘密的 `.env.example`（白名单）。
- **依赖**：Python 依赖只进 `backend/requirements.txt`（注明用途）；前端依赖只进 `frontend/package.json`；**禁止提交** `node_modules/`、`.venv/`、依赖树。
- **工具链与预编译资源**：`judge/toolchain/`（w64devkit）、`frontend/public/clang/`（wasm-clang-runtime）只按 README 重建、**不提交**（已入 `.gitignore`）；禁止未经评估引入第三方大文件。

## 4. 完成标准（怎样算做完）

一次任务需**全部**满足：

1. 改动落在 §1 绿区，未触碰 §2 红区、未违反 §3 禁令；
2. 自测命令跑通并留结果（任务相关者至少一项）：
   - 后端契约：`cd backend && python -m scripts.smoke`
   - 块 A 评测机：`cd judge && python scripts/test_judge_daemon.py`
   - 块 B WASM：`cd frontend && node scripts/verify_clang_wasm.mjs`
   - 前端类型：`cd frontend && npx vue-tsc --noEmit`（改前端必跑）
3. 文档同步：接口变→`api.md`；架构/备忘→`PROJECT_MEMO.md`；问题→`REVIEW_NOTES.md` + `DEV_LOG.md`；每日→`实验报告XX.md`；
4. **提交前**：`cd 仓库根 && powershell -File scripts/check_harness.ps1` 输出 `HARNESS OK`，且 `git status` 无工具链/依赖树噪音，才可 `git add`。
