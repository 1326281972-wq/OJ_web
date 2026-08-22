"""全局配置：从 backend/.env 或环境变量读取。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)  # 确保 SQLite 目录存在（新机器/重装后可跑通）

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}",
)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
FAKE_JUDGE = os.getenv("FAKE_JUDGE", "true").lower() in ("1", "true", "yes")
SUBMIT_INTERVAL_SECONDS = 5   # 同一用户两次提交最小间隔（42901）
CODE_MAX_BYTES = 64 * 1024    # 代码长度上限
