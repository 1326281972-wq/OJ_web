"""通用依赖：当前用户解析、角色校验。"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from ...core.errors import ApiError
from ...core.security import decode_token
from ...db import get_db
from ...models.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise ApiError(401, 40101, "not authenticated")
    try:
        payload = decode_token(cred.credentials)
        user = db.get(User, int(payload.get("sub")))
    except (JWTError, TypeError, ValueError):
        raise ApiError(401, 40101, "invalid token")  # noqa: B904
    if user is None or user.status != "active":
        raise ApiError(401, 40101, "not authenticated")
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ApiError(403, 40301, "permission denied")
        return user

    return dep
