from typing import Any, List


def _normalize_text(text: Any) -> str:
    """
    文本归一化，用于比较 D Agent decision 和 Branch node text。

    目标：
    支付是否成功
    系统判断支付是否成功
    支付是否成功？
    都应该匹配。
    """

    normalized = (
        str(text or "")
        .lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("？", "")
        .replace("?", "")
        .replace("：", "")
        .replace(":", "")
        .replace("。", "")
        .replace(".", "")
    )

    remove_words = [
        "系统",
        "进行",
        "执行",
        "判断",
        "检查",
        "验证",
        "校验",
        "确认",
    ]

    for word in remove_words:
        normalized = normalized.replace(word, "")

    return normalized.strip()

def _get_field(item: Any, field_name: str, default: str = "") -> str:
    """
    兼容 Pydantic object 和 dict 的字段读取。
    """

    if item is None:
        return default

    if isinstance(item, dict):
        return item.get(field_name, default) or default

    return getattr(item, field_name, default) or default


def _get_nodes(branch_diagram: Any) -> List[Any]:
    """
    读取 BranchFlowSpec / dict 中的 nodes。
    """

    if branch_diagram is None:
        return []

    if isinstance(branch_diagram, dict):
        nodes = branch_diagram.get("nodes", [])
        return nodes if isinstance(nodes, list) else []

    nodes = getattr(branch_diagram, "nodes", [])
    return nodes if isinstance(nodes, list) else []


def _get_decisions(decomposition_spec: Any) -> List[Any]:
    """
    读取 DecompositionSpec / dict 中的 decisions。
    """

    if decomposition_spec is None:
        return []

    if isinstance(decomposition_spec, dict):
        decisions = decomposition_spec.get("decisions", [])
        return decisions if isinstance(decisions, list) else []

    decisions = getattr(decomposition_spec, "decisions", [])
    return decisions if isinstance(decisions, list) else []

def _get_flows(decomposition_spec: Any) -> list[Any]:
    """
    读取 DecompositionSpec / dict 中的 flows。

    作用：
    当 coverage 检测发现某个 decision 缺失时，
    后续可以从 flows 中找出这个 decision 的入边和出边。
    """

    if decomposition_spec is None:
        return []

    if isinstance(decomposition_spec, dict):
        flows = decomposition_spec.get("flows", [])
        return flows if isinstance(flows, list) else []

    flows = getattr(decomposition_spec, "flows", [])
    return flows if isinstance(flows, list) else []


def _is_text_match(text_a: str, text_b: str) -> bool:
    """
    判断两个文本是否可以认为是同一个节点。

    例如：
    支付是否成功
    系统判断支付是否成功

    应该被认为匹配。
    """

    a = _normalize_text(text_a)
    b = _normalize_text(text_b)

    if not a or not b:
        return False

    return a in b or b in a


def _format_flow(flow: Any) -> str:
    """
    把 Decomposition flow 格式化成 retry prompt 更容易理解的文字。
    """

    source = _get_field(flow, "source", "")
    target = _get_field(flow, "target", "")
    condition = _get_field(flow, "condition", "")

    if condition:
        return f"- {source} -> {target} [condition: {condition}]"

    return f"- {source} -> {target}"


def _get_related_flows(decision_text: str, decomposition_spec: Any) -> list[str]:
    """
    找出和缺失 decision 相关的 flows。

    包括：
    1. A -> decision
    2. decision -> B
    3. decision -> C
    """

    related_flows = []

    for flow in _get_flows(decomposition_spec):
        source = _get_field(flow, "source", "")
        target = _get_field(flow, "target", "")

        if _is_text_match(source, decision_text) or _is_text_match(target, decision_text):
            related_flows.append(_format_flow(flow))

    return related_flows

def _extract_decision_text(decision: Any) -> str:
    """
    从 D Agent 的 decision item 中提取判断文本。

    兼容字段：
    1. question
    2. name
    3. text
    """

    for field_name in ["question", "name", "text"]:
        value = _get_field(decision, field_name, "")
        if value:
            return value

    return ""


def _extract_node_text(node: Any) -> str:
    """
    从 branch node 中提取文本。
    """

    return _get_field(node, "text", "")


def _extract_node_kind(node: Any) -> str:
    """
    从 branch node 中提取 kind。
    """

    return _get_field(node, "kind", "")


def _is_decision_covered(decision_text: str, node_texts: list[str]) -> bool:
    """
    判断 D Agent 的 decision 是否被 Branch nodes 覆盖。

    使用双向包含。
    例如：
    expected = 支付是否成功
    actual = 系统判断支付是否成功
    应该返回 True。
    """

    expected = _normalize_text(decision_text)

    if not expected:
        return True

    for node_text in node_texts:
        actual = _normalize_text(node_text)

        if not actual:
            continue

        if expected in actual or actual in expected:
            return True

    return False

def check_decomposition_decision_coverage(
    branch_diagram: Any,
    decomposition_spec: Any,
) -> List[str]:
    """
    检查 Decomposition Agent decisions 是否被 BranchFlowSpec 覆盖。

    返回：
    errors: List[str]

    如果 D Agent 识别出“支付是否成功”，但 Branch nodes 中没有相似节点，
    则返回错误，用于触发 branch retry。
    """

    decisions = _get_decisions(decomposition_spec)
    nodes = _get_nodes(branch_diagram)

    if not decisions or not nodes:
        return []

    # 优先使用 branch 中的 decision 节点文本。
    # 如果模型把判断节点 kind 生成错了，再退一步使用全部节点文本。
    decision_node_texts = [
        _extract_node_text(node)
        for node in nodes
        if _extract_node_kind(node) == "decision"
    ]

    all_node_texts = [
        _extract_node_text(node)
        for node in nodes
    ]

    searchable_texts = decision_node_texts if decision_node_texts else all_node_texts

    errors = []

    for decision in decisions:
        decision_text = _extract_decision_text(decision)

        if not decision_text:
            continue

    if not _is_decision_covered(decision_text, searchable_texts):
        related_flows = _get_related_flows(
            decision_text=decision_text,
            decomposition_spec=decomposition_spec,
        )

        if related_flows:
            errors.append(
                "Decomposition decision 未被 Branch 图覆盖："
                f"{decision_text}\n"
                "相关 flows：\n"
                + "\n".join(related_flows)
            )
        else:
            errors.append(
                f"Decomposition decision 未被 Branch 图覆盖：{decision_text}"
            )
    return errors