# 数据模型与字段约定（主路径优先）

> 配套文档：`OJ在线测评系统建设方案.md`、`模块图与选型比对.md`、`实验报告.md`（主路径定义）
> 原则：**先覆盖主路径**（第 5 天必须演示的业务流程：登录 → 看题 → WASM 运行 → 提交 → 轮询 → 评测 → 终态），再补次要内容；**对照需求删除用不到的表与字段**；库表、接口、前端三处字段名必须一致。

---

## 1. 主路径步骤 → 支撑实体（表）

| 主路径步骤 | 支撑表 |
|------------|--------|
| 选手注册/登录 | `users` |
| 打开题库、查看题目详情（1001 A+B） | `problems` |
| 编辑器 WASM 编译运行 | 纯前端，**不落表** |
| 提交代码 | `submissions` |
| 轮询评测状态 | `submissions` |
| 评测机登录、拉任务、取数据、回传 | `judge_machines`、`submissions`、`test_cases`、`problems`(限制)、`compile_infos`/`run_infos` |

主路径共支撑 **7 张表**：users / problems / test_cases / submissions / compile_infos / run_infos / judge_machines。

## 2. 主路径实体与字段（7 表）

### users（R1）

| 字段 | 类型 | 约束 | 说明 | 接口字段 | 前端展示名 |
|------|------|------|------|----------|------------|
| id | INTEGER | PK | 用户 ID | id | 用户 ID |
| user_id | VARCHAR(64) | UNIQUE NOT NULL | 登录账号 | user_id | 账号 |
| password_hash | VARCHAR(128) | NOT NULL | bcrypt，**永不返回** | — | — |
| nickname | VARCHAR(64) | NOT NULL | 昵称 | nickname | 昵称 |
| email | VARCHAR(128) | UNIQUE，可空 | 邮箱（次要） | email | 邮箱 |
| role | VARCHAR(16) | DEFAULT 'contestant' | admin/contestant/judger | role | 角色 |
| status | VARCHAR(16) | DEFAULT 'active' | active/disabled | status | 状态 |
| created_at | DATETIME | NOT NULL | 注册时间 | created_at | 注册时间 |

### problems（R2）

| 字段 | 类型 | 约束 | 说明 | 接口字段 | 前端展示名 |
|------|------|------|------|----------|------------|
| id | INTEGER | PK | 题号（对外 1001） | id | 题号 |
| title | VARCHAR(128) | NOT NULL | 标题 | title | 标题 |
| description | TEXT | NOT NULL | Markdown 描述 | description | 题目描述 |
| input | TEXT | NOT NULL | 输入说明 | input | 输入 |
| output | TEXT | NOT NULL | 输出说明 | output | 输出 |
| sample_input | TEXT | NOT NULL | 样例输入（WASM 本地自测用） | sample_input | 样例输入 |
| sample_output | TEXT | NOT NULL | 样例输出 | sample_output | 样例输出 |
| time_limit | INTEGER | DEFAULT 1000 | 时限(ms) | time_limit | 时限 |
| memory_limit | INTEGER | DEFAULT 256 | 内存(MB) | memory_limit | 内存限制 |
| spj | INTEGER | DEFAULT 0 | 0 普通 / 2 交互题 | spj | 题目类型 |
| defunct | BOOLEAN | DEFAULT 1 | 是否隐藏 | defunct | 发布状态 |
| created_by | INTEGER | FK users.id | 出题人 | — | — |
| created_at / updated_at | DATETIME | NOT NULL | 时间戳 | created_at | 创建时间 |

### test_cases（R3，评测机取数据）

| 字段 | 类型 | 约束 | 说明 | 接口字段 | 前端展示名 |
|------|------|------|------|----------|------------|
| id | INTEGER | PK | — | id | 数据 ID |
| problem_id | INTEGER | FK NOT NULL | 所属题目 | problem_id | 题号 |
| name | VARCHAR(128) | NOT NULL | 文件名（如 1.in） | name | 文件名 |
| input_file | TEXT | | 输入内容/路径 | —（走 testdata 下载接口） | — |
| output_file | TEXT | | 标准输出内容/路径 | — | — |
| order_no | INTEGER | DEFAULT 0 | 评测顺序 | order_no | 顺序 |

### submissions（R2/R3 核心，兼评测任务队列）

| 字段 | 类型 | 约束 | 说明 | 接口字段 | 前端展示名 |
|------|------|------|------|----------|------------|
| id | INTEGER | PK | 提交 ID | id | 提交 ID |
| user_id | INTEGER | FK NOT NULL | 提交者 | user_id | 提交者 |
| problem_id | INTEGER | FK NOT NULL | 题目 | problem_id | 题号 |
| language | VARCHAR(32) | DEFAULT 'cpp' | 语言 | language | 语言 |
| code | TEXT | NOT NULL | 源码（列表不返回，详情才返回） | code | 源码 |
| status | VARCHAR(32) | DEFAULT 'pending' | 状态机：pending/compiling/running/accepted/wrong_answer/compile_error/time_limit_exceeded/runtime_error 等 | status | 状态 |
| time_used | INTEGER | | 耗时(ms) | time_used | 耗时 |
| memory_used | INTEGER | | 内存(KB) | memory_used | 内存 |
| judger | VARCHAR(64) | | 评测机账号 | judger | 评测机 |
| judge_time | DATETIME | | 检出/评测时间（卡死回收用） | judge_time | 评测时间 |
| submitted_at | DATETIME | NOT NULL | 提交时间 | submitted_at | 提交时间 |

### compile_infos / run_infos（失败例：CE / RE）

| 字段 | 类型 | 约束 | 说明 | 接口字段 | 前端展示名 |
|------|------|------|------|----------|------------|
| id | INTEGER | PK | — | — | — |
| submission_id | INTEGER | FK UNIQUE NOT NULL | 唯一关联提交 | submission_id | 提交 ID |
| info | TEXT | NOT NULL | 编译/运行错误全文 | info | 错误信息 |
| created_at | DATETIME | | — | — | — |

### judge_machines（R3）

| 字段 | 类型 | 约束 | 说明 | 接口字段 | 前端展示名 |
|------|------|------|------|----------|------------|
| id | INTEGER | PK | — | — | — |
| user_id | INTEGER | FK UNIQUE NOT NULL | 关联 judger 账号 | — | — |
| name | VARCHAR(64) | | 评测机名 | name | 名称 |
| mod / total | INTEGER | | 分片参数（协议预留） | mod/total | — |
| last_heartbeat | DATETIME | | 在线判定 | last_heartbeat | 最后心跳 |
| status | VARCHAR(16) | DEFAULT 'offline' | online/offline | status | 状态 |

## 3. 次要内容（本期保留，非主路径必需）

- `interactors` 表（R5 通信题：交互器源码/版本管理）——**第 7 天启用**，主路径不涉及；
- `problems.spj=2`（交互题标记）、`problems.hint`（题目提示，可选展示）。

## 4. 对照需求删除的表与字段

| 删除项 | 原方案字段 | 删除原因 |
|--------|-----------|----------|
| submissions.is_wasm | 区分 WASM 本地提交 | 主路径不区分提交来源，删除 |
| submissions.pass_rate | OI 分制预留 | 本期无 OI 分制，删除 |
| problems.accepted / submit | 提交/通过统计 | 用 count 查询实时计算，不落冗余字段 |
| problems.source | 题目来源 | 本期无内容来源，删除 |
| test_cases.score | OI 分值 | 本期无 OI 分制，删除 |
| 未选模块相关表 | 打印队列、设备管理 | 第 1 天已排除，不建表 |

> 规则：主路径需求无人承担、或字段与需求无关 → 一律删除/移出，避免表结构与需求脱节。

## 5. 三处字段名一致性（库表 / 接口 / 前端）

**约定：全链路统一 snake_case**。数据库字段名 = 接口 JSON 字段名 = 前端 API 层变量名；前端仅展示层映射中文标签。禁止前端自行转 camelCase，避免三处对不上。

字段对照表（库表 → 接口 JSON → 前端展示）已并入第 2 节各表"接口字段 / 前端展示名"两列；特殊项说明：

| 数据库字段 | 接口 JSON | 前端 | 说明 |
|-----------|-----------|------|------|
| users.password_hash | 不返回 | 不显示 | 仅服务端校验 |
| submissions.code | 仅 `GET /submissions/{id}` 返回 | 详情页显示 | 列表接口返回 code=null |
| test_cases.input_file/output_file | 不返回正文，走 `GET /judge/testdata/{pid}/{file}` | 前端不展示 | 评测机专用 |
