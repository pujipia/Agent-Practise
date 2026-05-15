def normalize_text(text):
    if text is None:
        return ""
    return str(text).replace(" ", "").replace("\n", "")


def has_edge(spec, source_id: str, target_id: str) -> bool:
    for edge in spec.edges:
        if edge.source == source_id and edge.target == target_id:
            return True
    return False

def is_return_node(node) -> bool:
    """
    判断一个节点是不是迴邊节点。
    迴邊节点应该返回前面的输入/操作节点，而不是连接到流程结束。
    """
    text = normalize_text(node.text)

    return_keywords = [
        "重新上传",
        "重新输入",
        "重新选择",
        "重新支付",
        "压缩文件后重新上传",
        "提示登录失败",
        "提示验证码错误",
        "补全",
        "修改",
    ]

    return any(keyword in text for keyword in return_keywords)

def is_terminal_node(node) -> bool:
    """
    判断一个节点是不是终止节点。
    终止节点应该连接到“流程结束”节点。
    """
    text = normalize_text(node.text)

    if is_rework_node(node):
        return False

    terminal_keywords = [
        "流程结束",
        "结束",
        "输出解析结果",
        "输出解析结果并保存文件信息",
        "保存文件信息",
        "进入系统首页",
        "进入主页",
        "登录成功",
        "锁定账号",
        "拒绝文件",
        "取消订单",
        "冻结订单",
        "终止申请",
        "转入人工审核队列",
        "通知用户订单已发货",
        "生成报告",
        "生成审查报告",
        "生成正常巡检报告",
        "生成异常告警",
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
        "返回输入",
        "返回输入阶段",
        "返回上一步",
        "返回上一阶段",
        "返回重新检查",
        "返回检查",
        "重新输入",
        "重新检查",
        "再次检查",
        "重新判断",
        "再次判断",
        "回到输入",
        "回到检查",
        "回到判断",
    ]

    for node in spec.nodes:
        text = normalize_text(node.text)

        if any(keyword in text for keyword in loop_keywords):
            has_loop_edge = False

            for edge in spec.edges:
                label = getattr(edge, "label", "") or ""

                if edge.source == node.id:
                    # 情况 1：有返回 label
                    if normalize_text(label) == "返回":
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