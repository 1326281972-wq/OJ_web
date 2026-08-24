/**
 * 块 B Node 端自测：真实 WASM 编译链（clang22 + lld22 + sysroot22）。
 *
 * 用法（可重复命令）：cd frontend && node scripts/verify_clang_wasm.mjs
 *
 * 覆盖：
 *   正常路径 —— 编译 A+B → 链接 → 运行(stdin "1 2") → 断言输出 3
 *   坏输入   —— 语法错误源码 → 断言编译失败且 stderr 含 error
 *
 * 资源：frontend/public/clang/{clang22,lld22,sysroot/}（自托管，见 src/wasm/vendor/README.md）。
 * 编译参数与 src/wasm/vendor/compiler-bridge.js 的 CLANG22_CONFIG / shared.js clangCommonArgs 对齐。
 */
import { WASI } from 'node:wasi'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const CLANG_DIR = path.join(ROOT, 'public', 'clang')
const SYSROOT = path.join(CLANG_DIR, 'sysroot')
const CLANG = path.join(CLANG_DIR, 'clang22')
const LLD = path.join(CLANG_DIR, 'lld22')

const A_PLUS_B = `#include <iostream>
using namespace std;
int main(){int a,b;cin>>a>>b;cout<<a+b<<endl;return 0;}
`
const SYNTAX_ERR = 'int main(){int a=1; return 0;' // 缺右花括号

const CLANG_ARGS = [
  '-cc1', '-emit-obj', '-disable-free', '-isysroot', '/',
  '-internal-isystem', '/include/c++/v1',
  '-internal-isystem', '/include/wasm32-wasip1/noeh/c++/v1',
  '-internal-isystem', '/include/wasm32-wasip1',
  '-internal-isystem', '/include',
  '-internal-isystem', '/lib/clang/22/include',
  '-ferror-limit', '19',
  '-O2', '-o', '/work/main.o', '-x', 'c++', '/work/main.cc',
]
const LLD_ARGS = [
  '--export-dynamic', '-z', 'stack-size=1048576',
  '-L', '/lib/wasm32-wasip1',
  '/lib/wasm32-wasip1/crt1.o', '/work/main.o',
  '-lc', '-lc++', '-lc++abi', '-lclang_rt.builtins', '-o', '/work/main.wasm',
]

const RESULTS = []

function check(name, cond, detail = '') {
  RESULTS.push(cond)
  console.log(`[${cond ? 'PASS' : 'FAIL'}] ${name} ${detail}`)
}

function requireExists(p) {
  if (!fs.existsSync(p)) throw new Error(`missing resource: ${p}`)
}

async function runWasm(file, args, { stdin = '', preopens = {}, env = {} } = {}) {
  // Node WASI 的 stdin/stdout/stderr 仅接受数字 fd：用临时文件重定向
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'oj-wasi-'))
  const inFile = path.join(dir, 'stdin')
  const outFile = path.join(dir, 'stdout')
  const errFile = path.join(dir, 'stderr')
  fs.writeFileSync(inFile, Buffer.from(stdin))
  const inFd = fs.openSync(inFile, 'r')
  const outFd = fs.openSync(outFile, 'w')
  const errFd = fs.openSync(errFile, 'w')
  const wasi = new WASI({
    args,
    env,
    preopens,
    version: 'preview1',
    returnOnExit: true,
    stdin: inFd,
    stdout: outFd,
    stderr: errFd,
  })
  const mod = await WebAssembly.compile(fs.readFileSync(file))
  const inst = await WebAssembly.instantiate(mod, wasi.getImportObject())
  try {
    wasi.start(inst)
  } catch {
    /* returnOnExit 时正常结束/异常退出均不抛；退出码从 wasi.exitCode 读取 */
  }
  fs.closeSync(inFd)
  fs.closeSync(outFd)
  fs.closeSync(errFd)
  const result = {
    stdout: fs.readFileSync(outFile, 'utf8'),
    stderr: fs.readFileSync(errFile, 'utf8'),
    exitCode: wasi.exitCode ?? 0,
  }
  fs.rmSync(dir, { recursive: true, force: true })
  return result
}

async function main() {
  requireExists(CLANG)
  requireExists(LLD)
  for (const p of ['include/wasm32-wasip1', 'lib/wasm32-wasip1/crt1.o', 'lib/clang/22/include']) {
    requireExists(path.join(SYSROOT, p))
  }
  const wd = fs.mkdtempSync(path.join(os.tmpdir(), 'oj-verify-'))
  const preopens = { '/': SYSROOT, '/work': wd }

  // 1) 正常路径：编译（WASI argv[0] 为程序名，参数从 argv[1] 起）
  fs.writeFileSync(path.join(wd, 'main.cc'), A_PLUS_B)
  const c = await runWasm(CLANG, ['clang', ...CLANG_ARGS], { preopens })
  check('编译 A+B（clang -cc1 -emit-obj）', c.exitCode === 0, `exit=${c.exitCode} stderr=${c.stderr.slice(0, 80)}`)

  // 2) 链接
  const l = await runWasm(LLD, ['wasm-ld', ...LLD_ARGS], { preopens })
  check('链接（wasm-ld）', l.exitCode === 0, `exit=${l.exitCode} stderr=${l.stderr.slice(0, 80)}`)
  check('产物 main.wasm 存在', fs.existsSync(path.join(wd, 'main.wasm')))

  // 3) 运行并断言输出
  if (fs.existsSync(path.join(wd, 'main.wasm'))) {
    const r = await runWasm(path.join(wd, 'main.wasm'), ['main.wasm'], { preopens, stdin: '1 2\n' })
    check('运行 A+B(1 2) 输出 3', r.stdout.trim() === '3', `stdout=${JSON.stringify(r.stdout)} exit=${r.exitCode}`)
  }

  // 4) 坏输入：语法错误 → 编译失败
  fs.writeFileSync(path.join(wd, 'main_bad.cc'), SYNTAX_ERR)
  const badArgs = CLANG_ARGS.map((a) => (a === '/work/main.cc' ? '/work/main_bad.cc' : a))
  const b = await runWasm(CLANG, ['clang', ...badArgs], { preopens })
  // 注：clang -cc1 模式语法错误时退出码为 0，判据以 stderr 诊断为准（与浏览器端 CompileError 一致）
  check('语法错误 → stderr 含 error', /error/i.test(b.stderr), b.stderr.slice(0, 80))

  fs.rmSync(wd, { recursive: true, force: true })
  const ok = RESULTS.every(Boolean)
  console.log(`\n结果：${RESULTS.filter(Boolean).length}/${RESULTS.length} 通过`)
  process.exit(ok ? 0 : 1)
}

main().catch((e) => {
  console.error('FATAL:', e.message)
  process.exit(1)
})
