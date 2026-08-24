"""backend/scripts/test_anomaly_paths.py - 异常路径子测（第 7 天联调附加）。

被 scripts/smoke_e2e.py 的 Phase 3 调用；不依赖 daemon / 不起 uvicorn（in-process TestClient）。
6 条异常路径对应 README/图片模板里"两端字段不一致、时序假设不一致、环境问题、脏数据"四类断点。

通过全部 exit 0；任一 FAIL exit 1。
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("FAKE_JUDGE", "true")  # 不启动 daemon，契约级断言

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASSED: list[bool] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    PASSED.append(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


def main() -> int:
    c = TestClient(app)

    # 准备：登录
    login = c.post("/api/v1/auth/login", json={"user_id": "demo_user", "password": "demo123"})
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    judge_login = c.post("/api/v1/judge/login", json={"user_id": "judger1", "password": "judger123"})
    assert judge_login.status_code == 200, judge_login.text
    jt = judge_login.json()["data"]["access_token"]
    JH = {"Authorization": f"Bearer {jt}"}

    # ---------- A1: 题目不存在 → 40401（两端字段不一致：提交者认为题目存在） ----------
    r = c.post(
        "/api/v1/submissions",
        json={"problem_id": 999, "language": "cpp", "code": "int main(){return 0;}"},
        headers=H,
    )
    check("A1 题目不存在 → 40401", r.status_code == 404 and r.json().get("code") == 40401, f"got {r.status_code} {r.text[:80]}")

    # ---------- A2: 评测机 sub 状态非法 status='unknown_status' → 42201 ----------
    r = c.post(
        "/api/v1/judge/results",
        json={"submission_id": 1, "status": "unknown_status"},
        headers=JH,
    )
    check("A2 评测机非法 status → 42201", r.status_code == 400 and r.json().get("code") == 42201, f"got {r.status_code}")

    # ---------- A3: testdata 文件名越界（路径穿越） → 42201 / 404 ----------
    r = c.get("/api/v1/judge/testdata/1001/..%2F..%2Fetc%2Fpasswd", headers=JH)
    check("A3 testdata 文件名越界 → 拒绝", r.status_code in (400, 404), f"got {r.status_code}")

    # ---------- A4: 选手 token 调评测机接口 → 40301（角色不匹配） ----------
    r = c.post("/api/v1/judge/tasks", json={"mod": 0, "total": 1, "max_running": 1}, headers=H)
    check("A4 选手调评测机 → 40301", r.status_code == 403 and r.json().get("code") == 40301, f"got {r.status_code}")

    # ---------- A5: 评测机重复 checkout 同一 sid → 第二次 ok=False（原子性） ----------
    # 先让 demo_user 提交一个，拿到 sid
    sr = c.post(
        "/api/v1/submissions",
        json={"problem_id": 1001, "language": "cpp", "code": "int main(){return 0;}"},
        headers=H,
    )
    # 兜底：限流 5s 时仍能拿到（前面已 reset + sleep）
    if sr.status_code == 409 and sr.json().get("code") == 40901:
        # 等待限流
        import time
        time.sleep(6)
        sr = c.post(
            "/api/v1/submissions",
            json={"problem_id": 1001, "language": "cpp", "code": "int main(){return 0;}"},
            headers=H,
        )
    assert sr.status_code == 201, sr.text
    sid = sr.json()["data"]["id"]
    r1 = c.post(f"/api/v1/judge/tasks/{sid}/checkout", headers=JH)
    r2 = c.post(f"/api/v1/judge/tasks/{sid}/checkout", headers=JH)
    check(
        "A5 重复 checkout 第二次 ok=False",
        r1.status_code == 200 and r1.json()["data"]["ok"] is True
        and r2.status_code == 200 and r2.json()["data"]["ok"] is False,
        f"r1.ok={r1.json()['data'].get('ok')} r2.ok={r2.json()['data'].get('ok')}",
    )

    # ---------- A6: 评测机 process_pending_once 在 1.out 缺失时回传 system_error ----------
    # 不删 db 演示：直接将 problem 1001 的 2.out 设为空字符串不可行（接口会 404），
    # 这里用契约层断言：把 judge/results 回传 'system_error' 时，detail API 应能拿到非空 run_info
    r = c.post(
        "/api/v1/judge/results",
        json={"submission_id": sid, "status": "system_error", "run_info": "test data not found: 1.out"},
        headers=JH,
    )
    detail = c.get(f"/api/v1/submissions/{sid}", headers=H)
    check(
        "A6 评测机回传 system_error 可在 detail 看到",
        r.status_code == 200 and detail.json()["data"]["status"] == "system_error",
        f"detail.status={detail.json()['data']['status']}",
    )

    n_pass = PASSED.count(True)
    n_fail = PASSED.count(False)
    print(f"\n[OK] anomaly {n_pass}/{len(PASSED)} 通过" if n_fail == 0 else f"\n[FAIL] anomaly {n_pass}/{len(PASSED)} 通过")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
