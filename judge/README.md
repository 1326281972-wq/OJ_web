# 真实评测机（第 6 天·块 A）

`judge/` 目录是独立于后端的评测机 daemon：拉任务 → 检出 → 编译（本机 g++）→ 逐测试点运行 → 回传结果。
与 `backend/app/api/v1/judge.py` 及 `docs/api.md` 第 4 节契约一致（不依赖任何第三方 HTTP 库，仅标准库）。

## 目录结构

```
judge/
├── judge_daemon.py               # 评测机主程序（可 import 亦可直接运行）
├── toolchain/w64devkit/          # 便携 GCC 16.2（下载后解压，见下）
├── scripts/test_judge_daemon.py  # 块 A 自测（全链路）
└── README.md
```

## 工具链准备

本机无系统 g++ 时，下载便携 w64devkit（GCC 16.2，约 58.6MB）解压到 `judge/toolchain/`：

```
cd judge/toolchain
curl -L -o w64devkit.7z.exe "https://github.com/skeeto/w64devkit/releases/download/v2.9.1/w64devkit-x64-2.9.1.7z.exe"
w64devkit.7z.exe -y        # 自解压出 w64devkit/ 目录
```

网络不通时可换镜像前缀：`https://ghfast.top/`（在 URL 前拼接，本次开发即用此通道）。
解压后验证：`judge/toolchain/w64devkit/bin/g++.exe --version`。

### 浏览器端 WASM 编译资源（块 B，同样已被 .gitignore 忽略）

`frontend/public/clang/` 是浏览器内编译 C++ 所需的 **4 件资源**（wasm-clang-runtime v0.1.0 三件套 + 自举编译的 memfs），新环境需手动重建：

```
cd frontend/public/clang
curl -L -o clang22  "https://github.com/cppstudio-io/wasm-clang-runtime/releases/download/v0.1.0/clang22"
curl -L -o lld22    "https://github.com/cppstudio-io/wasm-clang-runtime/releases/download/v0.1.0/lld22"
curl -L -o sysroot22.tar "https://github.com/cppstudio-io/wasm-clang-runtime/releases/download/v0.1.0/sysroot22.tar"
mkdir -p sysroot
tar -xf sysroot22.tar -C sysroot
```

同样可用 `https://ghfast.top/` 镜像前缀（文件较大，共约 90MB）。

**`memfs`（第 4 件，97KB）无 release 下载源**——它是基于 binji/wasm-clang 的 `memfs.c`（移植到 wasi-sdk 33 `<wasi/api.h>`、`MAX_NODES` 提到 8192）编译的 WASM 模块，浏览器端 `shared.js` 用它实现 VFS（untar sysroot / 读写源文件 / 交换编译产物）。**缺失时浏览器点"运行"会 fetch `/clang/memfs` 404**。源文件与自举构建脚本在 `frontend/src/wasm/vendor/README.md`「资源文件」节记录（当前保留于未入库的 `.tmp-memfs-build/`，见 `build.sh`）。

验证：`cd frontend && node scripts/verify_clang_wasm.mjs`（Node WASI 真实编译链自测，6 项全 PASS）。**注意该脚本覆盖 clang22/lld22/sysroot 三项，不加载 memfs**（Node 侧用真实文件系统 preopens）；memfs 是否就绪只能由浏览器端"运行"实测（或按 vendor/README 的 memfs 独立自测步骤）。

## 启动评测机

先启动后端（FAKE_JUDGE=false 时后端不再自带假评测）：

```
cd backend
python -m uvicorn app.main:app --port 8000
```

再启动评测机（另一终端）。`judge/` 目录无独立虚拟环境，建议用后端 venv 的解释器（Python 3.11+ 即可，daemon 仅依赖标准库）：

```
cd OJ_web
backend\.venv\Scripts\python.exe judge\judge_daemon.py   # Windows
backend/.venv/bin/python judge/judge_daemon.py           # Linux/macOS
```

环境变量（均有默认值）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `OJ_BASE_URL` | `http://localhost:8000` | 后端地址 |
| `OJ_USER` / `OJ_PASSWORD` | `judger1` / `judger123` | 评测机账号（需 judger 角色） |
| `JOB_ID` | `judge-1` | 心跳上报的机器名 |
| `CXX` | `judge/toolchain/w64devkit/bin/g++.exe` | 编译器路径，可覆盖 |
| `OJ_POLL_INTERVAL` | `2` | 拉任务间隔（秒） |
| `OJ_COMPILE_TIMEOUT` | `20` | 编译超时（秒） |

## 自测（可重复命令）

```
cd judge && python scripts/test_judge_daemon.py
```

脚本自动：起临时后端（独立端口 8011 + 临时 SQLite）→ seed → 提交 5 个用例 → 驱动 daemon 全链路判定：
- T1 正确解 → `accepted`（含真实耗时）
- T2 语法错误 → `compile_error` + compile_info
- T3 错误答案 → `wrong_answer`
- T4 未知语言 → `judge_error`
- T5 编译器缺失 → `judge_error`（降级路径）

全部 PASS 退出码 0。运行需 `uvicorn` 可用（建议在 `backend/venv` 下运行：`cd judge && ../backend/venv/Scripts/python scripts/test_judge_daemon.py`，若 venv 路径不同请相应调整）。

## 已知限制（诚实记录，见 docs/REVIEW_NOTES.md）

- 内存采样仅 Windows（`GetProcessMemoryInfo`）；Linux/macOS 下 `memory_used` 为 0。
- 暂不支持 spj 与交互题：检出后直接回传 `judge_error`。
- 单机串行处理；多机分片（tasks 的 mod/total）接口已预留，daemon 端暂按 total=1 运行。
- 输出比较为宽松模式（去行尾空白/末尾空行），非 spj。
