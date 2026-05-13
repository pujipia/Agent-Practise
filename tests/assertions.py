#检查输出是否符合标准答案
from typing import Any, List, Tuple, Union

def normalize_text(text: Any) -> str:
    """
    文本标准化函数。

    作用：
    1. 把 None 转成空字符串，避免报错
    2. 转成小写，方便英文匹配
    3. 去掉空格和换行，减少格式差异影响
    4. 去掉中文问号和英文问号，避免 decision 节点因问号不同而匹配失败
    """

    if text is None:
        return ""

    return (
        str(text)
        .lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("？", "")
        .replace("?", "")
    )

def match_text_rule(actual_text: Any, rule: Any) -> bool:
    """
    通用文本匹配规则。

    支持两种检查方式：

    1. 字符串包含匹配：
       rule = "生成 Mermaid 代码"

       只要 actual_text 中包含这段文本，就认为匹配。

    2. 关键词集合匹配：
       rule = ["Mermaid", "渲染"]

       只要 actual_text 同时包含 Mermaid 和 渲染，就认为匹配。

    这样可以允许 LLM 输出：
    - Mermaid 是否可以渲染？
    - 判断 Mermaid 是否可以渲染
    - Mermaid 代码是否可以渲染
    都被认为是同一个关键节点。
    """

    normalized_actual = normalize_text(actual_text)

    # 情况 1：关键词列表匹配
    if isinstance(rule, list):
        return all(
            normalize_text(keyword) in normalized_actual
            for keyword in rule
        )

    # 情况 2：普通字符串包含匹配
    normalized_rule = normalize_text(rule)

    return normalized_rule in normalized_actual

def get_nodes(diagram: Any) -> List[Any]:
    """
    从 diagram 中安全读取 nodes。

    兼容两种情况：
    1. Pydantic model: diagram.nodes
    2. dict: diagram["nodes"]
    """

    if diagram is None:
        return []

    if isinstance(diagram, dict):
        nodes = diagram.get("nodes", [])
        return nodes if isinstance(nodes, list) else []

    nodes = getattr(diagram, "nodes", [])
    return nodes if isinstance(nodes, list) else []


def get_edges(diagram: Any) -> List[Any]:
    """
    从 diagram 中安全读取 edges。

    兼容两种情况：
    1. Pydantic model: diagram.edges
    2. dict: diagram["edges"]
    """

    if diagram is None:
        return []

    if isinstance(diagram, dict):
        edges = diagram.get("edges", [])
        return edges if isinstance(edges, list) else []

    edges = getattr(diagram, "edges", [])
    return edges if isinstance(edges, list) else []


def get_field(item: Any, field_name: str, default: str = "") -> str:
    """
    从 node / edge 中安全读取字段。

    兼容两种情况：
    1. Pydantic object: item.text / item.label
    2. dict: item["text"] / item["label"]
    """

    if item is None:
        return default

    if isinstance(item, dict):
        return item.get(field_name, default) or default

    return getattr(item, field_name, default) or default


def get_node_texts(diagram: Any) -> List[str]:
    """
    提取所有节点文本。
    """

    nodes = get_nodes(diagram)
    return [get_field(node, "text", "") for node in nodes]


def get_edge_labels(diagram: Any) -> List[str]:
    """
    提取所有边标签。
    """

    edges = get_edges(diagram)
    return [get_field(edge, "label", "") for edge in edges]


def check_required_node_texts(
    diagram: Any,
    required_texts: List[Any],
) -> Tuple[bool, List[Any]]:
    """
    检查 diagram 中是否包含所有必须出现的节点文本。

    支持两种 required_texts 写法：

    1. 普通字符串：
       "生成 Mermaid 代码"

    2. 关键词列表：
       ["Mermaid", "渲染"]

    第二种写法表示：
    只要某个节点 text 同时包含这些关键词，就认为通过。
    """

    actual_texts = get_node_texts(diagram)
    missing = []

    for required_rule in required_texts:
        found = any(
            match_text_rule(actual_text, required_rule)
            for actual_text in actual_texts
        )

        if not found:
            missing.append(required_rule)

    return len(missing) == 0, missing


def check_required_edge_labels(
    diagram: Any,
    required_labels: List[str],
) -> Tuple[bool, List[str]]:
    """
    检查 diagram 中是否包含所有必须出现的边标签。

    同样使用“包含匹配”。

    例如：
    required_label = "支持"
    actual_label = "文件格式支持"

    可以认为通过。
    """

    actual_labels = get_edge_labels(diagram)
    normalized_actual_labels = [normalize_text(label) for label in actual_labels]

    missing = []

    for required_label in required_labels:
        normalized_required = normalize_text(required_label)

        found = any(
            normalized_required in actual_label
            for actual_label in normalized_actual_labels
        )

        if not found:
            missing.append(required_label)

    return len(missing) == 0, missing


def _find_node_ids_by_text(
    diagram: Any,
    expected_rule: Any,
) -> List[str]:
    """
    根据节点文本查找可能匹配的 node id。

    支持两种 expected_rule：

    1. 普通字符串：
       "生成 Mermaid 代码"

    2. 关键词列表：
       ["Mermaid", "渲染"]

    这样可以匹配：
    actual_text = "Mermaid 是否可以渲染？"
    expected_rule = ["Mermaid", "渲染"]
    """

    nodes = get_nodes(diagram)
    matched_ids = []

    for node in nodes:
        node_id = get_field(node, "id", "")
        node_text = get_field(node, "text", "")

        if match_text_rule(node_text, expected_rule):
            matched_ids.append(node_id)

    return matched_ids


def check_required_edges(
    diagram: Any,
    required_edges: List[Tuple[Any, Any]],
) -> Tuple[bool, List[Tuple[Any, Any]]]:
    """
    检查 diagram 中是否包含必须存在的边。

    required_edges 支持两种写法：

    1. 原来的字符串写法：
       ("调用 linear rule extractor", "生成 Mermaid 代码")

    2. 新的关键词写法：
       (["生成", "Mermaid"], ["Mermaid", "渲染"])

    第二种写法表示：
    source 节点 text 同时包含 ["生成", "Mermaid"]
    target 节点 text 同时包含 ["Mermaid", "渲染"]
    """
    edges = get_edges(diagram)
    missing = []

    for source_rule, target_rule in required_edges:
        source_ids = _find_node_ids_by_text(diagram, source_rule)
        target_ids = _find_node_ids_by_text(diagram, target_rule)

        if not source_ids or not target_ids:
            missing.append((source_rule, target_rule))
            continue

        found = False

        for edge in edges:
            source = get_field(edge, "source", "")
            target = get_field(edge, "target", "")

            if source in source_ids and target in target_ids:
                found = True
                break

        if not found:
            missing.append((source_rule, target_rule))

    return len(missing) == 0, missing


def run_case_assertions(diagram: Any, case: Any) -> Tuple[bool, List[str]]:
    """
    对单个测试用例执行所有断言检查。

    返回：
    - bool: 是否通过
    - List[str]: 错误信息列表
    """

    errors = []

    ok_nodes, missing_nodes = check_required_node_texts(
        diagram=diagram,
        required_texts=case.must_have_node_texts,
    )

    if not ok_nodes:
        errors.append(f"缺少关键节点: {missing_nodes}")

    ok_labels, missing_labels = check_required_edge_labels(
        diagram=diagram,
        required_labels=case.must_have_edge_labels,
    )

    if not ok_labels:
        errors.append(f"缺少关键边标签: {missing_labels}")

    ok_edges, missing_edges = check_required_edges(
        diagram=diagram,
        required_edges=case.must_have_edges,
    )

    if not ok_edges:
        errors.append(f"缺少关键边: {missing_edges}")

    return len(errors) == 0, errors