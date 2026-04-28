from typing import Literal
from pydantic import BaseModel, Field

#additional parts in multi flowchart
class BranchNode(BaseModel):
    id: str = Field(description="节点ID，例如 A、B、C")
    text: str = Field(description="节点显示文字")
    kind: Literal["start_end", "process", "decision"] = Field(
        description="节点类型，只能是 start_end、process、decision"
    )


class BranchEdge(BaseModel):
    source: str = Field(description="起点节点ID")
    target: str = Field(description="终点节点ID")
    label: str | None = Field(
        default=None,
        description="边标签，例如 正确、不正确、yes、no，可为空"
    )


class BranchFlowSpec(BaseModel):
    diagram_type: Literal["flowchart"] = "flowchart"
    direction: Literal["TD", "LR", "RL", "BT"] = "TD"
    nodes: list[BranchNode]
    edges: list[BranchEdge]