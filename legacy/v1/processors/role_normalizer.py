from models.linear_flow_spec import LinearFlowSpec
from processors.text_cleaner import clean_step_text

# Recognize some connection words more accurately
def normalize_roles_by_input(linear_spec: LinearFlowSpec, user_input: str) -> LinearFlowSpec:
    if not linear_spec.steps:
        return linear_spec

    start_keywords = [
        "起点是",
        "起点为",
        "开始是",
        "从",
        "首先",
        "第一步",
        "先",
    ]

    end_keywords = [
        "终点是",
        "终点为",
        "结束是",
        "最后是",
        "最后",
        "最终",
        "完成",
        "就可以了",
        "即可",
    ]

    decision_keywords = [
        "是否",
        "判断",
        "检查",
        "校验",
        "验证",
        "如果",
        "能否",
        "有没有",
        "是否正确",
        "是否通过",
    ]

    # 1. 清理每个步骤的 text
    for step in linear_spec.steps:
        step.text = clean_step_text(step.text)

    # 2. 修正第一个节点
    if any(keyword in user_input for keyword in start_keywords):
        linear_spec.steps[0].role = "start"

    # 3. 修正最后一个节点
    if any(keyword in user_input for keyword in end_keywords):
        linear_spec.steps[-1].role = "end"

    # 4. 修正判断类节点
    for step in linear_spec.steps:
        if any(keyword in step.text for keyword in decision_keywords):
            step.role = "decision"

    # 5. 如果没有 start，默认第一个是 start
    if all(step.role != "start" for step in linear_spec.steps):
        linear_spec.steps[0].role = "start"

    # 6. 如果没有 end，默认最后一个是 end
    if all(step.role != "end" for step in linear_spec.steps):
        linear_spec.steps[-1].role = "end"

    return linear_spec