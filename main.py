from routers.flow_router import route_flow_type
from branch_flow_extractor import BranchFlowExtractor


def main():
    user_input = "上传文件后检查格式是否正确，如果正确就生成报告，如果不正确就提示错误"

    flow_type = route_flow_type(user_input)

    print("\nRouter 判断结果：")
    print(flow_type)

    if flow_type == "branch":
        branch_diagram = {
            "diagram_type": "flowchart",
            "direction": "TD",
            "nodes": [
                {"id": "A", "text": "上传文件", "kind": "process"},
                {"id": "B", "text": "检查格式是否正确", "kind": "decision"},
                {"id": "C", "text": "生成报告", "kind": "process"},
                {"id": "D", "text": "提示错误", "kind": "process"},
            ],
            "edges": [
                {"source": "A", "target": "B", "label": None},
                {"source": "B", "target": "C", "label": "正确"},
                {"source": "B", "target": "D", "label": "不正确"},
            ],
        }

        branch_result = BranchFlowExtractor(branch_diagram)

        mermaid_code = branch_result.to_mermaid()

        print("\nBranch Mermaid 结果：")
        print(mermaid_code) 

    else:
        print("\n这是 linear flow，后续交给普通线性流程处理。")


if __name__ == "__main__":
    main()