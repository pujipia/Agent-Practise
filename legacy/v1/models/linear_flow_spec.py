from typing import Literal
from pydantic import BaseModel, Field
#Literal: 限制函数可选值
#Field: "Description + default value"
#BaseModel: generate structural data and test
class StepItem(BaseModel):
    text: str = Field(description="步骤文字，例如 开始、读取文件、下载结果")
    role: Literal["start", "process", "decision", "end"] = Field(
        description="步骤角色，只能是 start、process、decision、end 之一"
    )
#description的作用： 1.给开发者看便于理解 2. 给Pydantic生成Scheme 3. 给LLM/Agent，理解填什么
class LinearFlowSpec(BaseModel):
    steps: list[StepItem] = Field(
        description="按执行顺序排列的步骤列表"
    )