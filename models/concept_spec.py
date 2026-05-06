from typing import List, Literal

from pydantic import BaseModel, Field


class ConceptItem(BaseModel):
    """
    单个关键概念。
    """

    name: str = Field(..., description="概念名称")
    type: Literal["input", "process", "decision", "module"] = Field(
        ...,
        description="概念类型，只能是 input、process、decision、module"
    )
    description: str = Field(..., description="概念说明")


class ConceptListSpec(BaseModel):
    """
    Research Agent 输出的概念列表。
    """

    concepts: List[ConceptItem] = Field(
        default_factory=list,
        description="从用户输入或工程文档中抽取出的关键概念列表，不能为空"
    )