"""题目接口：列表（分页）+ 详情。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.errors import ApiError
from ...db import get_db
from ...models.models import Problem
from ...schemas.problem import ProblemDetailOut, ProblemOut
from .deps import get_current_user

router = APIRouter()


@router.get("/problems")
def list_problems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: Session = Depends(get_db),
    user: Problem = Depends(get_current_user),  # noqa: ARG001  仅鉴权
):
    q = db.query(Problem).filter(Problem.defunct.is_(False))
    if keyword:
        q = q.filter(Problem.title.contains(keyword))
    total = q.count()
    items = q.order_by(Problem.id).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "total": total,
            "items": [ProblemOut.model_validate(p).model_dump() for p in items],
        },
    }


@router.get("/problems/{pid}")
def problem_detail(
    pid: int,
    db: Session = Depends(get_db),
    user: Problem = Depends(get_current_user),  # noqa: ARG001
):
    p = db.get(Problem, pid)
    if p is None or p.defunct:
        raise ApiError(404, 40401, "problem not found")
    return {"code": 0, "message": "ok", "data": ProblemDetailOut.model_validate(p).model_dump()}
