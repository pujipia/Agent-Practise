#真正跑 Agent pipeline，并打印 PASS / FAIL
import time
from utils.regression_report import save_regression_report
from agents.research_agent import extract_concepts
from agents.decomposition_agent import extract_decomposition
from routers.flow_router import route_flow_type

from branch_flow_extractor import extract_branch_flow
from processors.linear_rule_extractor import extract_linear_flow_by_rule
from processors.role_normalizer import normalize_roles_by_input
from builders.flowchart_builder import build_flowchart_from_linear

from utils.loop_repairs import repair_loop_edges
from utils.agent_pipeline_repairs import repair_agent_pipeline_edges

from validators.branch_validator import validate_branch_flow

from tests.builtin_cases import BUILTIN_TEST_CASES
from tests.assertions import run_case_assertions


def _build_diagram_for_case(case):
    """
    根据测试用例输入，运行当前 Agent pipeline，并返回：

    - flow_type: Router 判断结果
    - diagram: 生成后的结构化流程图对象
    - errors: branch validator 的严重错误
    - warnings: branch validator 的警告
    """

    # 1. Research Agent：抽取概念
    concept_spec = extract_concepts(case.input_text)

    # 2. Decomposition Agent：拆解结构
    decomposition_spec = extract_decomposition(case.input_text, concept_spec)

    # 3. Router：判断 linear / branch
    flow_type = route_flow_type(
        user_input=case.input_text,
        concept_spec=concept_spec,
        decomposition_spec=decomposition_spec,
    )

    # 4. 根据 flow_type 调用不同流程图生成逻辑
    if flow_type == "linear":
        linear_spec = extract_linear_flow_by_rule(case.input_text)
        linear_spec = normalize_roles_by_input(linear_spec, case.input_text)
        diagram = build_flowchart_from_linear(linear_spec)

        return flow_type, diagram, [], []

    if flow_type == "branch":
        diagram = extract_branch_flow(case.input_text)

        # 先做已有 loop repair
        diagram = repair_loop_edges(diagram)

        # 再做 Agent pipeline 专项 repair
        diagram = repair_agent_pipeline_edges(diagram)

        errors, warnings = validate_branch_flow(diagram, case.input_text)

        return flow_type, diagram, errors, warnings

    # 当前项目暂时只支持 linear / branch
    return flow_type, None, [f"Unsupported flow_type: {flow_type}"], []


def run_builtin_regression_tests() -> bool:
    """
    运行全部内置回归测试。

    返回：
    - True: 全部通过
    - False: 至少一个失败
    """

    total = len(BUILTIN_TEST_CASES)
    passed = 0
    failed = 0
    results = []

    print("\n" + "=" * 70)
    print("开始运行内置回归测试")
    print("=" * 70)

    for index, case in enumerate(BUILTIN_TEST_CASES, start=1):
        print(f"\n[{index}/{total}] {case.name}")
        print("-" * 70)

        start_time = time.time()
        case_passed = False
        warning_count = 0
        message = ""

        try:
            flow_type, diagram, errors, warnings = _build_diagram_for_case(case)

            # 1. 检查 Router 判断结果
            if flow_type != case.expected_flow_type:
                failed += 1
                message = (
                    f"Router 判断结果错误。"
                    f"预期: {case.expected_flow_type}; 实际: {flow_type}"
                )
                print("FAIL: Router 判断结果错误")
                print(f"  预期: {case.expected_flow_type}")
                print(f"  实际: {flow_type}")

            # 2. Branch validator 严重错误直接判 FAIL
            elif errors:
                failed += 1
                message = "Branch validator 检测到严重结构错误: " + "; ".join(errors)
                print("FAIL: Branch validator 检测到严重结构错误")
                for error in errors:
                    print(f"  - {error}")

            else:
                # 3. 检查关键节点、边标签、关键边
                ok, assertion_errors = run_case_assertions(diagram, case)

                if not ok:
                    failed += 1
                    message = "断言检查失败: " + "; ".join(assertion_errors)
                    print("FAIL: 断言检查失败")
                    for error in assertion_errors:
                        print(f"  - {error}")

                else:
                    # 4. warning 不直接判失败，只提示
                    case_passed = True
                    passed += 1

                    if warnings:
                        warning_count = len(warnings)
                        message = "PASS_WITH_WARNING: " + "; ".join(warnings)
                        print("PASS_WITH_WARNING")
                        for warning in warnings:
                            print(f"  - warning: {warning}")
                    else:
                        message = "PASS"
                        print("PASS")

        except Exception as e:
            failed += 1
            message = f"{type(e).__name__}: {e}"
            print("ERROR: 测试运行过程中发生异常")
            print(f"  {type(e).__name__}: {e}")

        duration = time.time() - start_time

        results.append(
            {
                "name": case.name,
                "passed": case_passed,
                "warnings": warning_count,
                "duration": duration,
                "message": message,
            }
        )

    print("\n" + "=" * 70)
    print("内置回归测试完成")
    print(f"通过: {passed}/{total}")
    print(f"失败: {failed}/{total}")
    print("=" * 70)

    report_path = save_regression_report(results)

    print("\n" + "=" * 60)
    print("Regression Summary")
    print("=" * 60)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {failed}/{total}")
    print(f"Report saved to: {report_path}")

    return failed == 0

if __name__ == "__main__":
    run_builtin_regression_tests()

