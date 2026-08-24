/**
 * compiler-bridge —— 浏览器内 clang 编排层（engine 层，Node/浏览器通用 ESM）。
 *
 * 把各页面驱动层里重复的 clang 浏览器端编排逻辑收拢到一处：
 *   - clang22/lld22/sysroot22 的 API 实例配置（原两处各抄一份）
 *   - extractJson：从 hostWrite 日志里抠 -ast-dump=json 的 JSON
 *   - clang 模块加载、ast-dump 调用、compile+link+run 调用
 *
 * 无 wasm-clang-demo 硬依赖：shared.js 的 API 类由调用方注入（createClangApi
 * 的 APIClass 参数）。不 import shared.js 的部分（extractJson / 配置常量）
 * 在 Node 侧可独立 import。
 *
 * 日志：bridge 在调用方 hostWrite 之外自建一份 log 缓冲（apiBundle.log.text），
 * ast-dump / compileLinkRun 靠它切片定位输出，调用方无需再自己维护 rawLog。
 */

import { parseClangDiagnostics, hasErrors, CompileError } from './error-parser.js';

/**
 * bits/stdc++.h —— GCC 通用头（OI/教学常用），libc++（wasi-sdk 33）不提供。
 * 编译前注入 memfs 的 /include/wasm32-wasip1/bits/stdc++.h（该父目录由
 * sysroot22.tar untar 时创建）。仅收录 libc++ 实际提供的头，避免 GCC 专属头
 * （<ext/...>、<tr1/...> 等）导致编译失败。
 */
export const BITS_STDC_HEADER = `// bits/stdc++.h (libc++/wasi-sdk 33 兼容精简版)
#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <cctype>
#include <cerrno>
#include <cfenv>
#include <cfloat>
#include <charconv>
#include <chrono>
#include <cinttypes>
#include <ciso646>
#include <climits>
#include <clocale>
#include <cmath>
#include <complex>
#include <concepts>
// noeh（无异常处理）wasm 环境不支持 <csetjmp>/<csignal>，已从精简版移除
#include <cstdarg>
#include <cstdbool>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <cuchar>
#include <cwchar>
#include <cwctype>
#include <deque>
#include <exception>
#include <filesystem>
#include <forward_list>
#include <fstream>
#include <functional>
#include <future>
#include <initializer_list>
#include <iomanip>
#include <ios>
#include <iosfwd>
#include <iostream>
#include <istream>
#include <iterator>
#include <limits>
#include <list>
#include <locale>
#include <map>
#include <memory>
#include <memory_resource>
#include <mutex>
#include <new>
#include <numbers>
#include <numeric>
#include <optional>
#include <ostream>
#include <queue>
#include <random>
#include <ranges>
#include <ratio>
#include <regex>
#include <scoped_allocator>
#include <set>
#include <shared_mutex>
#include <sstream>
#include <stack>
#include <stdexcept>
#include <streambuf>
#include <string>
#include <string_view>
#include <system_error>
#include <tuple>
#include <typeindex>
#include <typeinfo>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <valarray>
#include <variant>
#include <vector>
#include <complex.h>
#include <ctype.h>
#include <errno.h>
#include <fenv.h>
#include <float.h>
#include <inttypes.h>
#include <math.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <tgmath.h>
#include <uchar.h>
#include <wchar.h>
#include <wctype.h>
`;

/** 确保 memfs 中已注入 bits/stdc++.h（进程内幂等，api.ready 后执行）。
 *  注意路径不能以 / 开头：memfs LookupPath 对前导 / 的空首组件解析失败
 *  （返回 parent=NULL 触发 ASSERT），untar 用的就是相对根路径。 */
async function ensureBitsHeader(api) {
  if (api._bitsHeaderInjected) return;
  await api.ready; // sysroot untar 完成，include/wasm32-wasip1 目录已建
  api.memfs.addFile('include/wasm32-wasip1/bits/stdc++.h', BITS_STDC_HEADER);
  api._bitsHeaderInjected = true;
}

/** clang22 / lld22 / sysroot22.tar 的标准配置（LLVM 22.1.8, wasi-sdk 33）。 */
export const CLANG22_CONFIG = Object.freeze({
  clang: 'clang22',
  lld: 'lld22',
  sysroot: 'sysroot22.tar',
  clangResourceInclude: '/lib/clang/22/include',
  // wasi-sdk 33 layout: C headers live under include/<triple>, libc++
  // headers under include/<triple>/<eh-variant>/c++/v1.
  clangExtraArgs: Object.freeze([
    '-internal-isystem', '/include/wasm32-wasip1/noeh/c++/v1',
    '-internal-isystem', '/include/wasm32-wasip1',
  ]),
  lldLibdir: 'lib/wasm32-wasip1',
  // LLVM 22 wasm-ld dropped --no-threads.
  lldFlags: Object.freeze(['--export-dynamic']),
  lldLibs: Object.freeze(['-lc', '-lc++', '-lc++abi', '-lclang_rt.builtins']),
});

/**
 * 从文本中抠出第一个括号配平的 {...} 块（跳过字符串字面量与转义）。
 * clang -ast-dump=json 把一个 JSON 对象写进 stdout，混在我们自己的日志行里。
 * @param {string} text
 * @returns {string|null}
 */
export function extractJson(text) {
  // 锚定 AST 根节点再往回找 '{'：诊断（warning/note）回显的源码行可能带 '{'
  // （如 int a[3] = {1, 2, 3}; 的 -Warray-bounds 警告），从全文首个 '{' 起匹配
  // 会抠到诊断文本，JSON.parse 出 "Expected property name or '}'" 天书报错
  const anchor = /"kind"\s*:\s*"TranslationUnitDecl"/.exec(text);
  const start = anchor ? text.lastIndexOf('{', anchor.index) : text.indexOf('{');
  if (start < 0) return null;
  let depth = 0, inStr = false, esc = false;
  for (let i = start; i < text.length; ++i) {
    const ch = text[i];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === '\\') esc = true;
      else if (ch === '"') inStr = false;
    } else if (ch === '"') inStr = true;
    else if (ch === '{') ++depth;
    else if (ch === '}' && --depth === 0) return text.slice(start, i + 1);
  }
  return null;
}

/**
 * 用注入的 API 类创建 clang API 实例 + 独立日志缓冲。
 *
 * 体积防线：单进程日志超过 LOG_CAP 后截断（log.truncated = true）——
 * 真身 <iostream> 的 ast-dump 会产出数百 MB，浏览器会冻结；
 * astDumpJson 看到 truncated 会抛友好错误（页面绝不冻结）。
 *
 * @param {object} args
 * @param {Function} args.APIClass shared.js 的 API 类（浏览器全局注入）
 * @param {(name: string) => Promise<ArrayBuffer>} args.readBuffer
 * @param {(name: string) => Promise<WebAssembly.Module>} args.compileStreaming
 * @param {(str: string) => void} args.hostWrite 页面日志输出
 * @param {boolean} [args.showTiming=true]
 * @param {object} [args.config=CLANG22_CONFIG]
 * @returns {{api: object, log: {text: string, truncated: boolean}}}
 */
export function createClangApi({ APIClass, readBuffer, compileStreaming, hostWrite, showTiming = true, config = CLANG22_CONFIG }) {
  const LOG_CAP = 8 * 1024 * 1024;   // 内部日志上限（防线阈值）
  const PAGE_CAP = 2 * 1024 * 1024;  // 转发给页面 #out 的上限
  const log = { text: '', truncated: false };
  let pageForwarded = 0;
  const api = new APIClass({
    readBuffer,
    compileStreaming,
    hostWrite: (s) => {
      if (!log.truncated) {
        log.text += s;
        if (log.text.length > LOG_CAP) {
          log.truncated = true;
          log.text += '\n[输出过大，已截断]\n';
        }
      }
      if (pageForwarded < PAGE_CAP) {
        pageForwarded += s.length;
        hostWrite(s);
      }
    },
    showTiming,
    ...config,
  });
  return { api, log };
}

/**
 * 浏览器内跑 clang -cc1 -ast-dump=json，返回解析好的 AST。
 * clang 模块经 api.moduleCache 缓存，重复调用不再加载。
 *
 * @param {{api: object, log: {text: string}}} bundle createClangApi 的产出
 * @param {string} source C++ 源码
 * @param {object} [options]
 * @param {string} [options.input='main.cc'] memfs 内源文件名（多次调用请传唯一名：
 *   memfs.addFile 不保证覆盖同名文件）
 * @param {(stage: string) => void} [options.onProgress] 进度回调
 * @returns {Promise<{ast: object, jsonText: string}>}
 */
export async function astDumpJson(bundle, source, { input = 'main.cc', onProgress } = {}) {
  const { api, log } = bundle;
  await api.ready; // sysroot untar
  await ensureBitsHeader(api);
  api.memfs.addFile(input, source);
  onProgress?.('加载 clang 模块');
  const clang = await api.getModule(api.clangFilename);
  onProgress?.('运行 clang -cc1 -ast-dump=json');
  const startLen = log.text.length;
  let runError = null;
  try {
    await api.run(clang, 'clang', '-cc1', '-ast-dump=json',
                  '-ast-dump-main-file-only',
                  ...api.clangCommonArgs, '-x', 'c++', input);
  } catch (exn) {
    // clang 编译错误时进程非零退出，shared.js App.run 抛 ProcExit——
    // 诊断文本已经写入日志，先解析再决定怎么报。
    runError = exn;
  }
  const slice = log.text.slice(startLen);
  // 体积防线：输出被截断（如真身 <iostream> 的数百 MB ast-dump）→ 友好报错，页面不冻结
  if (log.truncated) {
    throw new Error('这个程序包含的内容太多了（编译输出超过 8MB），试试更小的例子，或者去掉大个头文件');
  }
  // 先查诊断：clang 报错后仍会输出 error-recovery AST，不能拿它当编译成功。
  // （本构建不支持 -fdiagnostics-format=json，走文本诊断解析）
  const diagnostics = parseClangDiagnostics(slice);
  if (hasErrors(diagnostics)) throw new CompileError(diagnostics, slice);
  if (runError) throw runError;
  const jsonText = extractJson(slice);
  if (!jsonText) throw new Error('clang stdout 中未找到 AST JSON');
  return { ast: JSON.parse(jsonText), jsonText };
}

/**
 * 编译 + 链接 + 运行一个 C++ 程序（clang -emit-obj → wasm-ld → WASI 执行）。
 *
 * @param {{api: object, log: {text: string}}} bundle
 * @param {object} args
 * @param {string} args.input memfs 内源文件名
 * @param {string} args.contents 源码
 * @param {string} args.obj 目标 .o 文件名
 * @param {string} args.wasm 目标 .wasm 文件名
 * @returns {Promise<string>} 本次运行新产生的输出文本（供调用方断言程序输出）
 */
export async function compileLinkRun(bundle, { input, contents, obj, wasm }) {
  const { api, log } = bundle;
  await ensureBitsHeader(api);
  const startLen = log.text.length;
  await api.compile({ input, contents, obj });
  await api.link(obj, wasm);
  const buffer = api.memfs.getFileContents(wasm);
  const testMod = await WebAssembly.compile(buffer);
  await api.run(testMod, wasm);
  return log.text.slice(startLen);
}

/**
 * 结果模式（PM 不支持语法的真跑回退）：编译 + 链接 + 真跑，返回结构化结果。
 *
 * 与 compileLinkRun 的差别：
 *   - 编译/链接失败抛结构化错误（CompileError 带 diagnostics / LinkError 带 rawLog），
 *     调用方走儿童友好错误层，不裸丢 ProcExit；
 *   - stdin 预喂（api.memfs.setStdinStr）：真实 cin 是预喂语义，耗尽即 EOF，
 *     cin 失败后程序按 C++ 真实行为继续（变量保持默认值）——没有 PM 的交互等待；
 *   - 程序 stdout 从日志切片里剥出来（去掉 shared.js 的命令回显行与计时尾行），
 *     退出码 / wasm trap 结构化返回，而不是混在文本里。
 *
 * @param {{api: object, log: {text: string}}} bundle
 * @param {object} args
 * @param {string} args.input memfs 内源文件名
 * @param {string} args.contents 源码
 * @param {string} args.obj 目标 .o 文件名
 * @param {string} args.wasm 目标 .wasm 文件名
 * @param {string} [args.stdin] 预喂 STDIN（EOF 语义，见上）
 * @returns {Promise<{stdout: string, exitCode: number|null, trap: string|null}>}
 */
export async function compileLinkRunResult(bundle, { input, contents, obj, wasm, stdin = '' }) {
  const { api, log } = bundle;
  await ensureBitsHeader(api);

  // 编译：clang 报错时进程非零退出（ProcExit），诊断已写日志——按 astDumpJson 同款
  // 文本诊断解析抛 CompileError，页面走统一错误卡
  let startLen = log.text.length;
  try {
    await api.compile({ input, contents, obj });
  } catch (exn) {
    const slice = log.text.slice(startLen);
    const diagnostics = parseClangDiagnostics(slice);
    if (hasErrors(diagnostics)) throw new CompileError(diagnostics, slice);
    throw exn;
  }

  // 链接：noeh sysroot 下 try/catch 等会在这里炸（缺 __cxa_* 符号），
  // lld 输出不是 clang 诊断格式，包成 LinkError 由调用方翻译成友好文案
  startLen = log.text.length;
  try {
    await api.link(obj, wasm);
  } catch (exn) {
    throw Object.assign(new Error('链接失败'), {
      name: 'LinkError', rawLog: log.text.slice(startLen),
    });
  }

  api.memfs.setStdinStr(stdin);
  const buffer = api.memfs.getFileContents(wasm);
  const testMod = await WebAssembly.compile(buffer);

  startLen = log.text.length;
  let exitCode = 0, trap = null;
  try {
    // 退出码 0：App.run 内部吞掉 ProcExit(0)，正常返回
    await api.run(testMod, wasm);
  } catch (exn) {
    // 非零退出：App.run 重写错误消息后把 ProcExit（带 .code）抛出来；
    // wasm 崩溃（除零/越界 trap）是裸 RuntimeError
    if (typeof exn.code === 'number') exitCode = exn.code;
    else trap = exn.message ?? String(exn);
  }

  // 程序 stdout = 切片去掉首行 `> xxx.wasm` 命令回显、末尾 `(0.01s/0.46s)` 计时行，
  // 以及 App.run 对非零退出/trap 追加的 `Error: ...`（+JS 栈）尾块
  let stdout = log.text.slice(startLen).replace(/\x1b\[[0-9;]*m/g, '');
  stdout = stdout.replace(/^> [^\n]*\.wasm\n/, '');
  stdout = stdout.replace(/\n?\([^()\n]*s\/[^()\n]*s\)\n?$/, '');
  stdout = stdout.replace(/\n?Error: process exited with code \d+\.\n?$/, '');
  if (trap !== null) stdout = stdout.replace(/\n?Error: [^\n]*(\n\s+at [^\n]*)*\n?$/, '');
  return { stdout, exitCode, trap };
}
