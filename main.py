from routers.flow_router import route_flow_type
from branch_flow_extractor import extract_branch_flow, BranchFlowExtractor
from pathlib import Path
import re

from models.linear_flow_spec import LinearFlowSpec, StepItem
from processors.role_normalizer import normalize_roles_by_input
from builders.flowchart_builder import build_flowchart_from_linear
from compilers.flowchart_compiler import compile_flowchart

def extract_linear_flow_by_rule(user_input: str) -> LinearFlowSpec:
    """
    不调用大模型，直接用规则从用户输入中提取线性流程步骤。
    目的：先保证 linear flow 一定可以输出 Mermaid。
    """

    # 常见线性连接词
    separators = [
        "然后",
        "接着",
        "随后",
        "之后",
        "再",
        "最后",
        "最终",
        "并且",
        "，",
        ",",
        "->",
        "→",
    ]

    pattern = "|".join(map(re.escape, separators))

    raw_steps = re.split(pattern, user_input)

    steps = []
    for step in raw_steps:
        step = step.strip()
        if step:
            steps.append(step)

    if not steps:
        steps = [user_input.strip()]

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

def main():
    user_input = input("请输入流程描述：")

    flow_type = route_flow_type(user_input)

    print("\nRouter 判断结果：")
    print(flow_type)

    if flow_type == "branch":
        branch_diagram = extract_branch_flow(user_input)

        branch_result = BranchFlowExtractor(branch_diagram)
        mermaid_code = branch_result.to_mermaid()

        print("\nBranch Mermaid 结果：")
        print(mermaid_code)
        diagram_dir = Path("diagrams")
        diagram_dir.mkdir(exist_ok=True)

        output_path = diagram_dir / "branch_flowchart.mmd"
        output_path.write_text(mermaid_code, encoding="utf-8")

        print(f"\n已保存到：{output_path}")
    if flow_type == "branch":
        branch_diagram = extract_branch_flow(user_input)

        branch_result = BranchFlowExtractor(branch_diagram)
        mermaid_code = branch_result.to_mermaid()

        print("\nBranch Mermaid 结果：")
        print(mermaid_code)
        diagram_dir = Path("diagrams")
        diagram_dir.mkdir(exist_ok=True)

        output_path = diagram_dir / "branch_flowchart.mmd"
        output_path.write_text(mermaid_code, encoding="utf-8")

        print(f"\n已保存到：{output_path}")

    elif flow_type == "linear":
        # 1. 不调用 LLM，直接用规则提取 linear steps
        linear_spec = extract_linear_flow_by_rule(user_input)

        print("\nLinear 规则提取结果：")
        print(linear_spec)

        # 2. 修正 start / process / decision / end
        linear_spec = normalize_roles_by_input(linear_spec, user_input)

        # 3. 转成统一 FlowchartSpec
        flowchart_spec = build_flowchart_from_linear(linear_spec)

        # 4. 编译成 Mermaid
        mermaid_code = compile_flowchart(flowchart_spec)

        print("\nLinear Mermaid 结果：")
        print(mermaid_code)

        # 5. 保存文件
        diagram_dir = Path("diagrams")
        diagram_dir.mkdir(exist_ok=True)

        output_path = diagram_dir / "flowchart.mmd"
        output_path.write_text(mermaid_code, encoding="utf-8")

        print(f"\n已保存到：{output_path}")

if __name__ == "__main__":
    main()