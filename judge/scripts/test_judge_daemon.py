"""judge/scripts/test_judge_daemon.py — 块 A 自测（可重复，一条命令）。

用法：cd judge && python scripts/test_judge_daemon.py

流程：
  1. 起临时后端（FAKE_JUDGE=false、临时 SQLite、端口 8011）并 seed 演示数据；
  2. 以 demo_user 提交 5 个用例：
       T1 正确解     → 期待 accepted，且真实耗时 > 0
       T2 语法错误   → 期待 compile_error，且 compile_info 非空
       T3 错误答案   → 期待 wrong_answer
       T4 未知语言   → 期待 judge_error
       T5 正确解（CXX=缺失路径）→ 期待 judge_error（编译器缺失降级路径）
  3. 调用 judge_daemon.process_pending_once()：真实 HTTP 拉任务→检出→取数据→编译→运行→回传；
  4. 逐条断言并打印 PASS/FAIL；全部通过 exit 0，否则 exit 1。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # judge/
BACKEND = ROOT.parent / "backend"
PORT = 8011
BASE = f"http://127.0.0.1:{PORT}"
TMP = Path(tempfile.mkdtemp(prefix="oj_judge_test_"))
DB = TMP / "test.db"

os.environ["OJ_BASE_URL"] = BASE
os.environ["DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
os.environ["FAKE_JUDGE"] = "false"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

import judge_daemon  # noqa: E402

A_PLUS_B = """#include <bits/stdc++.h>
using namespace std;
int main(){int a,b;cin>>a>>b;cout<<a+b<<endl;return 0;}"""
WRONG = "// wrong-answer\n" + A_PLUS_B.replace("cout<<a+b", "cout<<0")
SYNTAX_ERR = "int main(){int a=1; return 0;"  # 缺右花括号，编译必失败

PASSED: list[bool] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    PASSED.append(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


def http_post(path: str, body: dict, token: str | None = None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def http_get(path: str, token: str):
    req = urllib.request.Request(BASE + path)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def wait_server(timeout: float = 40.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE + "/api/v1/health", timeout=1):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def backdate_submission(sid: int) -> None:
    """回拨 submitted_at，规避提交接口的 5s 限频（仅测试用，不改契约）。"""
    from sqlalchemy import update as sa_update

    from app.db import SessionLocal
    from app.models.models import Submission

    db = SessionLocal()
    try:
        db.execute(sa_update(Submission).where(Submission.id == sid).values(submitted_at=datetime(2000, 1, 1)))
        db.commit()
    finally:
        db.close()


def main() -> int:
    env = dict(os.environ)
    seed = subprocess.run(
        [sys.executable, "-m", "scripts.seed"], cwd=str(BACKEND), env=env, capture_output=True
    )
    if seed.returncode != 0:
        print("seed FAIL:", seed.stderr.decode(errors="replace")[-500:])
        return 1
    print("seed OK")

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(BACKEND),
        env=env,
    )
    try:
        if not wait_server():
            print("server FAIL: backend not ready (uvicorn 是否已安装？请按 judge/README.md 使用 venv)")
            return 1
        print("backend ready")

        login = http_post("/api/v1/auth/login", {"user_id": "demo_user", "password": "demo123"})
        token = login["data"]["access_token"]

        def submit(code: str, language: str = "cpp") -> int:
            r = http_post("/api/v1/submissions", {"problem_id": 1001, "language": language, "code": code}, token)
            sid = r["data"]["id"]
            backdate_submission(sid)
            return sid

        t1 = submit(A_PLUS_B)
        t2 = submit(SYNTAX_ERR)
        t3 = submit(WRONG)
        t4 = submit("x = 1", language="python")

        jt = judge_daemon.login()
        judged = {sid: st for sid, st in judge_daemon.process_pending_once(jt, max_running=8)}
        check("T1-T4 均被 daemon 判定", set([t1, t2, t3, t4]).issubset(judged.keys()), f"judged={judged}")

        def detail(sid: int) -> dict:
            return http_get(f"/api/v1/submissions/{sid}", token)["data"]

        d1, d2, d3, d4 = detail(t1), detail(t2), detail(t3), detail(t4)
        check("T1 正确解 → accepted", d1["status"] == "accepted", f"status={d1['status']} time={d1['time_used']}ms mem={d1['memory_used']}KB")
        check("T1 真实耗时>0", (d1["time_used"] or 0) > 0, f"time_used={d1['time_used']}")
        check("T2 语法错误 → compile_error", d2["status"] == "compile_error", f"status={d2['status']}")
        check("T2 compile_info 非空", bool(d2["compile_info"]), f"info={str(d2['compile_info'])[:80]}")
        check("T3 错误答案 → wrong_answer", d3["status"] == "wrong_answer", f"status={d3['status']}")
        check("T4 未知语言 → judge_error", d4["status"] == "judge_error", f"status={d4['status']} run_info={d4['run_info']}")

        # T5：编译器缺失 → judge_error（降级路径）
        t5 = submit(A_PLUS_B)
        old_cxx = os.environ.get("CXX")
        os.environ["CXX"] = str(TMP / "missing-g++.exe")
        try:
            judge_daemon.process_pending_once(jt, max_running=8)
        finally:
            if old_cxx is None:
                os.environ.pop("CXX", None)
            else:
                os.environ["CXX"] = old_cxx
        d5 = detail(t5)
        check("T5 无编译器 → judge_error(降级)", d5["status"] == "judge_error", f"status={d5['status']} run_info={d5['run_info']}")

        ok = all(PASSED)
        print(f"\n结果：{PASSED.count(True)}/{len(PASSED)} 通过")
        return 0 if ok else 1
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
