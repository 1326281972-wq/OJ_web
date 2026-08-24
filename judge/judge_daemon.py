"""judge/judge_daemon.py — 真实评测机 daemon（第 6 天·块 A）。

与 backend/app/api/v1/judge.py 及 docs/api.md 第 4 节契约一致：
  login / tasks / checkout / source / problem / testdata / results / compile-info / run-info / heartbeat

本机编译器默认使用 judge/toolchain/w64devkit/bin/g++.exe（便携 GCC 16.2），
可用环境变量 CXX 覆盖；找不到时对提交回传 judge_error（编译器缺失降级路径）。

用法：
  cd judge && python judge_daemon.py            # 常驻轮询
  OJ_BASE_URL=http://host:port python judge_daemon.py

可供 import 测试：process_pending_once(token) / judge_submission(token, task)
（judge/scripts/test_judge_daemon.py 即基于此做全链路自测。）
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.getenv("OJ_BASE_URL", "http://localhost:8000").rstrip("/")
JUDGE_USER = os.getenv("OJ_USER", "judger1")
JUDGE_PASSWORD = os.getenv("OJ_PASSWORD", "judger123")
JOB_NAME = os.getenv("JOB_ID", "judge-1")
HEARTBEAT_INTERVAL = float(os.getenv("OJ_HEARTBEAT_INTERVAL", "15"))
POLL_INTERVAL = float(os.getenv("OJ_POLL_INTERVAL", "2"))
COMPILE_TIMEOUT = float(os.getenv("OJ_COMPILE_TIMEOUT", "20"))

_JUDGE_DIR = Path(__file__).resolve().parent
DEFAULT_CXX = _JUDGE_DIR / "toolchain" / "w64devkit" / "bin" / "g++.exe"


class JudgeError(RuntimeError):
    pass


# ---------- HTTP 客户端（零依赖，urllib） ----------
def _request(
    method: str,
    path: str,
    body=None,
    token: str | None = None,
    timeout: float = 60.0,
    raw: bool = False,
):
    req = urllib.request.Request(BASE_URL + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        raise JudgeError(f"HTTP {e.code}: {e.read()[:300]!r}") from e
    except urllib.error.URLError as e:
        raise JudgeError(f"连接 {BASE_URL} 失败: {e.reason}") from e
    if raw:
        return payload
    parsed = json.loads(payload or b"{}")
    if parsed.get("code") != 0:
        raise JudgeError(f"业务错误: {parsed}")
    return parsed.get("data")


def login() -> str:
    data = _request("POST", "/api/v1/judge/login", {"user_id": JUDGE_USER, "password": JUDGE_PASSWORD})
    return data["access_token"]


def fetch_tasks(token: str, max_running: int = 4) -> list:
    data = _request("POST", "/api/v1/judge/tasks", {"mod": 0, "total": 1, "max_running": max_running}, token)
    return data or []


def checkout(token: str, sid: int) -> dict:
    return _request("POST", f"/api/v1/judge/tasks/{sid}/checkout", None, token) or {}


def fetch_source(token: str, sid: int) -> dict:
    return _request("GET", f"/api/v1/judge/tasks/{sid}/source", None, token) or {}


def fetch_problem(token: str, sid: int) -> dict:
    return _request("GET", f"/api/v1/judge/tasks/{sid}/problem", None, token) or {}


def fetch_testdata(token: str, pid: int, filename: str) -> bytes:
    return _request("GET", f"/api/v1/judge/testdata/{pid}/{filename}", None, token, raw=True)


def post_results(
    token: str,
    sid: int,
    status: str,
    time_used: int | None = None,
    memory_used: int | None = None,
    run_info: str | None = None,
):
    _request(
        "POST",
        "/api/v1/judge/results",
        {
            "submission_id": sid,
            "status": status,
            "time_used": time_used,
            "memory_used": memory_used,
            "run_info": run_info,
        },
        token,
    )


def post_compile_info(token: str, sid: int, info: str):
    _request("POST", f"/api/v1/judge/results/{sid}/compile-info", {"info": info}, token)


def post_run_info(token: str, sid: int, info: str):
    _request("POST", f"/api/v1/judge/results/{sid}/run-info", {"info": info}, token)


def post_heartbeat(token: str):
    _request("POST", "/api/v1/judge/heartbeat", {"name": JOB_NAME, "mod": 0, "total": 1}, token)


# ---------- 编译器定位 / 编译 ----------
def resolve_cxx() -> tuple[str | None, str]:
    """返回 (可用 cxx 路径 | None, 探测到的路径)。CXX 环境变量可覆盖默认工具链。"""
    cxx_env = os.getenv("CXX") or ""
    cxx = Path(cxx_env) if cxx_env else DEFAULT_CXX
    if not cxx.is_file():
        return None, str(cxx)
    return str(cxx), str(cxx)


def compile_source(cxx: str, source: str, workdir: Path) -> tuple[str | None, str, int]:
    """编译 source。成功返回 (exe 路径, '', 0)；失败返回 (None, 编译错误文本, 返回码)。"""
    src_path = workdir / "main.cpp"
    exe = workdir / "main.exe"
    src_path.write_text(source, encoding="utf-8")
    cmd = [cxx, "-O2", "-std=c++17", "-DONLINE_JUDGE", "-o", str(exe), str(src_path)]
    # w64devkit 系工具链按 PATH 查找 as/ld 等子进程，把工具链 bin 注入子进程 PATH
    env = dict(os.environ)
    env["PATH"] = str(Path(cxx).resolve().parent) + os.pathsep + env.get("PATH", "")
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=COMPILE_TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return None, "compile timeout", -1
    if proc.returncode != 0:
        text = (proc.stderr or proc.stdout or b"").decode("utf-8", "replace").strip()
        return None, text, proc.returncode
    return str(exe), "", 0


# ---------- 运行（限时/内存采样，仅 Windows 采内存） ----------
def _peak_ws_kb(pid: int) -> int:
    """Windows：GetProcessMemoryInfo 的 PeakWorkingSetSize（KB）。非 Windows 返回 0。"""
    if os.name != "nt":
        return 0
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    PROCESS_QUERY_INFORMATION = 0x0400
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetProcessMemoryInfo.restype = wintypes.BOOL
    k32.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = k32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        return 0
    try:
        c = PROCESS_MEMORY_COUNTERS()
        c.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if k32.GetProcessMemoryInfo(handle, ctypes.byref(c), c.cb):
            return int(c.PeakWorkingSetSize) // 1024
        return 0
    finally:
        k32.CloseHandle(handle)


def run_case(exe: str, stdin_data: bytes, time_limit_ms: int, memory_limit_kb: int):
    """运行一个测试点。返回 (verdict, wall_ms, peak_mem_kb)。
    verdict：bytes(stdout) | 'TLE' | 'MLE' | 'RE'。"""
    proc = subprocess.Popen(
        [exe],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(Path(exe).parent),
    )
    stop = {"flag": False}
    peak = {"kb": 0}

    def sampler():
        while not stop["flag"]:
            try:
                kb = _peak_ws_kb(proc.pid)
            except Exception:
                kb = 0
            if kb > peak["kb"]:
                peak["kb"] = kb
            time.sleep(0.03)

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    t0 = time.perf_counter()
    try:
        out, _err = proc.communicate(input=stdin_data, timeout=time_limit_ms / 1000.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        stop["flag"] = True
        th.join(timeout=1)
        return "TLE", int((time.perf_counter() - t0) * 1000), peak["kb"]
    stop["flag"] = True
    th.join(timeout=1)
    wall = int((time.perf_counter() - t0) * 1000)
    if peak["kb"] > memory_limit_kb:
        return "MLE", wall, peak["kb"]
    if proc.returncode != 0:
        return "RE", wall, peak["kb"]
    return out, wall, peak["kb"]


def normalize_output(data: bytes) -> str:
    """宽松比较：去每行行尾空白与末尾空行。"""
    text = data.decode("utf-8", "replace")
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


# ---------- 评测流程 ----------
def judge_submission(token: str, task: dict) -> str:
    """处理单个任务（检出→取数据→编译→逐点运行→回传），返回终态 status 或 'skipped'。"""
    sid = task["id"]
    if not (checkout(token, sid) or {}).get("ok"):
        return "skipped"
    source = fetch_source(token, sid)
    problem = fetch_problem(token, sid)

    language = source.get("language") or "cpp"
    if language != "cpp":
        post_results(token, sid, "judge_error", run_info=f"unsupported language: {language}")
        return "judge_error"
    if int(problem.get("spj") or 0) != 0:
        post_results(token, sid, "judge_error", run_info=f"spj={problem.get('spj')} not supported yet")
        return "judge_error"

    cxx, cxx_path = resolve_cxx()
    if cxx is None:
        post_results(token, sid, "judge_error", run_info=f"compiler not found: {cxx_path} (CXX 可覆盖)")
        return "judge_error"

    workdir = Path(tempfile.mkdtemp(prefix="oj_judge_"))
    try:
        exe, compile_err, _rc = compile_source(cxx, source["code"], workdir)
        if exe is None:
            post_compile_info(token, sid, compile_err or "(no output)")
            post_results(token, sid, "compile_error")
            return "compile_error"

        time_limit = int(problem.get("time_limit") or 1000)
        memory_limit = int(problem.get("memory_limit") or 256) * 1024  # MB -> KB
        cases = problem.get("test_cases") or []
        max_time, max_mem = 0, 0
        for i, case in enumerate(cases, 1):
            name = case["name"]
            indata = fetch_testdata(token, problem["problem_id"], name)
            expected = fetch_testdata(token, problem["problem_id"], name.replace(".in", ".out"))
            out, wall, mem = run_case(exe, indata, time_limit, memory_limit)
            max_time, max_mem = max(max_time, wall), max(max_mem, mem)
            if out == "TLE":
                post_run_info(token, sid, f"case {i} ({name}): time limit exceeded ({wall}ms)")
                post_results(token, sid, "time_limit_exceeded", time_used=wall, memory_used=mem)
                return "time_limit_exceeded"
            if out == "MLE":
                post_run_info(token, sid, f"case {i} ({name}): memory limit exceeded ({mem}KB)")
                post_results(token, sid, "memory_limit_exceeded", time_used=wall, memory_used=mem)
                return "memory_limit_exceeded"
            if out == "RE":
                post_run_info(token, sid, f"case {i} ({name}): runtime error (exit code != 0)")
                post_results(token, sid, "runtime_error", time_used=wall, memory_used=mem)
                return "runtime_error"
            if normalize_output(out) != normalize_output(expected):
                post_run_info(token, sid, f"case {i} ({name}): wrong answer")
                post_results(token, sid, "wrong_answer", time_used=wall, memory_used=mem)
                return "wrong_answer"
        post_results(token, sid, "accepted", time_used=max_time, memory_used=max_mem)
        return "accepted"
    except Exception as exc:  # noqa: BLE001 - 兜底回传 system_error，不让任务卡死
        try:
            post_results(token, sid, "system_error", run_info=f"judge exception: {exc}")
        except Exception:
            pass
        return "system_error"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def process_pending_once(token: str, max_running: int = 4) -> list:
    """拉取一批 pending 任务并逐个判定，返回 [(sid, status)]。供常驻循环与测试调用。"""
    results = []
    for task in fetch_tasks(token, max_running=max_running):
        results.append((task["id"], judge_submission(token, task)))
    return results


# ---------- 常驻循环 ----------
def _heartbeat_loop(token: str):
    while True:
        try:
            post_heartbeat(token)
        except Exception:
            pass
        time.sleep(HEARTBEAT_INTERVAL)


def run_forever() -> None:
    token = login()
    threading.Thread(target=_heartbeat_loop, args=(token,), daemon=True).start()
    print(f"[judge] {JOB_NAME} connected to {BASE_URL}, polling every {POLL_INTERVAL}s", flush=True)
    while True:
        try:
            for sid, status in process_pending_once(token):
                print(f"[judge] submission {sid} -> {status}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[judge] poll error: {exc}", file=sys.stderr, flush=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_forever()
