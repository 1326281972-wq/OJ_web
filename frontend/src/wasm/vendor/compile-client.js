/**
 * compile-client —— 主线程侧的编译 Worker 客户端。
 *
 * 与 engine/compile-worker.js 配对：把 astDumpJson / compileLinkRunResult 的
 * 调用发到 Worker，返回与 compiler-bridge 同形的 Promise，
 * 错误按原类型重建（CompileError 带 diagnostics/rawLog，页面错误翻译依赖它们）。
 *
 * 结果模式真跑（run）带看门狗：真实 wasm 是同步执行，死循环会永久卡住 Worker。
 * 10s 无活动（进度/日志）或 60s 硬上限 → 判定死循环：worker.terminate() 杀掉，
 * 重建新 Worker（就绪握手重走，clang 模块缓存随之丢失、下次用时懒加载——
 * 模块经 api.getModule 缓存，terminate 后缓存与 Worker 一起销毁，重建后首个
 * 编译会重新 fetch + 编译 36MB clang，状态栏有进度提示，可接受）。
 *
 * 浏览器专用（依赖 Worker）。Node 侧测试直接用 compiler-bridge。
 */

import { CompileError } from './error-parser.js';

const RUN_IDLE_TIMEOUT_MS = 10_000; // 真跑 10s 无任何活动 → 判定死循环
const RUN_HARD_CAP_MS = 60_000;     // 真跑硬上限（边跑边刷输出的死循环也逃不掉）

/**
 * @param {object} [args]
 * @param {(str: string) => void} [args.hostWrite] clang/系统日志出口（页面 #out）
 * @returns {{
 *   astDump: (source: string, opts?: {input?: string, onProgress?: (stage: string) => void}) => Promise<{ast: object, jsonBytes: number}>,
 *   run: (source: string, opts?: {input?: string, stdin?: string}) => Promise<{stdout: string, exitCode: number|null, trap: string|null}>,
 *   terminate: () => void,
 * }}
 */
export function createCompileClient({ hostWrite = () => {} } = {}) {
  let worker = null;
  let nextId = 1;
  const pending = new Map();

  // 就绪握手：module worker 顶层 await 期间，过早 postMessage 会被无声丢弃。
  // worker 评估完会回 { type: 'ready' }，此前的编译请求在这里排队待发。
  let workerReady = false;
  let sendQueue = [];
  const post = (msg) => {
    if (workerReady) worker.postMessage(msg);
    else sendQueue.push(msg);
  };

  function clearRunTimers(p) {
    clearTimeout(p.idleTimer);
    clearTimeout(p.hardTimer);
  }

  /** 看门狗触发：拒掉真跑请求，杀 Worker 重建（clang 缓存随 Worker 销毁），
   *  其余在飞请求统一以「Worker 已重启」拒掉（下一次调用自然落到新 Worker）。 */
  function fireWatchdog(runId, reason) {
    const p = pending.get(runId);
    if (p) {
      clearRunTimers(p);
      pending.delete(runId);
      p.reject(Object.assign(new Error('程序可能死循环（已强行停止）'), {
        name: 'RunTimeoutError',
      }));
    }
    worker.terminate();
    for (const [id, q] of pending) {
      clearRunTimers(q);
      pending.delete(id);
      q.reject(Object.assign(new Error(reason), { name: 'WorkerRestartedError' }));
    }
    spawnWorker();
  }

  /** 真跑请求的活动信号（本 id 消息或全局日志）：重置 10s 空闲计时。 */
  function touchRun(p, id) {
    if (p.kind !== 'run') return;
    clearTimeout(p.idleTimer);
    p.idleTimer = setTimeout(() => fireWatchdog(id, '编译 Worker 已重启，请重试'),
                             RUN_IDLE_TIMEOUT_MS);
  }

  // Worker 脚本选择：微信内置浏览器/旧 WebKit 不支持 module worker
  // （new Worker(url, {type:'module'}) 静默失败 → 编译永远卡在加载中）。
  // 构建产物里有 esbuild 打的 classic 包 compile-worker.classic.js——
  // 优先用它（全浏览器通用）；本地开发无此文件时回退 module worker。
  const WORKER_MODULE_URL = new URL('./compile-worker.js', import.meta.url);
  const WORKER_CLASSIC_URL = new URL('./compile-worker.classic.js', import.meta.url);
  let workerScriptPromise = null;
  function resolveWorkerScript() {
    if (!workerScriptPromise) {
      workerScriptPromise = fetch(WORKER_CLASSIC_URL, { method: 'HEAD' })
        .then((r) => (r.ok
          ? { url: WORKER_CLASSIC_URL, options: undefined }
          : { url: WORKER_MODULE_URL, options: { type: 'module' } }))
        .catch(() => ({ url: WORKER_MODULE_URL, options: { type: 'module' } }));
    }
    return workerScriptPromise;
  }

  async function spawnWorker() {
    workerReady = false;
    sendQueue = [];
    const script = await resolveWorkerScript();
    worker = new Worker(script.url, script.options);

    worker.onmessage = (ev) => {
      const m = ev.data;
      if (m.type === 'ready') {
        workerReady = true;
        for (const msg of sendQueue.splice(0)) worker.postMessage(msg);
        return;
      }
      if (m.type === 'log') {
        hostWrite(m.text);
        // 全局日志没有 id：编译互斥链串行，真跑在飞时的日志基本就是它产生的
        for (const [id, p] of pending) touchRun(p, id);
        return;
      }
      const p = pending.get(m.id);
      if (!p) return;
      touchRun(p, m.id);
      if (m.type === 'progress') { p.onProgress?.(m.stage, m.dl ?? null); return; }
      clearRunTimers(p);
      pending.delete(m.id);
      if (m.ok) {
        p.resolve(p.kind === 'run' ? m.run : { ast: m.ast, jsonBytes: m.jsonBytes });
        return;
      }
      const e = m.error ?? { name: 'Error', message: '编译失败' };
      if (e.name === 'CompileError' && Array.isArray(e.diagnostics)) {
        // 诊断注入源码上下文（diag.source）：页面层 error-translator 的头文件感知
        // 建议（undeclared identifier → 补回 #include）需要比对源码里的 include，
        // 诊断自包含后调用方（ide-core/flow-view）无需改签名。
        const diags = e.diagnostics.map((d) => ({ ...d, source: p.source ?? d.source }));
        p.reject(new CompileError(diags, e.rawLog ?? ''));
      } else {
        p.reject(Object.assign(new Error(e.message), { name: e.name }));
      }
    };
    worker.onerror = (ev) => {
      const err = new Error(`编译Worker异常: ${ev.message ?? '未知'}`);
      for (const [id, p] of pending) {
        clearRunTimers(p);
        pending.delete(id);
        p.reject(err);
      }
    };
  }
  spawnWorker();

  return {
    astDump(source, { input = 'main.cc', onProgress } = {}) {
      return new Promise((resolve, reject) => {
        const id = nextId++;
        pending.set(id, { resolve, reject, onProgress, kind: 'ast', source });
        post({ id, source, input });
      });
    },
    /** 结果模式真跑：stdin 预喂（EOF 语义）；看门狗见文件头注释。 */
    run(source, { input = 'main.cc', stdin = '', onProgress } = {}) {
      return new Promise((resolve, reject) => {
        const id = nextId++;
        const p = { resolve, reject, onProgress, kind: 'run', source };
        p.idleTimer = setTimeout(() => fireWatchdog(id, '编译 Worker 已重启，请重试'),
                                 RUN_IDLE_TIMEOUT_MS);
        p.hardTimer = setTimeout(() => fireWatchdog(id, '编译 Worker 已重启，请重试'),
                                 RUN_HARD_CAP_MS);
        pending.set(id, p);
        post({ id, type: 'run', source, input, stdin });
      });
    },
    terminate() { worker.terminate(); },
  };
}
