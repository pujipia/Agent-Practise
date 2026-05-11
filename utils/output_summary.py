from pathlib import Path


def _find_existing_file(candidates):
    """
    从候选路径中找到第一个真实存在的文件。
    """

    for path in candidates:
        if path.exists():
            return str(path)

    return "未生成/未找到"


def _infer_flow_type_from_outputs(output_prefix: str) -> str:
    """
    根据 diagrams 文件夹里的输出文件推断流程类型。
    """

    diagram_dir = Path("diagrams")

    branch_files = [
        diagram_dir / f"{output_prefix}_branch.mmd",
        diagram_dir / f"{output_prefix}_branch.svg",
    ]

    linear_files = [
        diagram_dir / f"{output_prefix}_linear.mmd",
        diagram_dir / f"{output_prefix}_linear.svg",
    ]

    if any(path.exists() for path in branch_files):
        return "branch"

    if any(path.exists() for path in linear_files):
        return "linear"

    return "unknown"


def build_output_summary(output_prefix: str, flow_title: str = "") -> dict:
    """
    根据 output_prefix 自动生成单个流程片段的输出摘要。
    """

    diagram_dir = Path("diagrams")
    artifact_dir = Path("artifacts")

    flow_type = _infer_flow_type_from_outputs(output_prefix)

    mermaid_file = _find_existing_file(
        [
            diagram_dir / f"{output_prefix}_{flow_type}.mmd",
            diagram_dir / f"{output_prefix}_branch.mmd",
            diagram_dir / f"{output_prefix}_linear.mmd",
        ]
    )

    svg_file = _find_existing_file(
        [
            diagram_dir / f"{output_prefix}_{flow_type}.svg",
            diagram_dir / f"{output_prefix}_branch.svg",
            diagram_dir / f"{output_prefix}_linear.svg",
        ]
    )

    research_json = _find_existing_file(
        [
            artifact_dir / f"{output_prefix}_research_concepts.json",
        ]
    )

    decomposition_json = _find_existing_file(
        [
            artifact_dir / f"{output_prefix}_decomposition.json",
        ]
    )

    return {
        "flow_id": output_prefix,
        "flow_title": flow_title or "默认流程",
        "flow_type": flow_type,
        "mermaid_file": mermaid_file,
        "svg_file": svg_file,
        "research_json": research_json,
        "decomposition_json": decomposition_json,
        "status": "成功",
    }


def print_final_output_summary(summaries: list) -> None:
    """
    打印最终输出摘要。
    """

    if not summaries:
        return

    print("\n" + "=" * 70)
    print("处理完成：")
    print("=" * 70)

    print(f"流程数量：{len(summaries)}")

    for index, summary in enumerate(summaries, start=1):
        print("\n" + "-" * 70)
        print(f"[{index}/{len(summaries)}] {summary['flow_id']} - {summary['flow_title']}")
        print("-" * 70)
        print(f"流程类型：{summary['flow_type']}")
        print(f"Mermaid 文件：{summary['mermaid_file']}")
        print(f"SVG 图片：{summary['svg_file']}")
        print(f"Research JSON：{summary['research_json']}")
        print(f"Decomposition JSON：{summary['decomposition_json']}")
        print(f"状态：{summary['status']}")

    print("\n" + "=" * 70)