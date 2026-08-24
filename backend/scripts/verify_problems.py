"""backend/scripts/verify_problems.py — 全库题目数据 + 标准解真实评测验证（第 8 天回归）。

用法：cd backend && python -m scripts.verify_problems
流程：
  1. 起临时后端（FAKE_JUDGE=false、临时 SQLite、端口 8012）并 seed 全库 21 道题；
  2. 以 demo_user 逐题提交 seed.STD_SOLUTIONS 里的标准解（backdate 规避 5s 限流）；
  3. 调用 judge_daemon.process_pending_once() 真实编译运行；
  4. 断言每题均为 accepted，逐题打印 PASS/FAIL；全部通过 exit 0。
作用：验证新加题目的题面与测试数据、评测链路三件事同时成立（数据错了/题意歧义/评测断了都会 FAIL）。
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

ROOT = Path(__file__).resolve().parents[1]   # backend/
JUDGE = ROOT.parent / "judge"
PORT = 8012
BASE = f"http://127.0.0.1:{PORT}"
TMP = Path(tempfile.mkdtemp(prefix="oj_verify_"))
DB = TMP / "verify.db"

os.environ["OJ_BASE_URL"] = BASE
os.environ["DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
os.environ["FAKE_JUDGE"] = "false"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(JUDGE))

import judge_daemon  # noqa: E402
from scripts import seed  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PIDS = [1001] + [d["id"] for d in seed.PROBLEMS]
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
    seed_run = subprocess.run(
        [sys.executable, "-m", "scripts.seed"], cwd=str(ROOT), env=env, capture_output=True
    )
    if seed_run.returncode != 0:
        print("seed FAIL:", seed_run.stderr.decode(errors="replace")[-500:])
        return 1
    print(f"seed OK（题目 {len(PIDS)} 道：{PIDS}）")

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT),
        env=env,
    )
    try:
        if not wait_server():
            print("server FAIL: backend not ready")
            return 1

        login = http_post("/api/v1/auth/login", {"user_id": "demo_user", "password": "demo123"})
        token = login["data"]["access_token"]

        # 逐题提交标准解
        sids: dict[int, int] = {}
        for pid in PIDS:
            code = seed.build_solution(pid)
            r = http_post("/api/v1/submissions", {"problem_id": pid, "language": "cpp", "code": code}, token)
            sid = r["data"]["id"]
            backdate_submission(sid)
            sids[pid] = sid
        print(f"提交完成 {len(sids)} 份，开始真实评测…")

        jt = judge_daemon.login()
        judged: dict[int, str] = {}
        for _round in range(10):
            batch = judge_daemon.process_pending_once(jt, max_running=8)
            judged.update(batch)
            if len(judged) >= len(sids):
                break
        print(f"daemon 判定 {len(judged)} 份（期望 {len(sids)}）")

        for pid in PIDS:
            sid = sids[pid]
            d = http_get(f"/api/v1/submissions/{sid}", token)["data"]
            title = next(x["title"] for x in [dict(id=p["id"], title=p["title"]) for p in seed.PROBLEMS] + [dict(id=1001, title="A+B Problem")] if x["id"] == pid)
            check(f"{pid} {title} → accepted", d["status"] == "accepted",
                  f"status={d['status']} time={d['time_used']}ms mem={d['memory_used']}KB")

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
