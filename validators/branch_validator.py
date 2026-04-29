def normalize_text(text: str) -> str:
    return text.replace(" ", "").replace("\n", "")


def has_edge(spec, source_id: str, target_id: str) -> bool:
    for edge in spec.edges:
        if edge.source == source_id and edge.target == target_id:
            return True
    return False

def is_terminal_node(node) -> bool:
    """
    判断一个节点是不是流程结束类节点。
    这些节点没有出边是正常的。
    """
    text = normalize_text(node.text)

    terminal_keywords = [
        "结束",
        "流程结束",
        "完成",
        "进入主页",
        "进入首页",
        "进入系统",
        "登录成功",
        "提交成功",
        "支付成功",
        "生成订单",
        "订单完成",
        "审核通过",
    ]

    return any(keyword in text for keyword in terminal_keywords)

def validate_branch_flow(spec, user_input: str = ""):
    """
    校验 branch flow 的结构是否合理。

    主要检查：
    1. edge 的 source / target 是否存在
    2. decision 节点是否至少有两个出口
    3. 是否存在孤立节点
    4. 文本中出现“返回 / 重新输入 / 再次输入”时，是否存在返回边
    """

    errors = []
    warnings = []

    node_ids = {node.id for node in spec.nodes}

    from_count = {}
    to_count = {}

    # 1. 检查边的 source / target 是否存在
    for edge in spec.edges:
        if edge.source not in node_ids:
            errors.append(f"边的起点 {edge.source} 不存在")

        if edge.target not in node_ids:
            errors.append(f"边的终点 {edge.target} 不存在")

        from_count[edge.source] = from_count.get(edge.source, 0) + 1
        to_count[edge.target] = to_count.get(edge.target, 0) + 1

    # 2. 检查 decision 节点是否至少有两个出口
    for node in spec.nodes:
        if node.kind == "decision":
            out_degree = from_count.get(node.id, 0)

            if out_degree < 2:
                errors.append(
                    f"判断节点 {node.id}（{node.text}）至少应该有两个出口，但当前只有 {out_degree} 个"
                )

    # 3. 检查孤立节点
    for node in spec.nodes:
        in_degree = to_count.get(node.id, 0)
        out_degree = from_count.get(node.id, 0)

        # 第一个节点可以没有入边，最后一个节点可以没有出边
        is_first_node = node.id == spec.nodes[0].id
        is_last_node = node.id == spec.nodes[-1].id

        if in_degree == 0 and out_degree == 0:
            errors.append(f"节点 {node.id}（{node.text}）是孤立节点，没有任何连线")

        elif in_degree == 0 and not is_first_node:
            warnings.append(f"节点 {node.id}（{node.text}）没有入边，可能不是正常起点")

        elif out_degree == 0 and not is_last_node and not is_terminal_node(node):
            warnings.append(f"节点 {node.id}（{node.text}）没有出边，可能提前中断")

    # 4. 检查“返回 / 重新输入 / 再次输入”是否真的有回边
    loop_keywords = [
        "返回",
        "重新输入",
        "再次输入",
        "回到",
        "重新验证",
        "重新登录",
    ]

    for node in spec.nodes:
        text = normalize_text(node.text)

        if any(keyword in text for keyword in loop_keywords):
            has_loop_edge = False

            for edge in spec.edges:
                label = getattr(edge, "label", "")

                if edge.source == node.id:
                    # 情况 1：有返回 label
                    if label == "返回":
                        has_loop_edge = True

                    # 情况 2：目标节点在当前节点前面，也认为是回边
                    source_index = next(
                        (i for i, n in enumerate(spec.nodes) if n.id == edge.source),
                        None,
                    )
                    target_index = next(
                        (i for i, n in enumerate(spec.nodes) if n.id == edge.target),
                        None,
                    )

                    if (
                        source_index is not None
                        and target_index is not None
                        and target_index < source_index
                    ):
                        has_loop_edge = True

            if not has_loop_edge:
                errors.append(
                    f"节点 {node.id}（{node.text}）包含返回/重新输入含义，但没有检测到回边"
                )

    return errors, warnings


def print_validation_result(errors, warnings):
    """
    打印校验结果。
    """

    if not errors and not warnings:
        print("\nBranch 流程校验通过")
        return

    if warnings:
        print("\nBranch 流程校验警告：")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\nBranch 流程校验错误：")
        for error in errors:
            print(f"- {error}")