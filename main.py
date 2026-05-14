from pathlib import Path
from utils.console_logger import (
    print_flow_start,
    print_flow_summary,
    print_saved_result,
    print_stage,
)
from tests.regression_runner import run_builtin_regression_tests

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
from utils.output_summary import build_output_summary, print_final_output_summary
from utils.logger import set_debug_mode, log_debug

from ingest.Input_reader import read_user_input
from processors.role_normalizer import normalize_roles_by_input
from processors.linear_rule_extractor import extract_linear_flow_by_rule
from processors.flow_segmenter import split_flow_segments
from processors.input_scope_guard import check_input_scope

from builders.flowchart_builder import build_flowchart_from_linear
from compilers.flowchart_compiler import compile_flowchart

from utils.mermaid_renderer import render_mermaid_to_image
from utils.loop_repairs import repair_loop_edges

from validators.branch_validator import validate_branch_flow, print_validation_result

def process_single_flow(user_input: str, output_prefix: str = "flow_01") -> dict: #aviod D-Agent mistakely use a unexisted variable
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
    flow_type = "unknown"
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
        try:
            branch_diagram = extract_branch_flow(user_input)

        except Exception as e:
            print("\nBranch Flow 抽取失败。")
            print(f"错误类型：{type(e).__name__}")
            print(f"错误信息：{e}")
            print("本次流程生成已取消，返回主菜单。")
            return {
                "success": False,
                "flow_type": flow_type,
                "message": f"Branch Flow 抽取失败: {type(e).__name__}: {e}",
            }

        branch_diagram = repair_agent_pipeline_edges(branch_diagram)

        branch_diagram = repair_loop_edges(branch_diagram)

        errors, warnings = validate_branch_flow(branch_diagram, user_input)
        print_validation_result(errors, warnings)
        

        if errors:
            print("\n第一次 branch 抽取存在结构错误，准备 retry 一次。")

            try:
                branch_diagram = extract_branch_flow_with_retry(
                    user_input=user_input,
                    errors=errors,
                    previous_diagram=branch_diagram,
                    decomposition_spec=decomposition_spec,
                )

                branch_diagram = repair_agent_pipeline_edges(branch_diagram)
                branch_diagram = repair_loop_edges(branch_diagram)

                errors, warnings = validate_branch_flow(branch_diagram, user_input)
                print_validation_result(errors, warnings)

            except Exception as retry_error:
                print("\nBranch Flow retry 失败。")
                print(f"错误类型：{type(retry_error).__name__}")
                print(f"错误信息：{retry_error}")
                print("本次流程生成已取消，返回主菜单。")

                return {
                    "success": False,
                    "flow_type": flow_type,
                    "message": (
                        f"Branch Flow retry 异常: "
                        f"{type(retry_error).__name__}: {retry_error}"
                    ),
                }

        if errors:
            print("\nretry 后仍检测到严重结构错误，建议先修复后再生成 Mermaid。")

            error_text = "；".join(errors)

            return {
                "success": False,
                "flow_type": flow_type,
                "message": f"Branch Flow retry 后仍存在结构错误: {error_text}",
            }

        branch_result = BranchFlowExtractor(branch_diagram)
        mermaid_code = branch_result.to_mermaid()

        log_debug("\nBranch Mermaid 结果：")
        log_debug(mermaid_code)

        diagram_dir = Path("diagrams")
        diagram_dir.mkdir(exist_ok=True)

        output_path = diagram_dir / f"{output_prefix}_branch.mmd"
        output_path.write_text(mermaid_code, encoding="utf-8")

        print_saved_result("Branch Mermaid 文件", output_path)

        image_path = diagram_dir / f"{output_prefix}_branch.svg"
        render_mermaid_to_image(output_path, image_path)
        return {
            "success": True,
            "flow_type": flow_type,
            "message": "流程图生成成功。",
        }

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

        log_debug("\nLinear Mermaid 结果：")
        log_debug(mermaid_code)

        # 5. 保存文件
        diagram_dir = Path("diagrams")
        diagram_dir.mkdir(exist_ok=True)

        output_path = diagram_dir / f"{output_prefix}_linear.mmd"
        output_path.write_text(mermaid_code, encoding="utf-8")

        print_saved_result("Linear Mermaid 文件", output_path)

        image_path = diagram_dir / f"{output_prefix}_linear.svg"
        render_mermaid_to_image(output_path, image_path)
        return {
            "success": True,
            "flow_type": flow_type,
            "message": "流程图生成成功。",
        }

    else:
        print("\n暂不支持的流程类型：")
        print(flow_type)

        return {
        "success": False,
        "flow_type": flow_type,
        "message": f"暂不支持的流程类型: {flow_type}",
        }

def select_logging_mode() -> None:
    """
    让用户选择 normal / debug 日志模式。
    """

    print("\n请选择日志模式：")
    print("[1] 普通模式：只显示关键步骤和最终结果")
    print("[2] 调试模式：显示完整 JSON、Mermaid 和中间结果")

    while True:
        try:
            choice = input("请输入选项 1 或 2：").strip()
        except KeyboardInterrupt:
            raise

        if choice == "1":
            set_debug_mode(False)
            print("\n当前日志模式：普通模式")
            return

        if choice == "2":
            set_debug_mode(True)
            print("\n当前日志模式：调试模式")
            return

        print("无效选项，请输入 1 或 2。")

def confirm_input_scope(user_input: str) -> bool:
    """
    Check whether the input is suitable for flowchart generation.

    Returns:
        True:
            Continue to generate flowchart.

        False:
            Cancel current generation and return to main menu.
    """

    scope_result = check_input_scope(user_input)

    # If the input looks suitable, continue directly.
    if scope_result.is_supported:
        return True

    # Otherwise, show a warning and ask the user whether to continue.
    print("\n输入范围提醒")
    print("-" * 60)
    print(scope_result.reason)
    print("本工具主要适合将包含步骤、动作、判断、分支或返回关系的内容转换为流程图。")

    while True:
        answer = input("是否仍然继续生成流程图？[y/n]: ").strip().lower()

        if answer in ("y", "yes"):
            print("已选择继续生成流程图。")
            return True

        if answer in ("n", "no", "0"):
            print("已取消生成，返回主菜单。")
            return False

        print("请输入 y 或 n。")

def cleanup_previous_outputs(output_prefix: str) -> None:
    """
    Delete old generated diagram files for the same output prefix.

    This prevents final summary from showing stale Mermaid/SVG files
    after the current generation fails.
    """

    candidates = [
        Path("diagrams") / f"{output_prefix}_branch.mmd",
        Path("diagrams") / f"{output_prefix}_branch.svg",
        Path("diagrams") / f"{output_prefix}_linear.mmd",
        Path("diagrams") / f"{output_prefix}_linear.svg",
    ]

    for path in candidates:
        if path.exists():
            path.unlink()

def main() -> bool:
    """
    主入口函数。

    当前职责：
    1. 读取用户输入或文档内容
    2. 使用 Flow Segmenter 判断输入中有几个流程
    3. 逐个调用 process_single_flow() 处理每个流程
    """

    user_input = read_user_input()

    if user_input is None:
        return True
    
    if user_input == "__CHANGE_LOGGING_MODE__":
        select_logging_mode()
        return False


    user_input = user_input.strip()

    if not user_input:
        print("输入为空，返回主菜单。")
        return False

    segment_result = split_flow_segments(user_input.strip())
    segments = segment_result.flows

    print(f"\n检测到 {len(segments)} 个流程：")
    for segment in segments:
        print(f"- {segment.id}：{segment.title}")

    summaries = []

    for index, segment in enumerate(segments, start=1):
        print("\n" + "=" * 70)
        print(f"[{index}/{len(segments)}] 开始处理：{segment.id} - {segment.title}")
        print("=" * 70)

        if not confirm_input_scope(segment.content):
            return False

        cleanup_previous_outputs(segment.id)

        process_result = process_single_flow(
            user_input=segment.content,
            output_prefix=segment.id,
        )
        
        if process_result is None:
            process_result = {
                "success": False,
                "flow_type": "unknown",
                "message": "流程处理函数没有返回结果。",
            }
        status_text = "成功" if process_result.get("success") else "失败"

        summaries.append(
            build_output_summary(
                output_prefix=segment.id,
                flow_title=getattr(segment, "title", "默认流程"),
                flow_type=process_result.get("flow_type", "unknown"),
                status=status_text,
                message=process_result.get("message", ""),
            )
        )

    print_final_output_summary(summaries)
    return False

def confirm_exit_after_interrupt() -> bool:
    """
    当用户按 Ctrl + C 时，询问是否确认退出。

    返回：
    - True: 确认退出
    - False: 取消退出，返回主菜单
    """

    print("\n检测到 Ctrl + C 中断。")

    while True:
        try:
            answer = input("是否确认退出程序？[y/n]: ").strip().lower()

        except KeyboardInterrupt:
            # 用户在确认阶段再次 Ctrl+C，直接退出
            print("\n再次收到中断，已安全退出。")
            return True

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        print("请输入 y 或 n。")


if __name__ == "__main__":
    select_logging_mode()

    while True:
        try:
            should_exit = main()

            if should_exit:
                print("\n已退出 File Agent Flowchart Generator。")
                break

            print("\n已返回主菜单。")
            continue

        except KeyboardInterrupt:
            should_exit = confirm_exit_after_interrupt()

            if should_exit:
                print("\n已退出 File Agent Flowchart Generator。")
                break

            print("\n已取消退出，返回主菜单。")
            continue