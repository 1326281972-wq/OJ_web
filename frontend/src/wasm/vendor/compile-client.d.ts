/** wasm-clang-runtime v0.1.0 compile-client.js 的最小类型声明（自托管，Apache-2.0）。
 *  与源文件 JSDoc 签名保持一致；完整文档见 vendor/README.md。 */

export interface CompileRunOptions {
  input?: string
  stdin?: string
  onProgress?: (stage: string, downloadedBytes?: number | null) => void
}

export interface CompileRunResult {
  stdout: string
  exitCode: number | null
  trap: string | null
}

export interface CompileErrorLike extends Error {
  name: 'CompileError'
  diagnostics?: Array<{ level?: string; message?: string }>
  rawLog?: string
}

export interface AstDumpResult {
  ast: unknown
  jsonBytes: number
}

export interface CompileClient {
  astDump(
    source: string,
    options?: { input?: string; onProgress?: (stage: string) => void },
  ): Promise<AstDumpResult>
  run(source: string, options?: CompileRunOptions): Promise<CompileRunResult>
  terminate(): void
}

export declare function createCompileClient(options?: {
  hostWrite?: (message: string) => void
}): CompileClient
