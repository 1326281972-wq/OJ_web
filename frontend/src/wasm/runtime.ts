/** 浏览器内运行 C++ 的入口（主路径 WASM 运行步骤，第 6 天·块 B）。
 *
 * 真实实现：自托管 wasm-clang-runtime v0.1.0（Apache-2.0，见 vendor/README.md），
 * 编译在 Web Worker 内完成；clang22/lld22/sysroot22.tar 自托管于 /clang/
 * （frontend/public/clang/），零 npm 依赖、懒加载（首次运行才拉取）。
 *
 * VITE_FAKE_WASM=1 时仍走演示分支（.env.development 已置 0，仅调试回退用）。
 */
import { createCompileClient } from './vendor/compile-client.js'
import type { CompileClient } from './vendor/compile-client.js'

export interface RunResult {
  stdout: string
  stderr: string
  demo: boolean
}

let clientPromise: Promise<CompileClient> | null = null

function getClient(): Promise<CompileClient> {
  if (!clientPromise) {
    // 懒加载：首次运行才实例化 Worker（clang 模块随后按需 fetch）
    clientPromise = Promise.resolve().then(() =>
      createCompileClient({ hostWrite: () => {} }),
    )
  }
  return clientPromise
}

function formatError(e: unknown): string {
  const err = e as {
    name?: string
    message?: string
    rawLog?: string
    diagnostics?: Array<{ level?: string; message?: string }>
  }
  if (err?.name === 'CompileError') {
    if (err.diagnostics?.length) {
      return err.diagnostics
        .map((d) => `[${d.level ?? 'error'}] ${d.message ?? ''}`)
        .join('\n')
    }
    if (err.rawLog) return err.rawLog
  }
  if (err?.name === 'RunTimeoutError') {
    return '程序可能死循环（已强行停止）'
  }
  return err?.message ?? String(e)
}

export async function runCode(
  source: string,
  _language: string,
  sampleInput: string,
): Promise<RunResult> {
  if (import.meta.env.VITE_FAKE_WASM === '1') {
    return { stdout: sampleInput || '(空输入)', stderr: '', demo: true }
  }
  try {
    const client = await getClient()
    const r = await client.run(source, { stdin: sampleInput })
    const stderr = r.trap
      ? `程序异常终止（trap）：${r.trap}`
      : r.exitCode
        ? `程序退出码：${r.exitCode}`
        : ''
    return { stdout: r.stdout, stderr, demo: false }
  } catch (e) {
    return { stdout: '', stderr: formatError(e), demo: false }
  }
}
