"""建库 + 演示数据。

运行：cd backend && python -m scripts.seed
重置：删除 backend/data/app.db 后重跑即可。

题库：1001 A+B 演示题 + 1002~1021 二十道补充题（简单 ~ 中等）。
每道题带 2 组测试点（.in/.out 内容直接入库），标准解见 STD_SOLUTIONS，
用于 verify_problems.py 对全库做真实评测验证（第 8 天回归）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models.models import Problem, Submission, TestCase, User  # noqa: E402

# ---------------------------------------------------------------- 标准解
A_PLUS_B = """#include <bits/stdc++.h>
using namespace std;
int main(){int a,b;cin>>a>>b;cout<<a+b<<endl;return 0;}"""

WRONG = "// wrong-answer\n" + A_PLUS_B.replace("cout<<a+b", "cout<<0")

# 每道题的标准解（函数体，不带 include/main 外壳；评测机直接编译用户代码，
# 故验证时用 build_solution() 包装成完整程序后提交）。
# 供 verify_problems.py 对全库做真实评测验证（第 8 天回归）。
STD_SOLUTIONS: dict[int, str] = {
    1001: "int main(){int a,b;cin>>a>>b;cout<<a+b<<endl;return 0;}",
    1002: 'int main(){puts("Hello, World!");return 0;}',
    1003: "int main(){int a,b;cin>>a>>b;cout<<max(a,b)<<endl;return 0;}",
    1004: 'int main(){int n;cin>>n;cout<<(n%2?"odd":"even")<<endl;return 0;}',
    1005: "int main(){long long n;cin>>n;cout<<n*(n+1)/2<<endl;return 0;}",
    1006: 'int main(){int y;cin>>y;bool ok=(y%4==0&&y%100!=0)||y%400==0;cout<<(ok?"yes":"no")<<endl;return 0;}',
    1007: "int main(){int a,b,c;cin>>a>>b>>c;cout<<max(a,max(b,c))<<endl;return 0;}",
    1008: "int main(){int n;cin>>n;long long a=1,b=1;if(n<=2){cout<<1<<endl;return 0;}for(int i=3;i<=n;i++){long long t=a+b;a=b;b=t;}cout<<b<<endl;return 0;}",
    1009: "int main(){int n;cin>>n;int r=0;while(n){r=r*10+n%10;n/=10;}cout<<r<<endl;return 0;}",
    1010: 'int main(){int n;cin>>n;if(n<2){cout<<"no"<<endl;return 0;}for(int i=2;i*i<=n;i++)if(n%i==0){cout<<"no"<<endl;return 0;}cout<<"yes"<<endl;return 0;}',
    1011: "int main(){long long n;cin>>n;cout<<n*(n+1)*(2*n+1)/6<<endl;return 0;}",
    1012: 'int main(){char c;cin>>c;cout<<(char)(c-\'a\'+\'A\')<<endl;return 0;}',
    1013: 'int main(){double a,b,c;cin>>a>>b>>c;printf("%.2f\\n",(a+b+c)/3.0);return 0;}',
    1014: "int main(){long long a,b;cin>>a>>b;long long x=a,y=b;while(y){long long t=x%y;x=y;y=t;}cout<<x<<\" \"<<a/x*b<<endl;return 0;}",
    1015: "int main(){string s;getline(cin,s);reverse(s.begin(),s.end());cout<<s<<endl;return 0;}",
    1016: "int main(){int n;cin>>n;vector<int>a(n);for(auto&x:a)cin>>x;sort(a.begin(),a.end());for(int i=0;i<n;i++)cout<<(i?\" \":\"\")<<a[i];cout<<endl;return 0;}",
    1017: "int main(){int n;cin>>n;string s;if(n==0){cout<<0<<endl;return 0;}while(n){s=char('0'+n%2)+s;n/=2;}cout<<s<<endl;return 0;}",
    1018: "int main(){long long n;cin>>n;long long c=0;for(long long i=5;i<=n;i*=5)c+=n/i;cout<<c<<endl;return 0;}",
    1019: "int main(){string a,b;cin>>a>>b;string r;int i=a.size()-1,j=b.size()-1,c=0;while(i>=0||j>=0||c){int s=c;if(i>=0)s+=a[i--]-'0';if(j>=0)s+=b[j--]-'0';r=char('0'+s%10)+r;c=s/10;}cout<<r<<endl;return 0;}",
    1020: "int main(){int n;cin>>n;vector<int>a(n);for(auto&x:a)cin>>x;vector<int>dp(n,1);int ans=1;for(int i=0;i<n;i++){for(int j=0;j<i;j++)if(a[j]<a[i])dp[i]=max(dp[i],dp[j]+1);ans=max(ans,dp[i]);}cout<<ans<<endl;return 0;}",
    1021: "int main(){int n,W;cin>>n>>W;vector<int>dp(W+1);for(int k=0;k<n;k++){int w,v;cin>>w>>v;for(int j=W;j>=w;j--)dp[j]=max(dp[j],dp[j-w]+v);}cout<<dp[W]<<endl;return 0;}",
}

BUILD_HEADER = """#include <bits/stdc++.h>
using namespace std;
"""


def build_solution(pid: int) -> str:
    """把标准解函数体包装成评测机可编译的完整程序。"""
    return BUILD_HEADER + STD_SOLUTIONS[pid]

# ---------------------------------------------------------------- 题目数据
# cases: [(输入, 期望输出), ...]（每道题 2 组测试点）
PROBLEMS: list[dict] = [
    dict(
        id=1002, title="Hello, World!", time_limit=1000, memory_limit=256,
        description="你的第一个程序：向屏幕输出 Hello, World!",
        input="本题目没有输入。",
        output="输出一行：Hello, World!",
        sample_input="",
        sample_output="Hello, World!",
        cases=[("", "Hello, World!"), ("", "Hello, World!")],
    ),
    dict(
        id=1003, title="两数较大值", time_limit=1000, memory_limit=256,
        description="给定两个整数，输出其中较大的一个。",
        input="一行两个整数 a b。",
        output="输出 a 与 b 中较大的值。",
        sample_input="3 5",
        sample_output="5",
        cases=[("3 5", "5"), ("-7 -2", "-2")],
    ),
    dict(
        id=1004, title="奇偶判断", time_limit=1000, memory_limit=256,
        description="输入一个整数，判断它是奇数还是偶数。",
        input="一个整数 n。",
        output="若 n 为偶数输出 even，否则输出 odd。",
        sample_input="4",
        sample_output="even",
        cases=[("4", "even"), ("7", "odd")],
    ),
    dict(
        id=1005, title="1 到 N 的累加和", time_limit=1000, memory_limit=256,
        description="计算 1+2+...+N 的值。",
        input="一个整数 N（1<=N<=10^9）。",
        output="输出累加和。",
        sample_input="10",
        sample_output="55",
        cases=[("10", "55"), ("1000000000", "500000000500000000")],
    ),
    dict(
        id=1006, title="闰年判断", time_limit=1000, memory_limit=256,
        description="判断某一年是否为闰年。闰年规则：能被 4 整除但不能被 100 整除，或者能被 400 整除。",
        input="一个整数 y（年份）。",
        output="若是闰年输出 yes，否则输出 no。",
        sample_input="2000",
        sample_output="yes",
        cases=[("2000", "yes"), ("1900", "no")],
    ),
    dict(
        id=1007, title="三个数最大值", time_limit=1000, memory_limit=256,
        description="给定三个整数，输出其中最大的一个。",
        input="一行三个整数 a b c。",
        output="输出最大值。",
        sample_input="1 2 3",
        sample_output="3",
        cases=[("1 2 3", "3"), ("9 4 7", "9")],
    ),
    dict(
        id=1008, title="斐波那契数列", time_limit=1000, memory_limit=256,
        description="斐波那契数列定义为 F(1)=F(2)=1，F(n)=F(n-1)+F(n-2)。求第 N 项。",
        input="一个整数 N（1<=N<=40）。",
        output="输出 F(N)。",
        sample_input="10",
        sample_output="55",
        cases=[("10", "55"), ("40", "102334155")],
    ),
    dict(
        id=1009, title="数字反转", time_limit=1000, memory_limit=256,
        description="给定一个非负整数，将其各位数字反转（去掉前导零）后输出。",
        input="一个非负整数 n。",
        output="输出反转后的数字。",
        sample_input="12345",
        sample_output="54321",
        cases=[("12345", "54321"), ("1200", "21")],
    ),
    dict(
        id=1010, title="素数判断", time_limit=1000, memory_limit=256,
        description="判断一个正整数是否为素数。",
        input="一个整数 n（1<n<=10^6）。",
        output="若是素数输出 yes，否则输出 no。",
        sample_input="7",
        sample_output="yes",
        cases=[("7", "yes"), ("100", "no")],
    ),
    dict(
        id=1011, title="平方和", time_limit=1000, memory_limit=256,
        description="计算 1^2+2^2+...+n^2 的值。",
        input="一个整数 n（1<=n<=10^4）。",
        output="输出平方和。",
        sample_input="3",
        sample_output="14",
        cases=[("3", "14"), ("100", "338350")],
    ),
    dict(
        id=1012, title="小写转大写", time_limit=1000, memory_limit=256,
        description="输入一个小写字母，输出对应的大写字母。",
        input="一个小写字母。",
        output="输出对应的大写字母。",
        sample_input="a",
        sample_output="A",
        cases=[("a", "A"), ("z", "Z")],
    ),
    dict(
        id=1013, title="平均数", time_limit=1000, memory_limit=256,
        description="输入三个整数，输出它们的平均值，保留两位小数。",
        input="一行三个整数 a b c。",
        output="输出平均值，保留两位小数。",
        sample_input="1 2 3",
        sample_output="2.00",
        cases=[("1 2 3", "2.00"), ("1 2 4", "2.33")],
    ),
    dict(
        id=1014, title="最大公约数与最小公倍数", time_limit=1000, memory_limit=256,
        description="求两个正整数的最大公约数和最小公倍数。",
        input="一行两个正整数 a b。",
        output="输出 gcd(a,b) 与 lcm(a,b)，空格分隔。",
        sample_input="12 18",
        sample_output="6 36",
        cases=[("12 18", "6 36"), ("7 13", "1 91")],
    ),
    dict(
        id=1015, title="字符串反转", time_limit=1000, memory_limit=256,
        description="输入一行字符串（含空格），将其整体反转后输出。",
        input="一行字符串，长度不超过 100。",
        output="输出反转后的字符串。",
        sample_input="hello world",
        sample_output="dlrow olleh",
        cases=[("hello world", "dlrow olleh"), ("abc", "cba")],
    ),
    dict(
        id=1016, title="数组排序", time_limit=1000, memory_limit=256,
        description="给定 n 个整数，按非降序排列后输出。",
        input="第一行一个整数 n（1<=n<=1000）；第二行 n 个整数。",
        output="升序排列后的 n 个数，空格分隔。",
        sample_input="5\n3 1 4 1 5",
        sample_output="1 1 3 4 5",
        cases=[("5\n3 1 4 1 5", "1 1 3 4 5"), ("6\n9 8 7 6 5 4", "4 5 6 7 8 9")],
    ),
    dict(
        id=1017, title="二进制转换", time_limit=1000, memory_limit=256,
        description="将一个十进制正整数转换为二进制表示。",
        input="一个正整数 n（1<=n<=10^9）。",
        output="输出 n 的二进制表示。",
        sample_input="10",
        sample_output="1010",
        cases=[("10", "1010"), ("255", "11111111")],
    ),
    dict(
        id=1018, title="阶乘末尾零", time_limit=1000, memory_limit=256,
        description="求 n! 的十进制表示末尾有多少个 0。",
        input="一个整数 n（1<=n<=10^9）。",
        output="输出末尾 0 的个数。",
        sample_input="10",
        sample_output="2",
        cases=[("10", "2"), ("100", "24")],
    ),
    dict(
        id=1019, title="大数加法", time_limit=1000, memory_limit=256,
        description="输入两个非负大整数，输出它们的和（可能超过 64 位整数范围）。",
        input="两行，每行一个非负大整数（长度不超过 1000）。",
        output="输出两数之和。",
        sample_input="99999999999999999999\n1",
        sample_output="100000000000000000000",
        cases=[("99999999999999999999\n1", "100000000000000000000"), ("123456789\n987654321", "1111111110")],
    ),
    dict(
        id=1020, title="最长上升子序列", time_limit=1000, memory_limit=256,
        description="给定一个序列，求最长严格上升子序列的长度。",
        input="第一行一个整数 n（1<=n<=1000）；第二行 n 个整数。",
        output="输出最长上升子序列的长度。",
        sample_input="8\n1 3 5 2 4 6 7 8",
        sample_output="6",
        cases=[("8\n1 3 5 2 4 6 7 8", "6"), ("3\n3 2 1", "1")],
    ),
    dict(
        id=1021, title="01 背包", time_limit=1000, memory_limit=256,
        description="有 n 件物品和一个容量为 W 的背包，每件物品有重量 w 与价值 v，每件最多取一次，求能装下的最大总价值。",
        input="第一行两个整数 n W（1<=n<=100, 1<=W<=1000）；接下来 n 行每行两个整数 w v。",
        output="输出最大总价值。",
        sample_input="3 10\n5 10\n4 40\n6 30",
        sample_output="70",
        cases=[("3 10\n5 10\n4 40\n6 30", "70"), ("4 5\n2 3\n1 2\n3 4\n2 2", "7")],
    ),
]

# ---------------------------------------------------------------- 建库


def add_problem(db, admin_id: int, data: dict) -> Problem:
    p = Problem(
        id=data["id"],
        title=data["title"],
        description=data["description"],
        input=data["input"],
        output=data["output"],
        sample_input=data["sample_input"],
        sample_output=data["sample_output"],
        time_limit=data["time_limit"],
        memory_limit=data["memory_limit"],
        spj=0,
        defunct=False,
        created_by=admin_id,
    )
    db.add(p)
    db.flush()
    # 一个测试点需同时存输入与期望输出（daemon 拉 .in 喂数据、.out 比对），
    # 否则 judge.testdata/1.out → tc is None → 404 → daemon 全部 system_error。
    # （第 7 天联调发现：早期种子只写 .in；评测机自测 3/8 FAIL → 已修补）
    cases = []
    for i, (inp, out) in enumerate(data["cases"], 1):
        cases.append(TestCase(problem_id=p.id, name=f"{i}.in", input_file=inp, order_no=i))
        cases.append(TestCase(problem_id=p.id, name=f"{i}.out", output_file=out, order_no=i))
    db.add_all(cases)
    return p


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

        p = add_problem(db, admin.id, dict(
            id=1001, title="A+B Problem", time_limit=1000, memory_limit=256,
            description="计算两个整数的和",
            input="一行两个整数 a b",
            output="输出 a+b",
            sample_input="1 2",
            sample_output="3",
            cases=[("1 2", "3"), ("10 20", "30")],
        ))
        for data in PROBLEMS:
            add_problem(db, admin.id, data)

        db.add_all(
            [
                Submission(user_id=demo.id, problem_id=p.id, language="cpp", code=A_PLUS_B, status="pending"),
                Submission(user_id=demo.id, problem_id=p.id, language="cpp", code=WRONG, status="pending"),
            ]
        )
        db.commit()
        print(
            "seed 完成：admin/admin123、demo_user/demo123、judger1/judger123、"
            f"题目 1001~1021 共 {1 + len(PROBLEMS)} 道、示例提交 x2"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
