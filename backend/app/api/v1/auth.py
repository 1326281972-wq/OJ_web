"""认证接口：register / login / me（响应约定见 docs/api.md）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.errors import ApiError
from ...core.security import create_access_token, hash_password, verify_password
from ...db import get_db
from ...models.models import User
from ...schemas.auth import LoginIn, RegisterIn
from .deps import get_current_user

router = APIRouter()


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.user_id == body.user_id).first():
        raise ApiError(400, 41001, "user_id already exists")
    user = User(
        user_id=body.user_id,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
        email=body.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "code": 0,
        "message": "ok",
        "data": {"id": user.id, "user_id": user.user_id, "nickname": user.nickname, "role": user.role},
    }


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == body.user_id).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, 40101, "invalid user_id or password")
    if user.status != "active":
        raise ApiError(403, 40301, "user disabled")
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


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "code": 0,
        "message": "ok",
        "data": {"id": user.id, "user_id": user.user_id, "nickname": user.nickname, "role": user.role},
    }
