from typing import List

from pydantic import BaseModel, Field


class FlowSegment(BaseModel):
    """
    单个流程片段。

    例如：
    flow_01 - 登录流程
    flow_02 - 文件上传流程
    """

    id: str = Field(
        ...,
        description="流程编号，例如 flow_01、flow_02"
    )

    title: str = Field(
        ...,
        description="流程标题，例如 登录流程、文件上传流程"
    )

    content: str = Field(
        ...,
        description="该流程对应的自然语言文本内容"
    )


class FlowSegmentList(BaseModel):
    """
    多流程切分结果。

    一个输入文档中可能包含多个 FlowSegment。
    """

    flows: List[FlowSegment] = Field(
        default_factory=list,
        description="从用户输入或文档中切分出的多个流程片段"
    )