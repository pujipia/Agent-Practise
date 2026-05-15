from typing import Any, Dict, List

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
    """

    normalized = _normalize(text)

    if _is_return_node_text(normalized):
        return False

    return any(
        _normalize(keyword) in normalized
        for keyword in END_KEYWORDS
    )


def _find_end_node_id(nodes: List[Dict[str, Any]]) -> str | None:
    """
    如果已有结束节点，返回它的 id。
    """

    for node in nodes:
        node_id = node.get("id", "")
        node_text = node.get("text", "")

        if _is_end_text(node_id) or _is_end_text(node_text):
            return str(node_id)

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


def repair_end_edges(branch_diagram: Any) -> BranchFlowSpec:
    """
    最小版终点补全。

    只做：
    1. 补“流程结束”节点；
    2. 给明显终止动作节点补一条到“流程结束”的边。

    不做：
    1. 不删除已有边；
    2. 不修改回边；
    3. 不重排节点；
    4. 不影响 loop_repairs.py。
    """

    data = _to_dict(branch_diagram)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if not isinstance(nodes, list) or not isinstance(edges, list):
        return BranchFlowSpec.model_validate(data)

    end_action_node_ids = []

    for node in nodes:
        node_id = str(node.get("id", ""))
        node_text = str(node.get("text", ""))

        if _is_end_action_text(node_text):
            end_action_node_ids.append(node_id)

    if not end_action_node_ids:
        return BranchFlowSpec.model_validate(data)

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