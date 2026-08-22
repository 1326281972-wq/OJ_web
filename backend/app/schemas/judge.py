"""评测机接口请求模型（字段名与 docs/api.md 一致）。"""
from pydantic import BaseModel, Field


class TasksIn(BaseModel):
    mod: int = 0
    total: int = 1
    max_running: int = 2


class ResultsIn(BaseModel):
    submission_id: int
    status: str
    time_used: int | None = None
    memory_used: int | None = None
    run_info: str | None = None


class InfoIn(BaseModel):
    info: str


class HeartbeatIn(BaseModel):
    name: str = Field(default="", max_length=64)
    mod: int = 0
    total: int = 1
