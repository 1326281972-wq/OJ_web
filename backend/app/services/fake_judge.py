"""后端假评测器（第 4 天替换为真实 judge/judge_daemon.py）。

作用：演示 提交→pending→compiling→running→终态 的状态流转，
接口契约不变，只是"谁在回传结果"不同。代码含约定标记即判失败。
开关：FAKE_JUDGE=true（默认）。第 4 天接真实评测机后置 false 并停用本模块。
"""
import threading
import time
from datetime import datetime

from ..db import SessionLocal
from ..models.models import Submission

WA_MARKER = "// wrong-answer"  # seed 数据约定的失败标记（README 有说明）


def _judge_one(db, sub: Submission) -> None:
    sub.status = "compiling"
    db.commit()
    time.sleep(0.3)
    sub.status = "running"
    db.commit()
    time.sleep(0.3)
    if WA_MARKER in (sub.code or ""):
        sub.status = "wrong_answer"
    else:
        sub.status = "accepted"
        sub.time_used = 8
        sub.memory_used = 1024
    sub.judge_time = datetime.utcnow()
    db.commit()


def _loop() -> None:
    while True:
        db = SessionLocal()
        try:
            subs = (
                db.query(Submission)
                .filter(Submission.status == "pending")
                .order_by(Submission.id)
                .limit(5)
                .all()
            )
            for s in subs:
                _judge_one(db, s)
        except Exception:
            pass
        finally:
            db.close()
        time.sleep(2)


def start() -> None:
    threading.Thread(target=_loop, daemon=True).start()
