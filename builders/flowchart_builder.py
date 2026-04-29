from models.linear_flow_spec import LinearFlowSpec
from models.flowchart_spec import FlowNode, FlowEdge, FlowchartSpec


def infer_kind_from_text(text: str, role: str) -> str:
    clean_text = text.replace(" ", "").replace("\n", "")

    if role in ["start", "end"]:
        return "start_end"

    if role == "decision":
        return "decision"

    input_output_keywords = [
        "输入",
        "输出",
        "读取",
        "写入",
        "上传",
        "下载",
        "导出",
        "保存",
        "展示",
        "显示",
        "提示",
        "返回结果",
    ]

    subroutine_keywords = [
        "调用",
        "运行",
        "执行",
        "启动",
        "使用",
        "请求",
        "访问",
        "Agent",
        "模块",
        "函数",
        "工具",
        "程序",
        "API",
    ]

    if any(keyword in clean_text for keyword in input_output_keywords):
        return "input_output"

    if any(keyword in clean_text for keyword in subroutine_keywords):
        return "subroutine"

    return "process"


def build_flowchart_from_linear(spec: LinearFlowSpec) -> FlowchartSpec:
    nodes = []
    edges = []

    for i, step in enumerate(spec.steps):
        node_id = chr(ord("A") + i)
        node_kind = infer_kind_from_text(step.text, step.role)

        nodes.append(
            FlowNode(
                id=node_id,
                text=step.text,
                kind=node_kind,
            )
        )

    for i in range(len(nodes) - 1):
        edges.append(
            FlowEdge(
                source=nodes[i].id,
                target=nodes[i + 1].id,
                label=None,
            )
        )

    return FlowchartSpec(
        diagram_type="flowchart",
        direction="TD",
        nodes=nodes,
        edges=edges,
    )