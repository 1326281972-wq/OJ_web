"""题目输出模型。"""
from pydantic import BaseModel, ConfigDict


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    time_limit: int
    memory_limit: int
    spj: int


class ProblemDetailOut(ProblemOut):
    description: str
    input: str
    output: str
    sample_input: str
    sample_output: str
    defunct: bool
