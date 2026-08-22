"""提交接口：创建 / 列表 / 批量状态 / 详情（主路径 提交→轮询→终态）。"""
import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.config import CODE_MAX_BYTES, SUBMIT_INTERVAL_SECONDS
from ...core.errors import ApiError
from ...db import get_db
from ...models.models import CompileInfo, Problem, RunInfo, Submission, User
from ...schemas.auth import SubmissionIn
from .deps import get_current_user

router = APIRouter()


def _sub_out(s: Submission, with_code: bool = False) -> dict:
    d = {
        "id": s.id,
        "problem_id": s.problem_id,
        "language": s.language,
        "status": s.status,
        "time_used": s.time_used,
        "memory_used": s.memory_used,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
    }
    if with_code:
        d["code"] = s.code
    return d


@router.post("/submissions", status_code=201)
def create_submission(
    body: SubmissionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(body.code.encode("utf-8")) > CODE_MAX_BYTES:
        raise ApiError(400, 42201, "code too long")
    problem = db.get(Problem, body.problem_id)
    if problem is None or problem.defunct:
        raise ApiError(404, 40401, "problem not found")
    last = (
        db.query(Submission)
        .filter(Submission.user_id == user.id)
        .order_by(Submission.id.desc())
        .first()
    )
    if last and last.submitted_at and (time.time() - last.submitted_at.timestamp()) < SUBMIT_INTERVAL_SECONDS:
        raise ApiError(429, 42901, "submit too frequent, retry in 5s")
    sub = Submission(
        user_id=user.id,
        problem_id=body.problem_id,
        language=body.language,
        code=body.code,
        status="pending",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"code": 0, "message": "ok", "data": _sub_out(sub)}


@router.get("/submissions")
def list_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    problem_id: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Submission).filter(Submission.user_id == user.id)
    if problem_id:
        q = q.filter(Submission.problem_id == problem_id)
    if status_filter:
        q = q.filter(Submission.status == status_filter)
    total = q.count()
    items = q.order_by(Submission.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "message": "ok",
        "data": {"total": total, "items": [_sub_out(s) for s in items]},
    }


@router.get("/submissions/status")
def submission_status(
    ids: str = Query(..., description="逗号分隔的提交 id，≤50"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    id_list = [int(x) for x in ids.split(",") if x.strip()][:50]
    subs = db.query(Submission).filter(Submission.id.in_(id_list)).all()
    return {"code": 0, "message": "ok", "data": [{"id": s.id, "status": s.status} for s in subs]}


@router.get("/submissions/{sid}")
def submission_detail(
    sid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(Submission, sid)
    if s is None or (s.user_id != user.id and user.role != "admin"):
        raise ApiError(404, 40401, "submission not found")
    ci = db.query(CompileInfo).filter(CompileInfo.submission_id == sid).first()
    ri = db.query(RunInfo).filter(RunInfo.submission_id == sid).first()
    d = _sub_out(s, with_code=True)
    d["compile_info"] = ci.info if ci else None
    d["run_info"] = ri.info if ri else None
    return {"code": 0, "message": "ok", "data": d}
