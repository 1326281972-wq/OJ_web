"""统一业务异常：响应体顶层恒为 {code, message, data}，与 docs/api.md 一致。"""
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: int, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


async def api_error_handler(request, exc: ApiError):  # noqa: ANN001
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )
