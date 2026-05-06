from pathlib import Path

from routers.flow_router import route_flow_type
from branch_flow_extractor import extract_branch_flow, BranchFlowExtractor
from agents.research_agent import extract_concepts

from ingest.Input_reader import read_user_input
from processors.role_normalizer import normalize_roles_by_input
from processors.linear_rule_extractor import extract_linear_flow_by_rule

from builders.flowchart_builder import build_flowchart_from_linear
from compilers.flowchart_compiler import compile_flowchart

from utils.mermaid_renderer import render_mermaid_to_image
from utils.loop_repairs import repair_loop_edges

from validators.branch_validator import validate_branch_flow, print_validation_result

def main():
    user_input = read_user_input()

    if not user_input:
        print("输入为空，程序结束。")
        return

    # ============================================================
    # Research Agent：抽取关键概念
    # 作用：
    # 1. 从用户输入 / 文档内容中抽取关键概念
    # 2. 当前阶段只做旁路预览，不影响 router 和流程图生成
    # ============================================================

    try:  #旁路抽取概念
        concept_spec = extract_concepts(user_input) #调用Research Agent

        print("\nResearch Agent 概念抽取结果：")
        for index, concept in enumerate(concept_spec.concepts, start=1):
            print(
                f"{index}. [{concept.type}] {concept.name} - {concept.description}"
            )

    except Exception as e: #如果try中的调用出错，就进入except中不让程序崩溃
        print("\nResearch Agent 概念抽取失败，但不会影响流程图生成。")
        print(f"错误信息：{e}")

    flow_type = route_flow_type(user_input)

    print("\nRouter 判断结果：")
    print(flow_type)

    if flow_type == "branch":
    # 1. 用 LLM 抽取 branch JSON
        branch_diagram = extract_branch_flow(user_input)

    # 2. 修复返回 / 重新输入 / 再次输入这种循环边
        branch_diagram = repair_loop_edges(branch_diagram)

    # 3. 校验 branch 结构
        errors, warnings = validate_branch_flow(branch_diagram, user_input)
        print_validation_result(errors, warnings)

        if errors:
            print("\n检测到严重结构错误，建议先修复后再生成 Mermaid。")
            return

    # 4. 生成 Mermaid
        branch_result = BranchFlowExtractor(branch_diagram)
        mermaid_code = branch_result.to_mermaid()

        print("\nBranch Mermaid 结果：")
        print(mermaid_code)

        # 4. 保存文件
        diagram_dir = Path("diagrams")
        diagram_dir.mkdir(exist_ok=True)

        output_path = diagram_dir / "branch_flowchart.mmd"
        output_path.write_text(mermaid_code, encoding="utf-8")

        print(f"\n已保存到：{output_path}")

        image_path = diagram_dir / "branch_flowchart.svg"
        render_mermaid_to_image(output_path, image_path)

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
        
        image_path = diagram_dir / "branch_flowchart.svg"
        render_mermaid_to_image(output_path, image_path)

    else:
        print("\n暂不支持的流程类型：")
        print(flow_type)


if __name__ == "__main__":
    main()