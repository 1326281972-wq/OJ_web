/** 浏览器内运行 C++ 的入口（主路径 WASM 运行 步骤）。
 *
 * 当前为假实现：VITE_FAKE_WASM=1（.env.development）时点击"运行"
 * 固定把题目样例输入作为输出回显，并标注"演示模式"。
 * 第 6 天替换为真实 clang.wasm（见差距清单），开关置 0 后走下方真实分支。
 */
export interface RunResult {
  stdout: string
  stderr: string
  demo: boolean
}

export async function runCode(
  _source: string,
  _language: string,
  sampleInput: string,
): Promise<RunResult> {
  if (import.meta.env.VITE_FAKE_WASM === '1') {
    // 演示模式：固定返回样例输入（模拟程序读了样例输入并原样输出）
    return { stdout: sampleInput || '(空输入)', stderr: '', demo: true }
  }
  // TODO(第 6 天)：加载预编译 clang.wasm，真实编译并运行 source
  throw new Error('WASM runtime not ready')
}
