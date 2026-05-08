from pathlib import Path


def print_banner(message: str, width: int = 70, char: str = "=") -> None:
    """
    打印醒目的分隔标题。
    """

    print("\n" + char * width)
    print(message)
    print(char * width)


def print_stage(index: int, title: str) -> None:
    """
    打印当前处理阶段标题。
    """

    print("\n" + "-" * 70)
    print(f"[{index}] {title}")
    print("-" * 70)


def print_flow_start(
    flow_id: str,
    flow_title: str,
    current_index: int,
    total_count: int,
) -> None:
    """
    打印当前流程开始处理的标题。
    """

    print_banner(
        f"[{current_index}/{total_count}] 开始处理：{flow_id} - {flow_title}"
    )


def print_saved_result(label: str, path: str | Path) -> None:
    """
    打印结果保存路径。
    """

    print(f"\n{label} 已保存到：{path}")


def print_flow_summary(flow_segments) -> None:
    """
    打印 Flow Segmenter 检测到的流程列表。
    """

    print(f"\n检测到 {len(flow_segments.flows)} 个流程：")

    for segment in flow_segments.flows:
        print(f"- {segment.id}：{segment.title}")