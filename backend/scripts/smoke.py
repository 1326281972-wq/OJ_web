"""冒烟测试：health / register(成功+失败) / login(成功+失败) / me / problems / 提交→假评测→终态。

运行：cd backend && python -m scripts.smoke
注意：必须用 `with TestClient(app)` 才会触发 startup（假评测器线程）。
"""
import time

from fastapi.testclient import TestClient

from app.main import app


def show(name: str, r) -> None:  # noqa: ANN001
    print(f"[{name}] {r.status_code} {r.json()}")


def main() -> None:
    with TestClient(app) as c:
        show("health", c.get("/api/v1/health"))

        show("register", c.post("/api/v1/auth/register", json={"user_id": "smoke_u", "password": "123456", "nickname": "Smoke"}))
        show("register_dup(失败例)", c.post("/api/v1/auth/register", json={"user_id": "smoke_u", "password": "123456", "nickname": "Smoke"}))

        r = c.post("/api/v1/auth/login", json={"user_id": "demo_user", "password": "demo123"})
        show("login", r)
        token = r.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        show("login_bad(失败例)", c.post("/api/v1/auth/login", json={"user_id": "demo_user", "password": "wrong"}))
        show("me", c.get("/api/v1/auth/me", headers=headers))
        show("problems", c.get("/api/v1/problems?page=1&page_size=20", headers=headers))
        show("problem_detail", c.get("/api/v1/problems/1001", headers=headers))

        r = c.post("/api/v1/submissions", headers=headers, json={"problem_id": 1001, "language": "cpp", "code": "int main(){return 0;}"})
        show("submit", r)
        sid = r.json()["data"]["id"]
        show("status(即时)", c.get(f"/api/v1/submissions/status?ids={sid}", headers=headers))
        time.sleep(7)  # 等假评测器跑完（FAKE_JUDGE=true）
        show("status(终态)", c.get(f"/api/v1/submissions/status?ids={sid}", headers=headers))
        show("detail", c.get(f"/api/v1/submissions/{sid}", headers=headers))
        show("submit_bad(失败例)", c.post("/api/v1/submissions", headers=headers, json={"problem_id": 999, "language": "cpp", "code": "x"}))

        # ---- 评测机接口（judger 角色） ----
        rj = c.post("/api/v1/judge/login", json={"user_id": "judger1", "password": "judger123"})
        show("judge_login", rj)
        hj = {"Authorization": f"Bearer {rj.json()['data']['access_token']}"}
        show("judge_login_bad(失败例)", c.post("/api/v1/judge/login", json={"user_id": "judger1", "password": "wrong"}))
        show("judge_login_forbidden(选手登录失败例)", c.post("/api/v1/judge/login", json={"user_id": "demo_user", "password": "demo123"}))
        show("judge_tasks", c.post("/api/v1/judge/tasks", headers=hj, json={"mod": 0, "total": 1, "max_running": 2}))
        show("judge_tasks_denied(选手访问失败例)", c.post("/api/v1/judge/tasks", headers=headers, json={}))

        r = c.post("/api/v1/submissions", headers=headers, json={"problem_id": 1001, "language": "cpp", "code": "int main(){return 0;}"})
        sid2 = r.json()["data"]["id"]
        show("judge_checkout", c.post(f"/api/v1/judge/tasks/{sid2}/checkout", headers=hj))
        show("judge_checkout_twice(重复检出失败例)", c.post(f"/api/v1/judge/tasks/{sid2}/checkout", headers=hj))
        show("judge_source", c.get(f"/api/v1/judge/tasks/{sid2}/source", headers=hj))
        show("judge_problem", c.get(f"/api/v1/judge/tasks/{sid2}/problem", headers=hj))
        rt = c.get("/api/v1/judge/testdata/1001/1.in", headers=hj)
        print(f"[judge_testdata] {rt.status_code} content={rt.text!r}")
        rt_bad = c.get("/api/v1/judge/testdata/1001/../../etc/passwd", headers=hj)
        print(f"[judge_testdata_bad(文件名白名单失败例)] {rt_bad.status_code} {rt_bad.json()}")
        show("judge_results", c.post("/api/v1/judge/results", headers=hj, json={"submission_id": sid2, "status": "accepted", "time_used": 8, "memory_used": 1024}))
        show("judge_results_bad(非法终态失败例)", c.post("/api/v1/judge/results", headers=hj, json={"submission_id": sid2, "status": "unknown_status"}))
        show("judge_compile_info", c.post(f"/api/v1/judge/results/{sid2}/compile-info", headers=hj, json={"info": "main.cpp:1:1: error: expected ';'"}))
        show("judge_run_info", c.post(f"/api/v1/judge/results/{sid2}/run-info", headers=hj, json={"info": "segmentation fault"}))
        show("judge_heartbeat", c.post("/api/v1/judge/heartbeat", headers=hj, json={"name": "judge-node-1", "mod": 0, "total": 1}))
        show("detail_after_judge(回传后详情)", c.get(f"/api/v1/submissions/{sid2}", headers=headers))

    print("\n冒烟测试完成：上述均出现 code=0 或约定的失败码即可。")


if __name__ == "__main__":
    main()
