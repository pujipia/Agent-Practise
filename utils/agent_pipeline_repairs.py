from typing import Any, Dict, List, Optional

from models.branch_flow_spec import BranchFlowSpec


def _to_dict(diagram: Any) -> Dict[str, Any]:
    """
    将 BranchFlowSpec / dict 统一转换成 dict。

    作用：
    1. repair 函数可以兼容 Pydantic model
    2. 也可以兼容普通 dict
    """

    if isinstance(diagram, dict):
        return diagram

    if hasattr(diagram, "model_dump"):
        return diagram.model_dump()

    if hasattr(diagram, "dict"):
        return diagram.dict()

    raise TypeError("Unsupported diagram type. Expected dict or Pydantic model.")


def _normalize_text(text: Any) -> str:
    """
    文本标准化。

    作用：
    1. 避免 None 报错
    2. 去掉空格和换行
    3. 英文统一转小写
    """

    if text is None:
        return ""

    return str(text).lower().replace(" ", "").replace("\n", "")


def _node_text(node: Dict[str, Any]) -> str:
    """
    读取 node.text。
    """

    return str(node.get("text", "") or "")


def _edge_label(edge: Dict[str, Any]) -> str:
    """
    读取 edge.label。
    """

    return str(edge.get("label", "") or "")


def _find_node_id_by_keywords(
    nodes: List[Dict[str, Any]],
    keyword_groups: List[List[str]],
    kind: Optional[str] = None,
) -> Optional[str]:
    """
    根据关键词查找节点 id。

    keyword_groups 的含义：
    - 外层 list 表示多个候选匹配方案
    - 内层 list 表示这些关键词必须同时出现在 node.text 中

    例如：
    [
        ["生成", "mermaid", "代码"],
        ["mermaid", "代码生成"]
    ]

    表示只要满足其中一组即可。
    """

    for node in nodes:
        if kind is not None and node.get("kind") != kind:
            continue

        text = _normalize_text(_node_text(node))

        for keywords in keyword_groups:
            if all(_normalize_text(keyword) in text for keyword in keywords):
                return node.get("id")

    return None


def _get_node_by_id(nodes: List[Dict[str, Any]], node_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    根据 id 查找节点。
    """

    if not node_id:
        return None

    for node in nodes:
        if node.get("id") == node_id:
            return node

    return None


def _edge_exists(
    edges: List[Dict[str, Any]],
    source: Optional[str],
    target: Optional[str],
    label: Optional[str] = None,
) -> bool:
    """
    判断某条 edge 是否已存在。
    """

    if not source or not target:
        return False

    for edge in edges:
        if edge.get("source") != source:
            continue

        if edge.get("target") != target:
            continue

        if label is None:
            return True

        if _edge_label(edge) == label:
            return True

    return False


def _add_edge(
    edges: List[Dict[str, Any]],
    source: Optional[str],
    target: Optional[str],
    label: str = "",
) -> None:
    """
    添加 edge，并避免重复添加。
    """

    if not source or not target:
        return

    if _edge_exists(edges, source, target, label):
        return

    edges.append(
        {
            "source": source,
            "target": target,
            "label": label,
        }
    )


def _remove_edges(
    edges: List[Dict[str, Any]],
    source_ids: List[Optional[str]],
    target_ids: List[Optional[str]],
    keep_return_edges: bool = True,
) -> None:
    """
    删除指定 source -> target 的错误边。

    keep_return_edges=True 时，如果 label 是“返回/重试”类，就不删。
    """

    source_set = {source_id for source_id in source_ids if source_id}
    target_set = {target_id for target_id in target_ids if target_id}

    if not source_set or not target_set:
        return

    kept_edges = []

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        label = _normalize_text(_edge_label(edge))

        should_remove = source in source_set and target in target_set

        if should_remove and keep_return_edges:
            if any(keyword in label for keyword in ["返回", "重新", "重试", "return", "retry", "back"]):
                should_remove = False

        if not should_remove:
            kept_edges.append(edge)

    edges[:] = kept_edges


def _remove_outgoing_edges_to_any(
    edges: List[Dict[str, Any]],
    source_id: Optional[str],
    target_ids: List[Optional[str]],
    keep_return_edges: bool = True,
) -> None:
    """
    删除某个 source 指向多个错误 target 的边。
    """

    if not source_id:
        return

    _remove_edges(
        edges=edges,
        source_ids=[source_id],
        target_ids=target_ids,
        keep_return_edges=keep_return_edges,
    )


def _next_node_id(nodes: List[Dict[str, Any]]) -> str:
    """
    生成一个新的 node id。

    优先继续使用 A-Z。
    如果超过 Z，则使用 N1, N2, N3...
    """

    used_ids = {str(node.get("id")) for node in nodes}

    for code in range(ord("A"), ord("Z") + 1):
        candidate = chr(code)
        if candidate not in used_ids:
            return candidate

    index = 1
    while True:
        candidate = f"N{index}"
        if candidate not in used_ids:
            return candidate

        index += 1


def _ensure_node(
    nodes: List[Dict[str, Any]],
    node_id: Optional[str],
    text: str,
    kind: str,
) -> str:
    """
    确保某个节点存在。

    如果 node_id 已经存在，直接返回。
    如果不存在，则创建新节点。
    """

    if node_id and _get_node_by_id(nodes, node_id):
        return node_id

    new_id = _next_node_id(nodes)

    nodes.append(
        {
            "id": new_id,
            "text": text,
            "kind": kind,
        }
    )

    return new_id


def _deduplicate_edges(edges: List[Dict[str, Any]]) -> None:
    """
    去除重复边。
    """

    seen = set()
    unique_edges = []

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        label = edge.get("label", "")

        key = (source, target, label)

        if key in seen:
            continue

        seen.add(key)
        unique_edges.append(edge)

    edges[:] = unique_edges


def repair_agent_pipeline_edges(branch_diagram: Any) -> BranchFlowSpec:
    """
    修复 Agent pipeline 类流程图中的常见主链路断裂问题。

    当前重点修复：
    1. “逐个处理流程片段 / 默认流程处理”错误回到 Flow Segmenter
    2. 缺失“生成 Mermaid 代码”节点
    3. linear / branch extractor 没有连接到“生成 Mermaid 代码”
    4. “生成 Mermaid 代码”没有连接到“Mermaid 是否可以渲染”
    5. “Mermaid 是否可以渲染”没有入边
    6. 保存节点错误回到渲染检查节点
    """

    data = _to_dict(branch_diagram)

    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    edges: List[Dict[str, Any]] = data.get("edges", [])

    # ------------------------------------------------------------
    # Part 1. 查找 Agent pipeline 中的关键节点
    # ------------------------------------------------------------

    flow_segmenter_id = _find_node_id_by_keywords(
        nodes,
        [
            ["flow", "segmenter"],
            ["切分", "流程"],
        ],
    )

    multi_flow_decision_id = _find_node_id_by_keywords(
        nodes,
        [
            ["多个", "流程"],
            ["多", "流程"],
            ["multiple", "flow"],
        ],
        kind="decision",
    )

    process_each_segment_id = _find_node_id_by_keywords(
        nodes,
        [
            ["逐个", "流程片段"],
            ["逐个处理"],
            ["process", "segment"],
        ],
    )

    default_flow_id = _find_node_id_by_keywords(
        nodes,
        [
            ["默认流程"],
            ["直接处理"],
            ["default", "flow"],
        ],
    )

    research_agent_id = _find_node_id_by_keywords(
        nodes,
        [
            ["research", "agent"],
            ["抽取", "关键概念"],
        ],
    )

    linear_extractor_id = _find_node_id_by_keywords(
        nodes,
        [
            ["linear", "extractor"],
            ["linear", "rule"],
        ],
    )

    branch_extractor_id = _find_node_id_by_keywords(
        nodes,
        [
            ["branch", "extractor"],
            ["branch", "flow"],
        ],
    )

    mermaid_generation_id = _find_node_id_by_keywords(
        nodes,
        [
            ["生成", "mermaid", "代码"],
            ["mermaid", "代码生成"],
            ["generate", "mermaid"],
        ],
    )

    mermaid_render_check_id = _find_node_id_by_keywords(
        nodes,
        [
            ["mermaid", "是否", "渲染"],
            ["mermaid", "可以", "渲染"],
            ["mermaid", "渲染"],
            ["mermaid", "render"],
        ],
        kind="decision",
    )

    save_output_id = _find_node_id_by_keywords(
        nodes,
        [
            ["保存", "mermaid"],
            ["保存", "svg"],
            ["保存", "文件"],
            ["save", "mermaid"],
            ["save", "svg"],
        ],
    )

    render_error_prompt_id = _find_node_id_by_keywords(
        nodes,
        [
            ["提示", "检查", "mermaid"],
            ["提示", "检查", "流程描述"],
            ["check", "mermaid"],
            ["check", "description"],
        ],
    )

    unsupported_prompt_id = _find_node_id_by_keywords(
        nodes,
        [
            ["不支持", "流程类型"],
            ["unsupported", "flow"],
        ],
    )

    router_id = _find_node_id_by_keywords(
        nodes,
        [
            ["router"],
            ["判断", "流程类型"],
        ],
    )

    flow_type_decision_id = _find_node_id_by_keywords(
        nodes,
        [
            ["流程类型"],
            ["flow", "type"],
        ],
        kind="decision",
    )

    # ------------------------------------------------------------
    # Part 2. 修复 Flow Segmenter 后的主链路
    #
    # 正确结构：
    # 逐个处理每个流程片段 -> 调用 Research Agent
    # 直接处理默认流程 -> 调用 Research Agent
    #
    # 错误结构：
    # 逐个处理每个流程片段 -> 调用 Flow Segmenter
    # 直接处理默认流程 -> 调用 Flow Segmenter
    # ------------------------------------------------------------

    if research_agent_id:
        wrong_targets_after_segment = [
            flow_segmenter_id,
            multi_flow_decision_id,
        ]

        _remove_outgoing_edges_to_any(
            edges,
            source_id=process_each_segment_id,
            target_ids=wrong_targets_after_segment,
        )

        _remove_outgoing_edges_to_any(
            edges,
            source_id=default_flow_id,
            target_ids=wrong_targets_after_segment,
        )

        _add_edge(edges, process_each_segment_id, research_agent_id)
        _add_edge(edges, default_flow_id, research_agent_id)

    # ------------------------------------------------------------
    # Part 3. 修复 Router 与流程类型判断之间的主链路
    #
    # 正确结构：
    # 调用 Router 判断流程类型 -> 流程类型是什么？
    #
    # 错误结构：
    # 流程类型是什么？ -> 调用 Router 判断流程类型
    # ------------------------------------------------------------

    if router_id and flow_type_decision_id:
        _remove_edges(
            edges,
            source_ids=[flow_type_decision_id],
            target_ids=[router_id],
            keep_return_edges=False,
        )

        _add_edge(edges, router_id, flow_type_decision_id)

    # ------------------------------------------------------------
    # Part 4. 确保“生成 Mermaid 代码”节点存在
    #
    # 如果用户输入中明确写了“系统生成 Mermaid 代码”，
    # 但 Branch Extractor 吞掉了这个节点，就自动补回来。
    # ------------------------------------------------------------

    has_extractor = linear_extractor_id or branch_extractor_id

    if has_extractor and mermaid_render_check_id and mermaid_generation_id is None:
        mermaid_generation_id = _ensure_node(
            nodes=nodes,
            node_id=None,
            text="生成 Mermaid 代码",
            kind="subroutine",
        )

    # ------------------------------------------------------------
    # Part 5. 修复 extractor -> Mermaid generation -> render check
    #
    # 正确结构：
    # linear extractor -> 生成 Mermaid 代码
    # branch extractor -> 生成 Mermaid 代码
    # 生成 Mermaid 代码 -> Mermaid 代码是否可以渲染？
    #
    # 错误结构：
    # linear extractor -> 保存 Mermaid 文件
    # branch extractor -> 保存 Mermaid 文件
    # ------------------------------------------------------------

    if mermaid_generation_id:
        wrong_targets_after_extractor = [
            mermaid_render_check_id,
            save_output_id,
            flow_type_decision_id,
        ]

        _remove_outgoing_edges_to_any(
            edges,
            source_id=linear_extractor_id,
            target_ids=wrong_targets_after_extractor,
        )

        _remove_outgoing_edges_to_any(
            edges,
            source_id=branch_extractor_id,
            target_ids=wrong_targets_after_extractor,
        )

        _add_edge(edges, linear_extractor_id, mermaid_generation_id)
        _add_edge(edges, branch_extractor_id, mermaid_generation_id)

        if mermaid_render_check_id:
            _add_edge(edges, mermaid_generation_id, mermaid_render_check_id)

    # ------------------------------------------------------------
    # Part 6. 修复渲染失败后的返回目标
    #
    # 正确结构：
    # Mermaid 代码是否可以渲染？ --不能渲染--> 提示用户检查...
    # 提示用户检查... --返回--> 生成 Mermaid 代码
    #
    # 错误结构：
    # 提示用户检查... --返回--> 用户输入流程描述
    # ------------------------------------------------------------

    if render_error_prompt_id and mermaid_generation_id:
        first_input_id = _find_node_id_by_keywords(
            nodes,
            [
                ["用户输入"],
                ["input"],
            ],
        )

        _remove_outgoing_edges_to_any(
            edges,
            source_id=render_error_prompt_id,
            target_ids=[first_input_id],
            keep_return_edges=False,
        )

        _add_edge(edges, render_error_prompt_id, mermaid_generation_id, label="返回")

    # ------------------------------------------------------------
    # Part 7. 修复保存节点错误回流
    #
    # 正确结构：
    # 保存 Mermaid 文件和 SVG 图片 通常是终点
    #
    # 错误结构：
    # 保存 Mermaid 文件和 SVG 图片 -> Mermaid 代码是否可以渲染？
    # ------------------------------------------------------------

    _remove_outgoing_edges_to_any(
        edges,
        source_id=save_output_id,
        target_ids=[mermaid_render_check_id, flow_type_decision_id, router_id],
        keep_return_edges=False,
    )

    # ------------------------------------------------------------
    # Part 8. 修复不支持流程类型错误回到 Router
    #
    # 正确结构：
    # 不支持流程类型通常是异常提示节点，不应该回到 Router。
    # ------------------------------------------------------------

    _remove_outgoing_edges_to_any(
        edges,
        source_id=unsupported_prompt_id,
        target_ids=[router_id, flow_type_decision_id],
        keep_return_edges=False,
    )

    # ------------------------------------------------------------
    # Part 9. 去重并重新校验
    # ------------------------------------------------------------

    _deduplicate_edges(edges)

    data["nodes"] = nodes
    data["edges"] = edges

    return BranchFlowSpec.model_validate(data)