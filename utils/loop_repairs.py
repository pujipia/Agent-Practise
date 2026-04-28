import re


def normalize_text(text: str) -> str:
    """
    简单清理文本，方便做关键词匹配。
    """
    return text.replace(" ", "").replace("\n", "")


def has_edge(spec, source_id: str, target_id: str) -> bool:
    """
    检查某条边是否已经存在，避免重复添加。
    """
    for edge in spec.edges:
        if edge.source == source_id and edge.target == target_id:
            return True
    return False


def make_edge_like_existing(spec, source_id: str, target_id: str, label: str = ""):
    """
    根据现有 edge 的类型创建新 edge。
    这样可以避免不知道你的 Edge 类具体叫什么的问题。
    """
    if spec.edges:
        EdgeClass = spec.edges[0].__class__

        try:
            return EdgeClass(source=source_id, target=target_id, label=label)
        except Exception:
            pass

        try:
            return EdgeClass(source=source_id, target=target_id)
        except Exception:
            pass

    raise ValueError("无法创建新的 edge，请检查 Edge 模型字段是否为 source / target / label")


def find_target_node(spec, keywords):
    """
    根据关键词寻找要返回的目标节点。
    """
    for node in spec.nodes:
        text = normalize_text(node.text)
        if any(keyword in text for keyword in keywords):
            return node.id

    return None


def repair_loop_edges(spec):
    """
    自动修复循环边。

    例如：
    C: 提示错误并返回重新输入账号密码
    自动补：
    C --> A

    G: 重新输入验证码
    自动补：
    G --> D
    """

    for node in spec.nodes:
        text = normalize_text(node.text)

        # 情况 1：返回重新输入账号密码 / 重新登录 / 重新输入账户
        if any(keyword in text for keyword in ["重新输入账号", "重新输入账户", "重新输入用户名", "重新输入账号密码", "返回重新输入账号密码", "重新登录"]):
            target_id = find_target_node(
                spec,
                ["输入账号", "输入账户", "输入用户名", "账号密码", "账户密码", "登录"]
            )

            if target_id and target_id != node.id and not has_edge(spec, node.id, target_id):
                spec.edges.append(make_edge_like_existing(spec, node.id, target_id, label="返回"))

        # 情况 2：重新输入密码
        elif any(keyword in text for keyword in ["重新输入密码", "返回重新输入密码"]):
            target_id = find_target_node(
                spec,
                ["输入密码", "账号密码", "账户密码", "登录"]
            )

            if target_id and target_id != node.id and not has_edge(spec, node.id, target_id):
                spec.edges.append(make_edge_like_existing(spec, node.id, target_id, label="返回"))

        # 情况 3：重新输入验证码
        elif any(keyword in text for keyword in ["重新输入验证码", "返回验证码", "再次输入验证码"]):
            target_id = find_target_node(
                spec,
                ["验证码验证", "输入验证码", "进入验证码"]
            )

            if target_id and target_id != node.id and not has_edge(spec, node.id, target_id):
                spec.edges.append(make_edge_like_existing(spec, node.id, target_id, label="返回"))

        # 情况 4：比较宽泛的“返回上一步”
        elif any(keyword in text for keyword in ["返回上一步", "回到上一步", "重新操作", "再次操作"]):
            current_index = spec.nodes.index(node)

            if current_index > 0:
                target_id = spec.nodes[current_index - 1].id

                if target_id != node.id and not has_edge(spec, node.id, target_id):
                    spec.edges.append(make_edge_like_existing(spec, node.id, target_id, label="返回"))

    return spec