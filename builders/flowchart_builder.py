from models.linear_flow_spec import LinearFlowSpec
from models.flowchart_spec import FlowNode, FlowEdge, FlowchartSpec


ROLE_TO_KIND = {
    "start": "start_end",
    "process": "process",
    "decision": "decision",
    "end": "start_end",
}


def build_flowchart_from_linear(spec: LinearFlowSpec) -> FlowchartSpec:
    nodes = []
    edges = []

    for i, step in enumerate(spec.steps):
        node_id = chr(ord("A") + i)
        node_kind = ROLE_TO_KIND[step.role]

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