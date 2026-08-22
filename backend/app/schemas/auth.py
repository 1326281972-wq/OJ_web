"""认证相关请求/响应模型（字段名与 data-model.md 一致）。"""
from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(min_length=1, max_length=64)
    email: str | None = None


class LoginIn(BaseModel):
    user_id: str
    password: str


class SubmissionIn(BaseModel):
    problem_id: int
    language: str = "cpp"
    code: str = Field(min_length=1, max_length=65536)
