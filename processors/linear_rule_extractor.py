import re

from models.linear_flow_spec import LinearFlowSpec, StepItem


def extract_linear_flow_by_rule(user_input: str) -> LinearFlowSpec:
    """
    不调用大模型，直接用规则从用户输入中提取线性流程步骤。

    支持：
    1. 单行输入
    2. 多行输入
    3. 空行分隔
    4. 中文句号、分号、逗号
    5. 然后、接着、随后、之后、最后等逻辑连接词
    """

    # 1. 统一换行格式为 \n
    normalized_input = (
        user_input
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    # 2. 支持更多分隔符,遇到这些内容切成新步骤
    separators = [
        r"\n+",      # 一个或多个换行
        "然后",
        "接着",
        "随后",
        "之后",
        "最后",
        "最终",
        "并且",
        "，",
        ",",
        "。",
        "；",
        ";",
        r"\.",
        "->",
        "→",
    ]

    pattern = "|".join(separators) #表示这些分隔符之间是 'or'关系

    raw_steps = re.split(pattern, normalized_input)

    # 3. 清洗空步骤
    steps = []
    for step in raw_steps:
        step = step.strip()
        if step:
            steps.append(step)

    if not steps:
        steps = [normalized_input.strip()]

    step_items = []

    for i, step in enumerate(steps):
        if i == 0:
            role = "start"
        elif i == len(steps) - 1:
            role = "end"
        else:
            role = "process"

        step_items.append(
            StepItem(
                text=step,
                role=role,
            )
        )

    return LinearFlowSpec(steps=step_items)