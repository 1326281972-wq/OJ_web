"""7 张主路径表，字段与 docs/data-model.md 一致（snake_case，三处同名）。"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), unique=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="contestant")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    sample_input: Mapped[str] = mapped_column(Text, nullable=False)
    sample_output: Mapped[str] = mapped_column(Text, nullable=False)
    time_limit: Mapped[int] = mapped_column(Integer, default=1000)
    memory_limit: Mapped[int] = mapped_column(Integer, default=256)
    spj: Mapped[int] = mapped_column(Integer, default=0)  # 0 普通 / 2 交互题
    defunct: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_file: Mapped[str | None] = mapped_column(Text)
    output_file: Mapped[str | None] = mapped_column(Text)
    order_no: Mapped[int] = mapped_column(Integer, default=0)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="cpp")
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    time_used: Mapped[int | None] = mapped_column(Integer)
    memory_used: Mapped[int | None] = mapped_column(Integer)
    judger: Mapped[str | None] = mapped_column(String(64))
    judge_time: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CompileInfo(Base):
    __tablename__ = "compile_infos"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), unique=True, nullable=False
    )
    info: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunInfo(Base):
    __tablename__ = "run_infos"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), unique=True, nullable=False
    )
    info: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JudgeMachine(Base):
    __tablename__ = "judge_machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(64))
    mod: Mapped[int | None] = mapped_column(Integer)
    total: Mapped[int | None] = mapped_column(Integer)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="offline")
