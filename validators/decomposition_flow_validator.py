from typing import Any


# ============================================================
# Part 1. 通用字段读取函数
# 作用：
# 兼容 Pydantic object 和 dict 两种数据形式。
# ============================================================

def _get_field(item: Any, field_name: str, default: str = "") -> str:
    """
    兼容 dict 和 Pydantic object 的字段读取。

    例如：
    dict: item["source"]
    object: item.source
    """

    if item is None:
        return default

    if isinstance(item, dict):
        return item.get(field_name, default) or default

    return getattr(item, field_name, default) or default


def _normalize_text(text: Any) -> str:
    """
    文本归一化，用于比较 D Agent flow 和 Branch node / edge。

    目标：
    - 支付是否成功
    - 系统判断支付是否成功
    - 支付是否成功？

    应该被认为是相近文本。
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
        "调用",
        "判断",
        "检查",
        "验证",
        "校验",
        "确认",
        "模块",
    ]

    for word in remove_words:
        normalized = normalized.replace(word, "")

    return normalized.strip()


def _is_text_match(text_a: Any, text_b: Any) -> bool:
    """
    判断两个文本是否可以视为匹配。

    使用双向包含：
    - 支付是否成功
    - 系统判断支付是否成功

    这两个应该匹配。
    """

    a = _normalize_text(text_a)
    b = _normalize_text(text_b)

    if not a or not b:
        return False

    return a in b or b in a


# ============================================================
# Part 2. 读取 DecompositionSpec / BranchFlowSpec
# ============================================================

def _get_decisions(decomposition_spec: Any) -> list[Any]:
    """
    读取 Decomposition Agent 的 decisions。
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
    读取 Decomposition Agent 的 flows。
    """

    if decomposition_spec is None:
        return []

    if isinstance(decomposition_spec, dict):
        flows = decomposition_spec.get("flows", [])
        return flows if isinstance(flows, list) else []

    flows = getattr(decomposition_spec, "flows", [])
    return flows if isinstance(flows, list) else []


def _get_nodes(branch_diagram: Any) -> list[Any]:
    """
    读取 BranchFlowSpec 的 nodes。
    """

    if branch_diagram is None:
        return []

    if isinstance(branch_diagram, dict):
        nodes = branch_diagram.get("nodes", [])
        return nodes if isinstance(nodes, list) else []

    nodes = getattr(branch_diagram, "nodes", [])
    return nodes if isinstance(nodes, list) else []


def _get_edges(branch_diagram: Any) -> list[Any]:
    """
    读取 BranchFlowSpec 的 edges。
    """

    if branch_diagram is None:
        return []

    if isinstance(branch_diagram, dict):
        edges = branch_diagram.get("edges", [])
        return edges if isinstance(edges, list) else []

    edges = getattr(branch_diagram, "edges", [])
    return edges if isinstance(edges, list) else []


# ============================================================
# Part 3. 提取节点、边、decision、flow 信息
# ============================================================

def _extract_decision_text(decision: Any) -> str:
    """
    从 Decomposition decision item 中提取判断文本。

    兼容字段：
    - question
    - name
    - text
    """

    for field_name in ["question", "name", "text"]:
        value = _get_field(decision, field_name, "")
        if value:
            return value

    return ""


def _extract_node_id(node: Any) -> str:
    """
    读取 Branch node.id。
    """

    return _get_field(node, "id", "")


def _extract_node_text(node: Any) -> str:
    """
    读取 Branch node.text。
    """

    return _get_field(node, "text", "")


def _extract_edge_source(edge: Any) -> str:
    """
    读取 Branch edge.source。
    """

    return _get_field(edge, "source", "")


def _extract_edge_target(edge: Any) -> str:
    """
    读取 Branch edge.target。
    """

    return _get_field(edge, "target", "")


def _extract_edge_label(edge: Any) -> str:
    """
    读取 Branch edge.label。
    """

    return _get_field(edge, "label", "")


def _format_flow(flow: Any) -> str:
    """
    把 D Agent flow 格式化为可读错误信息。

    例如：
    支付是否成功 -> 释放库存 [condition: 支付失败]
    """

    source = _get_field(flow, "source", "")
    target = _get_field(flow, "target", "")
    condition = _get_field(flow, "condition", "")

    if condition:
        return f"{source} -> {target} [condition: {condition}]"

    return f"{source} -> {target}"


# ============================================================
# Part 4. 匹配工具函数
# ============================================================

def _find_matching_node_id(nodes: list[Any], text: str) -> str:
    """
    根据 D Agent 文本，在 Branch nodes 中找最匹配的 node.id。

    使用打分策略：
    1. 完全匹配优先；
    2. 较长文本包含匹配其次；
    3. 太短的包含匹配直接忽略，避免“库存”误匹配。
    """

    query = _normalize_text(text)

    if not query:
        return ""

    best_node_id = ""
    best_score = 0

    for node in nodes:
        node_text = _extract_node_text(node)
        node_id = _extract_node_id(node)
        candidate = _normalize_text(node_text)

        if not candidate:
            continue

        score = 0

        # 完全匹配最可靠
        if query == candidate:
            score = 100

        # 双向包含，但必须长度足够
        elif len(query) >= 4 and query in candidate:
            score = 60 + len(query)

        elif len(candidate) >= 4 and candidate in query:
            score = 50 + len(candidate)

        if score > best_score:
            best_score = score
            best_node_id = node_id

    return best_node_id

def _condition_matches_edge_label(condition: str, label: str) -> bool:
    """
    判断 D Agent flow.condition 是否和 Branch edge.label 匹配。

    例如：
    condition = 风控不通过
    label = 不通过

    可以认为匹配。
    """

    if not condition:
        return True

    normalized_condition = _normalize_text(condition)
    normalized_label = _normalize_text(label)

    if not normalized_condition:
        return True

    if not normalized_label:
        return False

    return (
        normalized_condition in normalized_label
        or normalized_label in normalized_condition
    )


def _is_source_a_decomposition_decision(
    source_text: str,
    decision_texts: list[str],
) -> bool:
    """
    判断某条 Decomposition flow 的 source 是否是真正的 decision。

    注意：
    这里必须比普通文本匹配更严格。
    不能把“库存检查模块”误判成“库存是否充足”。
    """

    source_norm = _normalize_text(source_text)

    if not source_norm:
        return False

    for decision_text in decision_texts:
        decision_norm = _normalize_text(decision_text)

        if not decision_norm:
            continue

        # 1. 完全匹配：最可靠
        if source_norm == decision_norm:
            return True

        # 2. source 或 decision 带有明显判断语义时，才允许包含匹配
        # 例如：
        # source = 系统判断支付是否成功
        # decision = 支付是否成功
        source_has_decision_signal = any(
            signal in str(source_text)
            for signal in ["是否", "能否", "判断", "检查", "验证", "校验", "确认"]
        )

        decision_has_decision_signal = any(
            signal in str(decision_text)
            for signal in ["是否", "能否", "判断", "检查", "验证", "校验", "确认"]
        )

        if source_has_decision_signal or decision_has_decision_signal:
            shorter_len = min(len(source_norm), len(decision_norm))

            # 太短的匹配不可信，例如“库存”匹配“库存是否充足”
            if shorter_len >= 4 and (
                source_norm in decision_norm or decision_norm in source_norm
            ):
                return True

    return False


# ============================================================
# Part 5. 对外主函数
# ============================================================

def check_decomposition_flow_coverage(
    branch_diagram: Any,
    decomposition_spec: Any,
) -> list[str]:
    """
    检查 Decomposition Agent 中的 decision flows
    是否被 BranchFlowSpec 的 edges 覆盖。

    只检查 source 是 decision 的 flows。

    例如 D Agent 中有：
    风控是否通过 -> 冻结订单并提交人工审核 [condition: 风控不通过]

    那 Branch 图中必须有：
    风控是否通过对应节点 -> 冻结订单并提交人工审核对应节点
    且 edge.label 应能匹配 “风控不通过”。
    """

    errors: list[str] = []

    decisions = _get_decisions(decomposition_spec)
    flows = _get_flows(decomposition_spec)
    nodes = _get_nodes(branch_diagram)
    edges = _get_edges(branch_diagram)

    if not decisions or not flows or not nodes:
        return errors

    decision_texts = [
        _extract_decision_text(decision)
        for decision in decisions
        if _extract_decision_text(decision)
    ]

    for flow in flows:
        source_text = _get_field(flow, "source", "")
        target_text = _get_field(flow, "target", "")
        condition = _get_field(flow, "condition", "")

        if not source_text or not target_text:
            continue

        # 第一版只检查 decision 出边。
        # 普通 process -> process 先不检查，避免误报过多。
        if not _is_source_a_decomposition_decision(source_text, decision_texts):
            continue

        source_id = _find_matching_node_id(nodes, source_text)
        target_id = _find_matching_node_id(nodes, target_text)

        formatted_flow = _format_flow(flow)

        if not source_id:
            continue

        if not target_id:
            continue

        matched_edges = [
            edge
            for edge in edges
            if _extract_edge_source(edge) == source_id
            and _extract_edge_target(edge) == target_id
        ]

        if not matched_edges:
            errors.append(
                "Decomposition decision flow 未被 Branch 图覆盖："
                f"{formatted_flow}"
            )
            continue

        if condition:
            has_matching_label = any(
                _condition_matches_edge_label(
                    condition=condition,
                    label=_extract_edge_label(edge),
                )
                for edge in matched_edges
            )

            if not has_matching_label:
                errors.append(
                    "Decomposition decision flow 的 edge.label 不匹配："
                    f"{formatted_flow}"
                )

    return errors