/**
 * compile-worker —— Web Worker 内的 clang 编译服务（module worker）。
 *
 * 为什么存在：clang WASI 实例是同步 CPU 密集任务，在主线程跑会冻结输入
 * （liveSync 每次停笔 800ms 全量编译一次，编辑器明显卡顿）。
 * 这里把 astDumpJson 整个搬进 Worker，主线程只剩结构化克隆的收发。
 *
 * shared.js 是经典脚本（页面以 <script> 引入，顶层 const API = IIFE）。
 * Worker 里没有它的全局，又不能给它加 export（会破坏经典脚本用法），
 * 因此 fetch 源码包一层函数作用域求值，显式取回 API 类。
 *
 * 协议（postMessage）：
 *   收 { id, source, input }                    → ast-dump（PM 路径）
 *     { id, type: 'run', source, input, stdin } → 结果模式真跑（compileLinkRunResult）
 *   回 { id, ok: true, ast, jsonBytes }         （ast-dump）
 *      { id, ok: true, run: { stdout, exitCode, trap } }  （真跑）
 *      { id, ok: false, error: { name, message, diagnostics?, rawLog? } }
 *      { id, type: 'progress', stage }   编译阶段进度
 *      { type: 'ready' }                 worker 就绪握手（客户端此前排队请求）
 *      { type: 'log', text }             clang/系统日志（转发页面 #out）
 */

const SELF_URL = self.location.href; // Worker 脚本自身 URL（module/classic 通用，不依赖 import.meta）

let astDumpJsonFn = null;
let compileLinkRunResultFn = null;

// 当前在飞请求 id：readBuffer 的下载进度消息需要挂到请求上，主线程才能路由给
// 对应的 onProgress（编译互斥链保证串行，单变量足够）
let activeId = null;

async function readBuffer(name) {
  // [改造·2026-08-24 OJ_web] 资源（clang22 / lld22 / sysroot22.tar）自托管于
  // /clang/（frontend/public/clang/），相对路径由 ../ 改为 /clang/。
  // 弱网防线：fetch 失败自动重试 2 次（共 3 次，退避 300ms / 900ms）；仍失败抛
  // WasmLoadError——页面层（ide-core）识别后给可点击的重试卡，不再静默卡死
  //
  // gzip 直取（2026-08 手机端优化）：服务器为每个资源预生成 .gz 静态文件。
  // 走 CF 在线压缩（br/gzip）时响应是 chunked、没有 content-length，进度条无法
  // 显示总量；直取 .gz + DecompressionStream 本地解压后：
  //   - content-length 精确（13/13MB 的确定性进度）
  //   - sysroot 39MB→6.5MB、clang 35MB→13MB（与 br 同量级，但可 CDN 缓存）
  // 浏览器不支持 DecompressionStream / .gz 404 / 解压失败 → 回退裸文件路径。
  const preferGz = typeof DecompressionStream === 'function'
    && typeof TransformStream === 'function';
  const stage = name.includes('sysroot') ? '下载运行时环境' : '加载 clang 模块';

  /** 流式读取响应体并汇总；isGz 时先计压缩字节（精确进度）再解压。 */
  async function readStream(response, isGz) {
    const total = Number(response.headers.get('content-length')) || 0;
    let stream = response.body;
    if (isGz) {
      let reported = 0;
      let lastReport = 0;
      const counter = new TransformStream({
        transform(chunk, ctrl) {
          reported += chunk.byteLength;
          if (reported - lastReport >= 524288 || reported === total) { // 每 512KB 报一次
            lastReport = reported;
            postMessage({ id: activeId, type: 'progress', stage,
                          dl: { name, got: reported, total } });
          }
          ctrl.enqueue(chunk);
        },
      });
      stream = stream.pipeThrough(counter).pipeThrough(new DecompressionStream('gzip'));
    }
    const reader = stream.getReader();
    const chunks = [];
    let got = 0;
    let lastReport = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      got += value.byteLength;
      if (!isGz && got - lastReport >= 1048576) { // 裸文件路径：每 1MB 报一次
        lastReport = got;
        postMessage({ id: activeId, type: 'progress', stage,
                      dl: { name, got, total: 0 } }); // CF 在线压缩时总量不可知
      }
    }
    if (!isGz) postMessage({ id: activeId, type: 'progress', stage,
                             dl: { name, got, total: 0 } });
    const buf = new Uint8Array(got);
    let off = 0;
    for (const c of chunks) { buf.set(c, off); off += c.byteLength; }
    return buf.buffer;
  }

  let lastErr = null;
  for (let attempt = 0; attempt < 3; attempt++) {
    if (attempt > 0) await new Promise((r) => setTimeout(r, 300 * 3 ** (attempt - 1)));
    const useGz = preferGz && attempt === 0; // 首次试 .gz，失败回退裸文件
    try {
      const url = new URL(`/clang/${name}${useGz ? '.gz' : ''}`, SELF_URL);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`fetch ${name}: HTTP ${response.status}`);
      if (!response.body?.getReader) return await response.arrayBuffer();
      return await readStream(response, useGz);
    } catch (exn) {
      lastErr = exn;
    }
  }
  throw Object.assign(
    new Error(`加载 ${name} 失败（已自动重试 2 次）：${lastErr?.message ?? '网络错误'}`),
    { name: 'WasmLoadError' },
  );
}
async function compileStreaming(name) {
  return WebAssembly.compile(await readBuffer(name));
}

let bridge = null;

// exnref 探测模块（34 字节）：只含一条 try_table（opcode 0x1f，新异常处理提案）。
// clang22/lld22 二进制里各有一条 try_table，Chrome 125+ / Safari 18.4+ 才能编译；
// 微信内置浏览器（X5 内核 / 旧 WKWebView）会直接编译失败。探测不过就切换到
// wasm-opt -all --strip-eh 生成的 clang22-noeh / lld22-noeh（剥掉 EH 指令后
// 二进制其余部分完全一致；被剥的唯一 try_table 是 clang 驱动层的兜底 catch，
// 剥掉后内部异常从「打印错误」退化为 trap，正常编译路径不受影响）。
const EXNREF_PROBE = new Uint8Array([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, 0x01, 0x04, 0x01, 0x60,
  0x00, 0x00, 0x03, 0x02, 0x01, 0x00, 0x0a, 0x0e, 0x01, 0x0c, 0x00, 0x02,
  0x40, 0x1f, 0x40, 0x01, 0x02, 0x00, 0x01, 0x0b, 0x0b, 0x0b,
]);

async function supportsExnref() {
  try {
    await WebAssembly.compile(EXNREF_PROBE);
    return true;
  } catch {
    return false;
  }
}

async function init() {
  const sharedUrl = new URL('./shared.js', SELF_URL); // [改造·2026-08-24] shared.js 与 worker 同目录
  const sharedSrc = await (await fetch(sharedUrl)).text();
  const { API } = new Function(`${sharedSrc}\n;return { API };`)();

  const bridgeModule = await import('./compiler-bridge.js');
  astDumpJsonFn = bridgeModule.astDumpJson;
  compileLinkRunResultFn = bridgeModule.compileLinkRunResult;

  const exnref = await supportsExnref();
  // 不支持 exnref → 换 noeh 二进制（sysroot 本来就是 noeh 变体，无需切换）
  const config = exnref
    ? bridgeModule.CLANG22_CONFIG
    : { ...bridgeModule.CLANG22_CONFIG, clang: 'clang22-noeh', lld: 'lld22-noeh' };
  if (!exnref) {
    postMessage({ type: 'log', text: '当前浏览器内核较旧，已自动切换兼容版编译器。\n' });
  }

  bridge = bridgeModule.createClangApi({
    APIClass: API,
    readBuffer,
    compileStreaming,
    hostWrite: (s) => postMessage({ type: 'log', text: s }),
    config,
  });
}

self.onmessage = async (ev) => {
  const { id, source, input, stdin } = ev.data;
  activeId = id; // readBuffer 下载进度消息挂到本请求（串行互斥，无竞态）
  try {
    if (ev.data.type === 'run') {
      // 结果模式真跑：同一 Worker 内串行（主线程 pipeline 互斥链保证不并发），
      // 复用已加载的 sysroot/clang/lld 模块缓存；obj/wasm 文件名随 input 唯一化
      const run = await compileLinkRunResultFn(bridge, {
        input, contents: source,
        obj: `${input}.o`, wasm: `${input}.wasm`, stdin,
      });
      postMessage({ id, ok: true, run });
      return;
    }
    const { ast, jsonText } = await astDumpJsonFn(bridge, source, {
      input,
      onProgress: (stage) => postMessage({ id, type: 'progress', stage }),
    });
    postMessage({ id, ok: true, ast, jsonBytes: jsonText.length });
  } catch (exn) {
    postMessage({
      id,
      ok: false,
      error: {
        name: exn.name ?? 'Error',
        message: exn.message ?? String(exn),
        diagnostics: exn.diagnostics ?? null,
        rawLog: exn.rawLog ?? null,
      },
    });
  }
};

// 就绪握手：worker 初始化（fetch shared.js + 动态 import compiler-bridge）未完成时，
// 主线程过早 postMessage 会丢消息（实测无声消失）。init 完成后显式通知客户端
// 「可以发编译请求了」，此前的请求在客户端排队。
init().then(
  () => postMessage({ type: 'ready' }),
  (exn) => postMessage({
    type: 'log',
    text: `编译服务初始化失败：${exn?.message ?? exn}（请刷新重试）`,
  }),
);
