"""建库 + 演示数据。

运行：cd backend && python -m scripts.seed
重置：删除 backend/data/app.db 后重跑即可。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models.models import Problem, Submission, TestCase, User  # noqa: E402

A_PLUS_B = """#include <bits/stdc++.h>
using namespace std;
int main(){int a,b;cin>>a>>b;cout<<a+b<<endl;return 0;}"""

WRONG = "// wrong-answer\n" + A_PLUS_B.replace("cout<<a+b", "cout<<0")


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.user_id == "admin").first():
            print("seed 已存在，跳过（如需重置请删除 backend/data/app.db 后重跑）")
            return
        admin = User(user_id="admin", password_hash=hash_password("admin123"), nickname="Admin", role="admin")
        demo = User(user_id="demo_user", password_hash=hash_password("demo123"), nickname="Demo", role="contestant")
        judger = User(user_id="judger1", password_hash=hash_password("judger123"), nickname="Judger", role="judger")
        db.add_all([admin, demo, judger])
        db.flush()

        p = Problem(
            id=1001,
            title="A+B Problem",
            description="计算两个整数的和",
            input="一行两个整数 a b",
            output="输出 a+b",
            sample_input="1 2",
            sample_output="3",
            time_limit=1000,
            memory_limit=256,
            spj=0,
            defunct=False,
            created_by=admin.id,
        )
        db.add(p)
        db.flush()
        db.add_all(
            [
                TestCase(problem_id=p.id, name="1.in", input_file="1 2", output_file="3", order_no=1),
                TestCase(problem_id=p.id, name="2.in", input_file="10 20", output_file="30", order_no=2),
            ]
        )

        db.add_all(
            [
                Submission(user_id=demo.id, problem_id=p.id, language="cpp", code=A_PLUS_B, status="pending"),
                Submission(user_id=demo.id, problem_id=p.id, language="cpp", code=WRONG, status="pending"),
            ]
        )
        db.commit()
        print("seed 完成：admin/admin123、demo_user/demo123、judger1/judger123、题目 1001、示例提交 x2")
    finally:
        db.close()


if __name__ == "__main__":
    main()
