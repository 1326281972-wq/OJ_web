"""scripts/smoke_e2e.py - 跨模块快速通检（第 7 天联调，一键跑通整套工作流）。

调用方（顺序）：
  Phase 1  backend/scripts.smoke           17 项契约（FAKE_JUDGE=true 不需 daemon）
  Phase 2  judge/scripts/test_judge_daemon  8 项端到端真实评测（自起临时后端+daemon）
  Phase 3  scripts/test_anomaly_paths        4 条异常路径（独立子测）

设计：
  - 不假设 db 干净：先 reset（删 app.db + reseed + 等 5.2s 限流缓冲）。
  - 失败立即 exit 1 并打印子进程尾部上下文，方便排错。
  - 用项目 venv 的 python（避免走错解释器）。
  - 全 PASS 才 exit 0。

用法：
  cd OJ_web
  powershell -ExecutionPolicy Bypass -File scripts\\smoke_e2e.py       # Windows
  bash      scripts/smoke_e2e.sh                                       # Linux
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# Windows 控制台默认 GBK，子进程日志含 \u0368 等特殊字符时 print 会炸，
# 统一按 UTF-8 写 stdout（Python 3.7+）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
JUDGE = ROOT / "judge"
VENV_PY = BACKEND / ".venv" / ("Scripts" if os.name == "nt" else "bin") / (
    "python.exe" if os.name == "nt" else "python"
)
DB_FILE = BACKEND / "data" / "app.db"


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> tuple[int, str, str]:
    r = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    return r.returncode, out, err


def reset_db() -> None:
    if DB_FILE.exists():
        DB_FILE.unlink()
    rc, out, err = run([str(VENV_PY), "-m", "scripts.seed"], BACKEND)
    if rc != 0:
        print("[FAIL] reseed", out[-600:])
        print("stderr:", err[-300:])
        sys.exit(1)
    print("[OK] reset_db + reseed")
    # 限流锚点：seed 写 2 个 pending，距 demo_user 下次可提交 >=5s
    time.sleep(5.2)


def section(name: str) -> None:
    print("\n" + "=" * 64)
    print(f"  {name}")
    print("=" * 64)


def run_smoke() -> int:
    section("Phase 1 - backend/scripts.smoke (17 case)")
    env = dict(os.environ)
    env["FAKE_JUDGE"] = "true"
    rc, out, err = run([str(VENV_PY), "-m", "scripts.smoke"], BACKEND, env)
    if rc != 0:
        print("[FAIL] smoke exit", rc)
        print(out[-1500:])
        if err:
            print("stderr:", err[-500:])
        return rc
    n200 = out.count("] 200") + out.count("] 201") + out.count("] 401")
    n_unexpected = out.count("] 500")
    print(f"[OK] smoke 17 case：{n200} 预期码命中 / {n_unexpected} 意外 500")
    return 0 if n_unexpected == 0 else 1


def run_judge_e2e() -> int:
    section("Phase 2 - judge/scripts.test_judge_daemon (端到端真评测 8 项)")
    rc, out, err = run([str(VENV_PY), "scripts/test_judge_daemon.py"], JUDGE)
    if rc != 0:
        print("[FAIL] judge_daemon exit", rc)
        print(out[-2000:])
        if err:
            print("stderr:", err[-500:])
        return rc
    pass_n = out.count("[PASS]")
    fail_n = out.count("[FAIL]")
    print(f"[OK] judge_daemon：{pass_n} PASS / {fail_n} FAIL")
    return 0 if fail_n == 0 else 1


def run_anomaly() -> int:
    section("Phase 3 - scripts.test_anomaly_paths (异常路径 6 条)")
    # 必须用 -m（与 smoke 一致）：python 直接跑 .py 时 sys.path[0] 是 scripts/，
    # from app.main import app 会 ModuleNotFoundError
    rc, out, err = run([str(VENV_PY), "-m", "scripts.test_anomaly_paths"], BACKEND)
    if rc != 0:
        print("[FAIL] anomaly exit", rc)
        print(out[-2000:])
        if err:
            print("stderr:", err[-500:])
        return rc
    last = [ln for ln in out.strip().splitlines() if ln.startswith("[OK") or ln.startswith("[FAIL")]
    print(last[-1] if last else "[OK] anomaly")
    return rc


def main() -> int:
    print("OJ_web 快速通检 - 第 7 天联调")
    reset_db()
    rc = 0
    rc |= run_smoke()
    rc |= run_judge_e2e()
    rc |= run_anomaly()
    section("总结")
    if rc == 0:
        print("[OK] smoke_e2e 全部通过 - 可提交 / 推送")
    else:
        print(f"[FAIL] smoke_e2e 有失败项 rc={rc}，按上面日志定位故障层次")
    return rc


if __name__ == "__main__":
    sys.exit(main())
