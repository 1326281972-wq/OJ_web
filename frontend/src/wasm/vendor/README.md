# vendor/：浏览器内 clang 编译运行时（自托管）

来源：`cppstudio-io/wasm-clang-runtime` v0.1.0（Apache-2.0，License 见本目录 `LICENSE`）。
本目录是**源码自托管**，不引入任何 npm 依赖（遵守第 6 天块 B「预编译 clang.wasm 自托管」选型）。

## 文件清单

| 文件 | 说明 | 改造点（相对上游 v0.1.0） |
|------|------|---------------------------|
| `shared.js` | WASI 运行时（syscall 实现）+ memfs + 模块缓存（API 类） | 无改动 |
| `compiler-bridge.js` | clang/lld/sysroot 调用封装（CLANG22_CONFIG） | 无改动 |
| `error-parser.js` | clang 诊断 → CompileError（diagnostics） | 无改动 |
| `compile-worker.js` | Worker 侧：加载资源、untar sysroot、编译/链接/运行 | 资源路径 `../{name}` → `/clang/{name}`（资源自托管于 `frontend/public/clang/`）；`../shared.js` → `./shared.js`（同目录） |
| `compile-client.js` | 主线程 Worker 客户端（看门狗/重建） | 无改动 |
| `compile-client.d.ts` | 最小 TS 类型声明（本项目新增） | 新增 |

## 资源文件（frontend/public/clang/，共 4 件）

- `clang22`（34.4MB，clang 22.1.8，wasm32-wasip1，WASI 程序）
- `lld22`（18.3MB，wasm-ld）
- `sysroot22.tar`（38MB，libc++/libc 头文件 + 静态库）
- `memfs`（97KB，VFS 模块，浏览器端 `shared.js` 的 `MemFS` 用它实现 untar/文件读写）

前三件下载自 `cppstudio-io/wasm-clang-runtime` v0.1.0 release；`memfs` 无 release 下载源，是自举编译产物。浏览器通过 `/clang/` 静态路径加载（`compile-worker.js` 的 `readBuffer`，`memfsFilename` 默认 `'memfs'`）。

### memfs 的来源与重建

- 源：binji/wasm-clang 的 `memfs.c` + `stb_sprintf.h`（上游 `binji/llvm-project/binji`），移植到 wasi-sdk 33（`<wasi/api.h>`），`MAX_NODES` 提到 8192（sysroot22.tar untar 出 4544 个节点，2019 版上限 1024 不够）。
- 构建：`clang --target=wasm32-wasip1 -O2` 编译两目标 → `wasm-ld --no-entry --export-dynamic --allow-undefined --initial-memory=4194304` 链接（本机无 wasi 工具链时用 `node:wasi` 跑 `clang22.wasm` 自举，见 `.tmp-memfs-build/build.sh` 与 `run-wasm.mjs`，该目录未入库、保留作 repro）。
- **缺失症状**：浏览器点"运行"时 `fetch /clang/memfs` 404（SPA fallback 可能回 200+HTML 而报 instantiate 失败）。
- 独立自测：`.tmp-memfs-build/memfs-test.mjs`（untar sysroot22.tar → addFile/getFileContents 无断言）。`verify_clang_wasm.mjs` **不含** memfs 校验。

## 调用入口

`frontend/src/wasm/runtime.ts` 封装 `createCompileClient()`；`VITE_FAKE_WASM=1`（默认 0）时走演示分支。

## 已知限制（详见 docs/REVIEW_NOTES.md）

- 浏览器不支持 exnref（WASM 异常提案）时会请求 `clang22-noeh`/`lld22-noeh`，当前**未自托管**（现代 Chromium/Firefox/Node≥24 均支持 exnref，无需 noeh）。
- 编译产物未经 brotli 压缩（构建期优化，第 7 天联调再处理）。
