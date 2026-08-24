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

## 资源文件（frontend/public/clang/）

- `clang22`（34.4MB，clang 22.1.8，wasm32-wasip1，WASI 程序）
- `lld22`（18.3MB，wasm-ld）
- `sysroot22.tar`（38MB，libc++/libc 头文件 + 静态库）

下载自 `cppstudio-io/wasm-clang-runtime` v0.1.0 release。浏览器通过 `/clang/` 静态路径加载。

## 调用入口

`frontend/src/wasm/runtime.ts` 封装 `createCompileClient()`；`VITE_FAKE_WASM=1`（默认 0）时走演示分支。

## 已知限制（详见 docs/REVIEW_NOTES.md）

- 浏览器不支持 exnref（WASM 异常提案）时会请求 `clang22-noeh`/`lld22-noeh`，当前**未自托管**（现代 Chromium/Firefox/Node≥24 均支持 exnref，无需 noeh）。
- 编译产物未经 brotli 压缩（构建期优化，第 7 天联调再处理）。
