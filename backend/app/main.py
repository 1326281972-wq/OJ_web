"""FastAPI 入口。启动：cd backend && uvicorn app.main:app --reload --port 8000"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1 import auth, problems, submissions
from .core.config import FAKE_JUDGE
from .core.errors import ApiError, api_error_handler
from .db import init_db

app = FastAPI(title="OJ Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(ApiError, api_error_handler)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(problems.router, prefix="/api/v1", tags=["problems"])
app.include_router(submissions.router, prefix="/api/v1", tags=["submissions"])


@app.get("/api/v1/health", tags=["meta"])
def health():
    return {"code": 0, "message": "ok", "data": {"status": "up", "fake_judge": FAKE_JUDGE}}


@app.on_event("startup")
def on_startup():
    init_db()
    if FAKE_JUDGE:
        from .services import fake_judge

        fake_judge.start()
