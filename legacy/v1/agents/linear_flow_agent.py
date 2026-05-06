from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.output import NativeOutput

from models.linear_flow_spec import LinearFlowSpec


model = OllamaModel(
    "deepseek-r1:8b",
    provider=OllamaProvider(base_url="http://localhost:11434/v1"),
)


linear_flow_agent = Agent(
    model,
    output_type=NativeOutput(LinearFlowSpec),
    instructions=(
        "请把用户输入的流程描述提取成线性步骤。"
        "按照执行顺序返回 steps 列表。"
        "role 只能使用 start、process、decision、end。"
        "如果用户明确说是起点或开始，使用 start。"
        "如果是普通动作，使用 process。"
        "如果是判断、是否、检查类步骤，使用 decision。"
        "如果用户明确说是终点、结束，使用 end。"
        "只输出符合结构的 JSON，不要输出自然语言解释。"
    ),
)