/**
 * error-parser —— clang 文本诊断 → 结构化诊断（engine 层，Node/浏览器通用）。
 *
 * clang wasm 构建（LLVM 22）不支持 -fdiagnostics-format=json（实测），
 * 因此解析默认文本格式：
 *   /work/foo.cc:2:14: error: expected ';' at end of declaration
 * 后续的源码行 / caret / fix-it 行不匹配该格式，自然被忽略；
 * note/warning 同样收录，由调用方决定是否展示。
 */

const ANSI_RE = /\x1b\[[0-9;]*m/g;
const DIAG_RE = /^([^\s][^:]*):(\d+):(\d+): (fatal error|error|warning|note|remark): (.*)$/;

/**
 * @typedef {Object} Diagnostic
 * @property {string} file
 * @property {number} line   // 1-based
 * @property {number} col    // 1-based
 * @property {"error"|"warning"|"note"|"remark"} severity
 * @property {string} message
 */

/**
 * @param {string} text clang stderr（可混入我们自己的日志行；非诊断行被忽略）
 * @returns {Diagnostic[]}
 */
export function parseClangDiagnostics(text) {
  const clean = String(text ?? '').replace(ANSI_RE, '');
  const diags = [];
  for (const rawLine of clean.split('\n')) {
    const m = DIAG_RE.exec(rawLine.trim());
    if (!m) continue;
    diags.push({
      file: m[1],
      line: Number(m[2]),
      col: Number(m[3]),
      severity: m[4] === 'fatal error' ? 'error' : m[4],
      message: m[5],
    });
  }
  return diags;
}

/** 是否含 error 级诊断。 */
export function hasErrors(diags) {
  return diags.some((d) => d.severity === 'error');
}

/** 编译错误（astDumpJson 抛出）：携带结构化诊断与原始日志片段。 */
export class CompileError extends Error {
  constructor(diagnostics, rawLog) {
    const first = diagnostics.find((d) => d.severity === 'error') ?? diagnostics[0];
    super(`编译失败: ${first ? `${first.line}:${first.col} ${first.message}` : '未知错误'}`);
    this.name = 'CompileError';
    this.diagnostics = diagnostics;
    this.rawLog = rawLog;
  }
}
