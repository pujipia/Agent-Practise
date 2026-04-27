from models.flowchart_spec import FlowchartSpec


FLOWCHART_SHAPE_MAP = {
    "start_end": "stadium",
    "process": "rect",
    "decision": "diamond",
    "database": "cyl",
    "document": "doc",
    "comment": "brace",
}


def escape_text(text: str) -> str:
    return text.replace('"', '\\"')


def compile_flowchart(spec: FlowchartSpec) -> str:
    lines = [f"flowchart {spec.direction}"]

    for node in spec.nodes:
        shape = FLOWCHART_SHAPE_MAP[node.kind]
        label = escape_text(node.text)
        lines.append(f'{node.id}@{{ shape: {shape} }}["{label}"]')

    for edge in spec.edges:
        if edge.label:
            lines.append(f'{edge.source} -->|{escape_text(edge.label)}| {edge.target}')
        else:
            lines.append(f'{edge.source} --> {edge.target}')

    return "\n".join(lines)