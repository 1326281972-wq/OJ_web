"""评测机接口：任务拉取/原子检出/源码与数据/结果回传/心跳（docs/api.md 第 4 节）。

除 /judge/login 公开外，其余接口仅 judger 角色可访问。
"""
import re
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import update
from sqlalchemy.orm import Session

from ...core.errors import ApiError
from ...core.security import create_access_token, verify_password
from ...db import get_db
from ...models.models import (
    CompileInfo,
    JudgeMachine,
    Problem,
    RunInfo,
    Submission,
    TestCase,
    User,
)
from ...schemas.auth import LoginIn
from ...schemas.judge import HeartbeatIn, InfoIn, ResultsIn, TasksIn
from .deps import get_current_user, require_roles

router = APIRouter()

TERMINAL_STATUS = {
    "accepted",
    "wrong_answer",
    "compile_error",
    "time_limit_exceeded",
    "memory_limit_exceeded",
    "runtime_error",
    "system_error",
    "judge_error",
}
# 测试数据文件名白名单：形如 1.in / 1.out
_FILENAME_RE = re.compile(r"^\d+\.(in|out)$")


@router.post("/judge/login")
def judge_login(body: LoginIn, db: Session = Depends(get_db)):
    """评测机账号登录（judger 角色），返回 access_token（同 auth/login 结构）。"""
    user = db.query(User).filter(User.user_id == body.user_id).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, 40101, "invalid user_id or password")
    if user.role != "judger":
        raise ApiError(403, 40301, "not a judger account")
    token = create_access_token(user.id, user.role)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user.id, "user_id": user.user_id, "nickname": user.nickname, "role": user.role},
        },
    }


@router.post("/judge/tasks")
def judge_tasks(
    body: TasksIn,
    judger: User = Depends(require_roles("judger")),
    db: Session = Depends(get_db),
):
    """拉取 pending 任务（mod/total 分片预留，单机取前 max_running 个）。"""
    q = db.query(Submission).filter(Submission.status == "pending")
    if body.total > 1:  # 分片预留：仅当 total>1 时按 mod 过滤 id 取模
        q = q.filter(Submission.id % body.total == body.mod)
    subs = q.order_by(Submission.id).limit(body.max_running).all()
    return {
        "code": 0,
        "message": "ok",
        "data": [
            {"id": s.id, "problem_id": s.problem_id, "language": s.language, "status": s.status}
            for s in subs
        ],
    }


@router.post("/judge/tasks/{sid}/checkout")
def judge_checkout(
    sid: int,
    judger: User = Depends(require_roles("judger")),
    db: Session = Depends(get_db),
):
    """原子检出：仅 pending 可检出，改状态为 judging 并记录 judger/judge_time；被抢返回 ok=false。"""
    result = db.execute(
        update(Submission)
        .where(Submission.id == sid, Submission.status == "pending")
        .values(status="judging", judger=judger.user_id, judge_time=datetime.utcnow())
    )
    db.commit()
    if result.rowcount == 0:
        return {"code": 0, "message": "ok", "data": {"ok": False}}
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "ok": True,
            "judger": judger.user_id,
            "judge_time": datetime.utcnow().isoformat() + "Z",
        },
    }


@router.get("/judge/tasks/{sid}/source")
def judge_source(
    sid: int,
    judger: User = Depends(require_roles("judger")),
    db: Session = Depends(get_db),
):
    s = db.get(Submission, sid)
    if s is None:
        raise ApiError(404, 40401, "submission not found")
    return {"code": 0, "message": "ok", "data": {"code": s.code, "language": s.language}}


@router.get("/judge/tasks/{sid}/problem")
def judge_problem(
    sid: int,
    judger: User = Depends(require_roles("judger")),
    db: Session = Depends(get_db),
):
    """题目限制与测试数据清单（含 spj 标记；交互题时 interactor 信息后续扩展）。"""
    s = db.get(Submission, sid)
    if s is None:
        raise ApiError(404, 40401, "submission not found")
    p = db.get(Problem, s.problem_id)
    if p is None:
        raise ApiError(404, 40401, "problem not found")
    cases = (
        db.query(TestCase)
        .filter(TestCase.problem_id == p.id)
        .order_by(TestCase.order_no)
        .all()
    )
    # 测试点清单只列 .in：daemon 用 name.replace(".in", ".out") 推导期望输出。
    # 若把 .out 也列为"测试点"，daemon 会把期望输出文件当输入喂给程序
    # （第 7 天联调发现：1.out 被当作测试点导致 A+B 读入只剩一个数字，结果不定）。
    test_cases = [{"name": c.name} for c in cases if c.name.endswith(".in")]
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "problem_id": p.id,
            "title": p.title,
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit,
            "spj": p.spj,
            "test_cases": test_cases,
        },
    }


@router.get("/judge/testdata/{pid}/{filename}")
def judge_testdata(
    pid: int,
    filename: str,
    judger: User = Depends(require_roles("judger")),
    db: Session = Depends(get_db),
):
    """测试数据文件流。文件名白名单校验（<数字>.in|.out），防止路径穿越。"""
    if not _FILENAME_RE.match(filename):
        raise ApiError(400, 42201, "invalid test data filename")
    tc = (
        db.query(TestCase)
        .filter(TestCase.problem_id == pid, TestCase.name == filename)
        .first()
    )
    content = None
    if tc:
        content = tc.input_file if filename.endswith(".in") else tc.output_file
    if content is None:
        raise ApiError(404, 40401, "test data not found")
    return Response(content=content, media_type="application/octet-stream")


@router.post("/judge/results")
def judge_results(
    body: ResultsIn,
    judger: User = Depends(require_roles("judger")),
    db: Session = Depends(get_db),
):
    """回传终态：写终态 status/time/memory/run_info。"""
    s = db.get(Submission, body.submission_id)
    if s is None:
        raise ApiError(404, 40401, "submission not found")
    if body.status not in TERMINAL_STATUS:
        raise ApiError(400, 42201, f"invalid status: {body.status}")
    s.status = body.status
    s.time_used = body.time_used
    s.memory_used = body.memory_used
    s.judger = judger.user_id
    s.judge_time = datetime.utcnow()
    if body.run_info:
        ri = db.query(RunInfo).filter(RunInfo.submission_id == s.id).first()
        if ri:
            ri.info = body.run_info
        else:
            db.add(RunInfo(submission_id=s.id, info=body.run_info))
    db.commit()
    return {"code": 0, "message": "ok", "data": None}


@router.post("/judge/results/{sid}/compile-info")
def judge_compile_info(
    sid: int,
    body: InfoIn,
    judger: User = Depends(require_roles("judger")),
    db: Session = Depends(get_db),
):
    s = db.get(Submission, sid)
    if s is None:
        raise ApiError(404, 40401, "submission not found")
    ci = db.query(CompileInfo).filter(CompileInfo.submission_id == sid).first()
    if ci:
        ci.info = body.info
    else:
        db.add(CompileInfo(submission_id=sid, info=body.info))
    db.commit()
    return {"code": 0, "message": "ok", "data": None}


@router.post("/judge/results/{sid}/run-info")
def judge_run_info(
    sid: int,
    body: InfoIn,
    judger: User = Depends(require_roles("judger")),
    db: Session = Depends(get_db),
):
    s = db.get(Submission, sid)
    if s is None:
        raise ApiError(404, 40401, "submission not found")
    ri = db.query(RunInfo).filter(RunInfo.submission_id == sid).first()
    if ri:
        ri.info = body.info
    else:
        db.add(RunInfo(submission_id=sid, info=body.info))
    db.commit()
    return {"code": 0, "message": "ok", "data": None}


@router.post("/judge/heartbeat")
def judge_heartbeat(
    body: HeartbeatIn,
    judger: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """心跳：更新 judge_machines 在线状态（judger 或 admin 均可）。"""
    jm = (
        db.query(JudgeMachine)
        .filter(JudgeMachine.user_id == judger.id)
        .first()
    )
    if jm is None:
        jm = JudgeMachine(user_id=judger.id, name=body.name, mod=body.mod, total=body.total)
        db.add(jm)
    else:
        jm.name = body.name
        jm.mod = body.mod
        jm.total = body.total
    jm.last_heartbeat = datetime.utcnow()
    jm.status = "online"
    db.commit()
    return {"code": 0, "message": "ok", "data": None}
