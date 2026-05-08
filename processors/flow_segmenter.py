import re #识别分隔符

from models.flow_segment_spec import FlowSegment, FlowSegmentList

#accept user_input and return a FlowSegmentList
def split_flow_segments(user_input: str) -> FlowSegmentList:
    """
    使用规则从用户输入中切分多个流程。

    当前支持三种多流程写法：
    1. Markdown 标题：# 登录流程 / ## 文件上传流程
    2. 中文流程标题：流程一：登录流程 / 流程二：文件上传流程
    3. 分隔线：---

    如果没有识别出多个流程，则把整段输入作为一个默认流程返回。
    """

    text = user_input.strip()

    if not text:
        return FlowSegmentList(flows=[])

    # 1. 优先按 Markdown 标题切分
    markdown_segments = _split_by_markdown_headings(text)

    if len(markdown_segments) > 1:
        return FlowSegmentList(flows=markdown_segments)

    # 2. 再尝试按“流程一 / 流程二 / 流程1 / 流程2”切分
    named_segments = _split_by_flow_titles(text)

    if len(named_segments) > 1:
        return FlowSegmentList(flows=named_segments)

    # 3. 再尝试按 --- 分隔线切分
    dash_segments = _split_by_dash_separator(text)

    if len(dash_segments) > 1:
        return FlowSegmentList(flows=dash_segments)

    # 4. 如果没有识别出多个流程，就作为单流程处理
    return FlowSegmentList(
        flows=[
            FlowSegment(
                id="flow_01",
                title="默认流程",
                content=text,
            )
        ]
    )


def _split_by_markdown_headings(text: str) -> list[FlowSegment]:
    """
    按 Markdown 标题切分流程。

    支持：
    # 登录流程
    ## 文件上传流程
    ### 审批流程
    """

    pattern = r"(?m)^(#{1,3})\s+(.+)$"
    matches = list(re.finditer(pattern, text))

    # 只有 0 个或 1 个标题时，不认为是多流程
    if len(matches) <= 1:
        return []

    segments = []

    for index, match in enumerate(matches):
        title = match.group(2).strip()

        # 当前标题后的内容开始位置
        start = match.end()

        # 下一个标题前的位置；如果没有下一个标题，就到文本末尾
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        content = text[start:end].strip()

        if not content:
            continue

        segments.append(
            FlowSegment(
                id=f"flow_{len(segments) + 1:02d}",
                title=title,
                content=content,
            )
        )

    return segments


def _split_by_flow_titles(text: str) -> list[FlowSegment]:
    """
    按中文流程标题切分。

    支持：
    流程一：登录流程
    流程二：文件上传流程
    流程1：登录流程
    流程2：文件上传流程
    """

    pattern = r"(?m)^(流程[一二三四五六七八九十\d]+[:：]\s*(.*))$"
    matches = list(re.finditer(pattern, text))

    if len(matches) <= 1:
        return []

    segments = []

    for index, match in enumerate(matches):
        # match.group(2) 是冒号后面的标题
        # 如果标题为空，就用整行作为标题
        title = match.group(2).strip() or match.group(1).strip()

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        content = text[start:end].strip()

        if not content:
            continue

        segments.append(
            FlowSegment(
                id=f"flow_{len(segments) + 1:02d}",
                title=title,
                content=content,
            )
        )

    return segments


def _split_by_dash_separator(text: str) -> list[FlowSegment]:
    """
    按 --- 分隔线切分流程。

    示例：
    登录流程
    用户输入账号。

    ---

    文件上传流程
    用户上传文件。

    处理逻辑：
    1. 用 --- 把文本切成多个部分
    2. 每一部分的第一行作为流程标题
    3. 第一行之后的内容作为流程正文 content
    """

    parts = re.split(r"(?m)^\s*---+\s*$", text)

    cleaned_parts = [
        part.strip()
        for part in parts
        if part.strip()
    ]

    if len(cleaned_parts) <= 1:
        return []

    segments = []

    for index, part in enumerate(cleaned_parts, start=1):
        lines = [
            line.strip()
            for line in part.splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        first_line = lines[0]

        if len(first_line) <= 30:
            title = first_line
            content_lines = lines[1:]
        else:
            title = f"流程 {index}"
            content_lines = lines

        content = "\n".join(content_lines).strip()

        if not content:
            content = first_line

        segments.append(
            FlowSegment(
                id=f"flow_{index:02d}",
                title=title,
                content=content,
            )
        )

    return segments