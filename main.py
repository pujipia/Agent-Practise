from pathlib import Path
from utils.console_logger import (
    print_flow_start,
    print_flow_summary,
    print_saved_result,
    print_stage,
)

from routers.flow_router import route_flow_type
from branch_flow_extractor import (
    extract_branch_flow,
    extract_branch_flow_with_retry,
    BranchFlowExtractor,
)
from agents.research_agent import extract_concepts
from agents.decomposition_agent import extract_decomposition
from utils.result_saver import save_research_result, save_decomposition_result
from utils.agent_pipeline_repairs import repair_agent_pipeline_edges

from ingest.Input_reader import read_user_input
from processors.role_normalizer import normalize_roles_by_input
from processors.linear_rule_extractor import extract_linear_flow_by_rule
from processors.flow_segmenter import split_flow_segments

from builders.flowchart_builder import build_flowchart_from_linear
from compilers.flowchart_compiler import compile_flowchart

from utils.mermaid_renderer import render_mermaid_to_image
from utils.loop_repairs import repair_loop_edges

from validators.branch_validator import validate_branch_flow, print_validation_result

def process_single_flow(user_input: str, output_prefix: str = "flow_01") -> None: #aviod D-Agent mistakely use a unexisted variable
    """
    处理单个流程片段。

    当前职责：
    1. 调用 Research Agent 抽取 concepts
    2. 调用 Decomposition Agent 拆解 modules / decisions / flows / dependencies
    3. 调用 Router 判断流程类型
    4. 根据 branch / linear 分别生成 Mermaid 和 SVG

    output_prefix 当前先作为预留参数。
    下一步支持多流程时，它会用于生成不同文件名，例如：
    flow_01_branch.svg
    flow_02_branch.svg
    """
    concept_spec = None
    decomposition_spec = None
    print_stage(1, "Research Agent：概念抽取")

    try:
        concept_spec = extract_concepts(user_input)

        print("\nResearch Agent 概念抽取结果：")
        for index, concept in enumerate(concept_spec.concepts, start=1):
            print(
                f"{index}. [{concept.type}] {concept.name} - {concept.description}"
            )
        #save Research Agent 返回的consept_spec in json
        research_output_path = save_research_result(
            concept_spec,
            output_prefix=output_prefix,
        )
        print_saved_result("Research Agent 结果", research_output_path)

    except Exception as e:
        print("\nResearch Agent 概念抽取失败，但不会影响流程图生成。")
        print(f"错误信息：{e}")

    # ============================================================
    # Decomposition Agent：拆解系统结构
    # 作用：
    # 1. 根据 user_input 和 concepts 拆解 modules / decisions / flows / dependencies
    # 2. 当前阶段只做旁路预览，不影响 router 和流程图生成
    # 3. 如果 Research Agent 没有有效 concepts，则跳过 Decomposition
    # ============================================================
    print_stage(2, "Decomposition Agent：系统拆解")

    if concept_spec is not None and concept_spec.concepts:
        try:
            decomposition_spec = extract_decomposition(user_input, concept_spec)

            print("\nDecomposition Agent 系统拆解结果：")

            print("\n[Modules]")
            for index, module in enumerate(decomposition_spec.modules, start=1):
                print(
                    f"{index}. {module.name} - {module.responsibility}"
                )


            print("\n[Decisions]")
            for index, decision in enumerate(decomposition_spec.decisions, start=1):
                options_text = " / ".join(decision.options) if decision.options else "无明确选项"
                print(
                    f"{index}. {decision.question} "
                    f"(options: {options_text}) - {decision.description}"
                )


            print("\n[Flows]")
            for index, flow in enumerate(decomposition_spec.flows, start=1):
                if flow.condition:
                    print(
                        f"{index}. {flow.source} -> {flow.target} "
                        f"[condition: {flow.condition}]"
                    )
                else:
                    print(
                        f"{index}. {flow.source} -> {flow.target}"
                    )


            print("\n[Dependencies]")
            for index, dependency in enumerate(decomposition_spec.dependencies, start=1):
                print(
                    f"{index}. [{dependency.type}] {dependency.name} - {dependency.description}"
                )
            decomposition_output_path = save_decomposition_result(
                decomposition_spec,
                output_prefix=output_prefix,
            )
            print_saved_result("Decomposition Agent 结果", decomposition_output_path)         


        except Exception as e:
            print("\nDecomposition Agent 拆解失败，但不会影响流程图生成。")
            print(f"错误信息：{e}")

    else:
        print("\nDecomposition Agent 已跳过：没有可用 concepts。")
    
    print_stage(3, "Router：流程类型判断")

    flow_type = route_flow_type(
        user_input=user_input,
        concept_spec=concept_spec,
        decomposition_spec=decomposition_spec,
    )

    print("\nRouter 判断结果：")
    print(flow_type)

    print_stage(4, "Flowchart Output：流程图生成")
    if flow_type == "branch":
        branch_diagram = extract_branch_flow(user_input)
        branch_diagram = repair_agent_pipeline_edges(branch_diagram)

        branch_diagram = repair_loop_edges(branch_diagram)

        errors, warnings = validate_branch_flow(branch_diagram, user_input)
        print_validation_result(errors, warnings)

        if errors:
            print("\n第一次 branch 抽取存在结构错误，准备 retry 一次。")

            branch_diagram = extract_branch_flow_with_retry(
                user_input=user_input,
                errors=errors,
                previous_diagram=branch_diagram,
            )
            branch_diagram = repair_agent_pipeline_edges(branch_diagram)
            branch_diagram = repair_loop_edges(branch_diagram)

            errors, warnings = validate_branch_flow(branch_diagram, user_input)
            print_validation_result(errors, warnings)

        if errors:
            print("\nretry 后仍检测到严重结构错误，建议先修复后再生成 Mermaid。")
            return

        branch_result = BranchFlowExtractor(branch_diagram)
        mermaid_code = branch_result.to_mermaid()

        print("\nBranch Mermaid 结果：")
        print(mermaid_code)

        diagram_dir = Path("diagrams")
        diagram_dir.mkdir(exist_ok=True)

        output_path = diagram_dir / f"{output_prefix}_branch.mmd"
        output_path.write_text(mermaid_code, encoding="utf-8")

        print_saved_result("Branch Mermaid 文件", output_path)

        image_path = diagram_dir / f"{output_prefix}_branch.svg"
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

        output_path = diagram_dir / f"{output_prefix}_linear.mmd"
        output_path.write_text(mermaid_code, encoding="utf-8")

        print_saved_result("Linear Mermaid 文件", output_path)

        image_path = diagram_dir / f"{output_prefix}_linear.svg"
        render_mermaid_to_image(output_path, image_path)

    else:
        print("\n暂不支持的流程类型：")
        print(flow_type)

def main():
    """
    主入口函数。

    当前职责：
    1. 读取用户输入或文档内容
    2. 使用 Flow Segmenter 判断输入中有几个流程
    3. 逐个调用 process_single_flow() 处理每个流程
    """

    user_input = read_user_input()

    if not user_input:
        print("输入为空，程序结束。")
        return

    segment_list = split_flow_segments(user_input)

    print_flow_summary(segment_list)

    for index, segment in enumerate(segment_list.flows, start=1):
        print_flow_start(
            flow_id=segment.id,
            flow_title=segment.title,
            current_index=index,
            total_count=len(segment_list.flows),
        )

        process_single_flow(
            user_input=segment.content,
            output_prefix=segment.id,
        )


if __name__ == "__main__":
    main()