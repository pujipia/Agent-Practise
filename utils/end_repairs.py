from typing import Any, Dict, List, Optional
from copy import deepcopy
from models.branch_flow_spec import BranchFlowSpec


END_TEXTS = ["结束", "流程结束", "结束流程"]

END_KEYWORDS = [
    "输出解析结果",
    "输出解析结果并保存文件信息",
    "保存文件信息",
    "进入系统首页",
    "进入首页",
    "进入主页",
    "锁定账号",
    "拒绝文件",
    "取消订单",
    "终止申请",
    "生成报告",
    "通知完成",
]
INVALID_END_TARGETS = {
    "",
    "null",
    "none",
    "nil",
    "undefined",
}
END_TARGET_ALIASES = {
    "end",
    "结束",
    "流程结束",
    "input_end",
    "output_end",
    "finish",
    "finished",
    "done",
}

RETURN_KEYWORDS = [
    "重新上传",
    "重新输入",
    "重新选择",
    "重新支付",
    "压缩文件后重新上传",
    "提示登录失败",
    "提示验证码错误",
    "返回",
]


def _to_dict(branch_diagram: Any) -> Dict[str, Any]:
    """
    把 BranchFlowSpec 或 dict 统一转成 dict，方便修改 nodes / edges。
    """

    if isinstance(branch_diagram, dict):
        return branch_diagram

    if hasattr(branch_diagram, "model_dump"):
        return branch_diagram.model_dump()

    if hasattr(branch_diagram, "dict"):
        return branch_diagram.dict()

    raise TypeError("Unsupported branch diagram type.")


def _normalize(text: Any) -> str:
    """
    简单文本归一化，减少空格、换行、问号影响。
    """

    return (
        str(text or "")
        .replace(" ", "")
        .replace("\n", "")
        .replace("？", "")
        .replace("?", "")
        .strip()
        .lower()
    )


def _is_end_text(text: Any) -> bool:
    """
    判断某个文本是否表示“结束节点”。
    """

    normalized = _normalize(text)

    return any(
        normalized == _normalize(end_text)
        for end_text in END_TEXTS
    )


def _is_return_node_text(text: Any) -> bool:
    """
    判断某个节点是否是返回类节点。
    返回类节点不能接到流程结束。
    """

    normalized = _normalize(text)

    return any(
        _normalize(keyword) in normalized
        for keyword in RETURN_KEYWORDS
    )


def _is_end_action_text(text: Any) -> bool:
    """
    判断某个节点是否是成功/终止动作节点。

    只识别明确表示流程完成、报告生成、建议生成、人工审查、
    工单创建、通知完成等终止语义的动作节点。

    返回/重试类节点不作为终止节点。
    """

    normalized = _normalize(text)

    if not normalized:
        return False

    if _is_return_node_text(normalized):
        return False

    # 1. 报告类终止动作：
    # 例如：
    # 系统生成低风险审查报告
    # 系统生成普通风险提示报告
    # 系统生成修改建议和风险提示报告
    if "生成" in normalized and "报告" in normalized:
        return True

    # 2. 建议类终止动作：
    # 例如：
    # 系统生成高风险终止建议
    if "生成" in normalized and "建议" in normalized:
        return True

    # 3. 提示检查 / 人工审查类终止动作：
    # 例如：
    # 系统提示用户检查合同文件内容
    # 系统提示需要人工审查
    if "提示" in normalized and (
        "检查" in normalized
        or "人工审查" in normalized
        or "人工审核" in normalized
        or "联系客服" in normalized
    ):
        return True

    # 4. 人工审核 / 人工审查 / 提交复核类终止动作
    if (
        "提交人工审核" in normalized
        or "提交人工审查" in normalized
        or "人工审核" in normalized
        or "人工审查" in normalized
    ):
        return True

    # 5. 工单类终止动作
    # 例如：创建发货异常工单
    if "创建" in normalized and "工单" in normalized:
        return True

    # 6. 保留原来的关键词匹配
    return any(
        _normalize(keyword) in normalized
        for keyword in END_KEYWORDS
    )

def _find_end_node_id(nodes: List[Dict[str, Any]]) -> Optional[str]:
    """
    查找真正的结束节点。

    只承认 kind="start_end" 的结束节点。
    不把 kind="process" 且 text="流程结束" 的节点当成真正结束节点，
    避免 LLM 生成的伪结束节点影响 end repair。
    """

    for node in nodes:
        node_id = str(node.get("id", ""))
        node_text = _normalize(node.get("text", ""))
        node_kind = str(node.get("kind", ""))

        if node_kind != "start_end":
            continue

        if _is_end_text(node_id) or _is_end_text(node_text):
            return node_id

    return None


def _next_node_id(nodes: List[Dict[str, Any]]) -> str:
    """
    生成一个未被使用的新节点 id。
    """

    used_ids = {str(node.get("id", "")) for node in nodes}

    for i in range(26):
        candidate = chr(ord("A") + i)
        if candidate not in used_ids:
            return candidate

    index = 1
    while f"END{index}" in used_ids:
        index += 1

    return f"END{index}"


def _edge_exists(edges: List[Dict[str, Any]], source: str, target: str) -> bool:
    """
    判断 source -> target 是否已经存在。
    """

    return any(
        str(edge.get("source", "")) == source
        and str(edge.get("target", "")) == target
        for edge in edges
    )

def _is_invalid_end_target(target: Any) -> bool:
    """
    判断 edge.target 是否是 LLM 生成的无效结束占位符。

    例如：
    target = "null"
    target = None
    target = ""
    target = "None"

    这些都不是合法节点 id，应该被修复为“流程结束”节点。
    """

    normalized = _normalize(target).lower()

    return normalized in [
        "",
        "null",
        "none",
        "nil",
        "undefined",
    ]

def _has_non_return_outgoing_edge(edges: List[Dict[str, Any]], source: str) -> bool:
    """
    判断某个节点是否已经有非返回类出边。

    如果已经有正常出边，说明它不是当前要补结束边的悬空终止节点，
    不应强行再接到“流程结束”。
    """

    for edge in edges:
        if str(edge.get("source", "")) != source:
            continue

        label = str(edge.get("label", "") or "")
        target = str(edge.get("target", "") or "")

        # target 是 null / none / 空字符串，不算正常出边
        if _is_invalid_end_target(target):
            continue

        is_return_edge = (
            "返回" in label
            or "重新" in label
            or "回到" in label
            or "退回" in label
            or "返回" in target
        )

        if not is_return_edge:
            return True

    return False

def repair_end_edges(branch_diagram: Any) -> BranchFlowSpec:
    """
    最小版终点补全。

    只做三件事：
    1. 如果 LLM 生成 target="null" / "none" / 空 target，
       则把这些非法结束占位符改成真正的“流程结束”节点。
    2. 如果明确终止动作节点没有任何出边，
       则补一条到“流程结束”的边。
    3. 不删除已有边、不修改回边、不重排节点。
    """

    data = _to_dict(branch_diagram)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if not isinstance(nodes, list) or not isinstance(edges, list):
        return BranchFlowSpec.model_validate(data)

    # ------------------------------------------------------------
    # Step 1. 找出 LLM 生成的非法结束占位符边
    # 例如：
    # {"source": "6", "target": "null", "label": ""}
    # ------------------------------------------------------------
    invalid_end_edges = []

    end_like_targets = INVALID_END_TARGETS | END_TARGET_ALIASES

    for edge in edges:
        target = _normalize(edge.get("target", "")).lower()

        if target in end_like_targets:
            invalid_end_edges.append(edge)

    # ------------------------------------------------------------
    # Step 2. 找出“明确终止动作且没有任何出边”的节点
    # 注意：
    # 这里只看没有出边的终止动作节点。
    # 已经有出边的节点不再额外补结束边。
    # ------------------------------------------------------------
    edge_sources = {
        str(edge.get("source", ""))
        for edge in edges
        if _normalize(edge.get("target", "")).lower() not in INVALID_END_TARGETS
        and _normalize(edge.get("target", "")).lower() not in END_TARGET_ALIASES
    }

    terminal_node_ids = []

    for node in nodes:
        node_id = str(node.get("id", ""))
        node_text = str(node.get("text", ""))
        node_kind = str(node.get("kind", ""))

        if not node_id:
            continue

        if node_kind == "decision":
            continue

        if node_id in edge_sources:
            continue

        if not _is_end_action_text(node_text):
            continue

        terminal_node_ids.append(node_id)

    # 如果既没有 null target，也没有需要补结束边的终止节点，直接返回
    if not invalid_end_edges and not terminal_node_ids:
        return BranchFlowSpec.model_validate(data)

    # ------------------------------------------------------------
    # Step 3. 找到或创建“流程结束”节点
    # ------------------------------------------------------------
    end_node_id = _find_end_node_id(nodes)

    if end_node_id is None:
        end_node_id = _next_node_id(nodes)

        nodes.append(
            {
                "id": end_node_id,
                "text": "流程结束",
                "kind": "start_end",
            }
        )

    # ------------------------------------------------------------
    # Step 4. 把所有 target=null / none / 空 target 改成“流程结束”
    # ------------------------------------------------------------
    for edge in invalid_end_edges:
        edge["target"] = end_node_id
        edge["label"] = ""

    # ------------------------------------------------------------
    # Step 5. 给明确终止动作节点补结束边
    # ------------------------------------------------------------
    for source_id in terminal_node_ids:
        if _edge_exists(edges, source_id, end_node_id):
            continue

        edges.append(
            {
                "source": source_id,
                "target": end_node_id,
                "label": "",
            }
        )

    data["nodes"] = nodes
    data["edges"] = edges

    return BranchFlowSpec.model_validate(data)

    def _is_return_edge(edge: Dict[str, Any]) -> bool:
        """
        判断一条边是否是返回类边。
        """
        label = str(edge.get("label", "") or "")
        target = str(edge.get("target", "") or "")

        return (
            "返回" in label
            or "重新" in label
            or "回到" in label
            or "退回" in label
            or "返回" in target
        )

    end_action_node_id_set = set(end_action_node_ids)

    filtered_edges = []

    for edge in edges:
        source = str(edge.get("source", ""))

        # 如果结束动作节点还有返回边，删除这条错误边
        if source in end_action_node_id_set and _is_return_edge(edge):
            continue

        filtered_edges.append(edge)

    edges = filtered_edges
    
    for source_id in end_action_node_ids:
        if source_id == end_node_id:
            continue


        if not _edge_exists(edges, source_id, end_node_id):
            edges.append(
                {
                    "source": source_id,
                    "target": end_node_id,
                    "label": "",
                }
            )

    data["nodes"] = nodes
    data["edges"] = edges

    return BranchFlowSpec.model_validate(data)