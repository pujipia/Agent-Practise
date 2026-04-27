from pydantic import BaseModel, Field
from models.common import FlowDirection, FlowNodeKind


class FlowNode(BaseModel):
    id: str = Field(description="唯一节点ID，例如 A、B、C")
    text: str = Field(description="节点显示文字")
    kind: FlowNodeKind = Field(description="节点语义类型")


class FlowEdge(BaseModel):
    source: str = Field(description="起点节点ID")
    target: str = Field(description="终点节点ID")
    label: str | None = Field(default=None, description="边标签，可为空")


class FlowchartSpec(BaseModel):
    diagram_type: str = Field(default="flowchart")
    direction: FlowDirection = Field(default="TD")
    nodes: list[FlowNode]
    edges: list[FlowEdge]