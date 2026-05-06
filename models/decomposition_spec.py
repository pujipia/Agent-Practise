from typing import List, Literal

from pydantic import BaseModel, Field


class ModuleItem(BaseModel):  #有哪些模块
    """
    系统模块或功能单元。
    """

    name: str = Field(..., description="模块名称")
    responsibility: str = Field(..., description="模块职责")


class DecisionItem(BaseModel):  #有哪些判断？
    """
    流程中的判断点。
    """

    question: str = Field(..., description="判断问题")
    options: List[str] = Field(
        default_factory=list,
        description="判断结果选项，例如 支持/不支持、成功/失败、是/否"
    )
    description: str = Field(..., description="判断点说明")


class FlowItem(BaseModel):  #流程之间怎么连接？
    """
    模块、动作或判断之间的流程关系。
    """

    source: str = Field(..., description="流程来源")
    target: str = Field(..., description="流程目标")
    condition: str = Field(
        default="",
        description="触发该流程关系的条件；如果没有条件则为空字符串"
    )


class DependencyItem(BaseModel):  #有哪些依赖项？
    """
    系统依赖项。
    """

    name: str = Field(..., description="依赖名称")
    type: Literal["internal", "external", "unknown"] = Field(
        default="unknown",
        description="依赖类型：internal、external 或 unknown"
    )
    description: str = Field(..., description="依赖说明")


class DecompositionSpec(BaseModel):
    """
    Decomposition Agent 输出的系统拆解结果。
    """

    modules: List[ModuleItem] = Field(
        default_factory=list,
        description="从输入中识别出的模块或功能单元"
    )

    decisions: List[DecisionItem] = Field(
        default_factory=list,
        description="从输入中识别出的判断点"
    )

    flows: List[FlowItem] = Field(
        default_factory=list,
        description="模块、动作、判断之间的流程关系"
    )

    dependencies: List[DependencyItem] = Field(
        default_factory=list,
        description="系统依赖项"
    )