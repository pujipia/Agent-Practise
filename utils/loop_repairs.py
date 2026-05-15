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
    自动修复明确的 return / 回边。

    设计原则：
    1. 只修复“明确表示返回 / 重新输入 / 重新上传 / 补全后返回”的节点。
    2. 不把所有失败、不通过、无效路径都默认改成 return。
    3. 不对 decision 节点自动补 return 边，避免把“是否重新支付”这类判断节点错误压缩成回边。
    4. 对模型已经生成的后向边，只在 source 节点有明确 return 语义时，才补 label="返回"。
    """

    # ============================================================
    # Part 1. return 关键词配置
    # 作用：
    # 1. 明确哪些 source 节点可以被认为是 return 节点
    # 2. 避免把“失败 / 无效 / 不通过 / 提示”误判为 return
    # ============================================================

    ACCOUNT_RETURN_KEYWORDS = [
        "重新输入账号",
        "重新输入账户",
        "重新输入用户名",
        "重新输入账号密码",
        "返回重新输入账号密码",
        "重新登录",
    ]

    PASSWORD_RETURN_KEYWORDS = [
        "重新输入密码",
        "返回重新输入密码",
    ]

    CAPTCHA_RETURN_KEYWORDS = [
        "重新输入验证码",
        "返回验证码",
        "再次输入验证码",
        "提示验证码错误",
    ]

    FILE_UPLOAD_RETURN_KEYWORDS = [
        "重新上传",
        "重新上传文件",
        "返回上传",
        "返回重新上传",
        "压缩文件后重新上传",
    ]

    ORDER_SUBMIT_RETURN_KEYWORDS = [
        "补全订单信息",
        "重新提交订单",
        "返回提交订单",
        "返回用户提交订单",
    ]

    GENERAL_RETURN_KEYWORDS = [
        "返回上一步",
        "回到上一步",
        "退回修改",
        "补充材料",
    ]

    EXPLICIT_RETURN_KEYWORDS = (
        ACCOUNT_RETURN_KEYWORDS
        + PASSWORD_RETURN_KEYWORDS
        + CAPTCHA_RETURN_KEYWORDS
        + FILE_UPLOAD_RETURN_KEYWORDS
        + ORDER_SUBMIT_RETURN_KEYWORDS
        + GENERAL_RETURN_KEYWORDS
    )

    def has_any_keyword(text, keywords):
        """
        判断 text 中是否包含任一关键词。
        """
        return any(keyword in text for keyword in keywords)

    def is_explicit_return_source(text):
        """
        判断 source 节点文本是否具有明确 return 语义。

        注意：
        这里故意不包含：
        - 失败
        - 无效
        - 不通过
        - 提示

        因为这些词不一定代表 return。
        """
        return has_any_keyword(text, EXPLICIT_RETURN_KEYWORDS)

    # ============================================================
    # Part 2. 根据节点文本补充缺失的 return 边
    # 作用：
    # 1. 处理模型没有生成回边的情况
    # 2. 只处理明确 return 语义节点
    # ============================================================

    for node in spec.nodes:
        text = normalize_text(node.text)
        kind = getattr(node, "kind", "")

        # 不对 decision 节点自动补 return 边。
        # 例如“用户是否选择重新支付”应该保留为 decision，
        # 不能被压缩成“返回支付模块”。
        if kind == "decision":
            continue

        # 情况 1：返回重新输入账号密码 / 重新登录 / 重新输入账户
        if has_any_keyword(text, ACCOUNT_RETURN_KEYWORDS):
            target_id = find_target_node(
                spec,
                ["输入账号", "输入账户", "输入用户名", "账号密码", "账户密码", "重新登录"]
            )

            if target_id and target_id != node.id and not has_edge(spec, node.id, target_id):
                spec.edges.append(
                    make_edge_like_existing(spec, node.id, target_id, label="返回")
                )

        # 情况 2：重新输入密码
        elif has_any_keyword(text, PASSWORD_RETURN_KEYWORDS):
            target_id = find_target_node(
                spec,
                ["输入密码", "账号密码", "账户密码", "重新登录"]
            )

            if target_id and target_id != node.id and not has_edge(spec, node.id, target_id):
                spec.edges.append(
                    make_edge_like_existing(spec, node.id, target_id, label="返回")
                )

        # 情况 3：重新输入验证码
        elif has_any_keyword(text, CAPTCHA_RETURN_KEYWORDS):
            target_id = find_target_node(
                spec,
                ["输入验证码", "验证码验证", "进入验证码", "发送验证码"]
            )

            if target_id and target_id != node.id and not has_edge(spec, node.id, target_id):
                spec.edges.append(
                    make_edge_like_existing(spec, node.id, target_id, label="返回")
                )

        # 情况 4：重新上传文件
        elif has_any_keyword(text, FILE_UPLOAD_RETURN_KEYWORDS):
            target_id = find_target_node(
                spec,
                ["用户上传文件", "上传文件", "文件上传"]
            )

            if target_id and target_id != node.id and not has_edge(spec, node.id, target_id):
                spec.edges.append(
                    make_edge_like_existing(spec, node.id, target_id, label="返回")
                )

        # 情况 5：补全订单信息后返回订单提交
        elif has_any_keyword(text, ORDER_SUBMIT_RETURN_KEYWORDS):
            target_id = find_target_node(
                spec,
                ["用户提交订单", "提交订单", "订单提交"]
            )

            if target_id and target_id != node.id and not has_edge(spec, node.id, target_id):
                spec.edges.append(
                    make_edge_like_existing(spec, node.id, target_id, label="返回")
                )

        # 情况 6：明确写了返回上一步 / 回到上一步
        elif has_any_keyword(text, GENERAL_RETURN_KEYWORDS):
            current_index = spec.nodes.index(node)

            if current_index > 0:
                target_id = spec.nodes[current_index - 1].id

                if target_id != node.id and not has_edge(spec, node.id, target_id):
                    spec.edges.append(
                        make_edge_like_existing(spec, node.id, target_id, label="返回")
                    )

    # ============================================================
    # Part 3. 补充已有回边的 label
    # 作用：
    # 1. 如果模型已经生成了后向边，但没有 label
    # 2. 只有 source 节点明确具有 return 语义时，才补 label="返回"
    # 3. 避免把普通共享节点 / 普通后向布局误标为 return
    # ============================================================

    node_index = {
        node.id: index
        for index, node in enumerate(spec.nodes)
    }

    node_text_by_id = {
        node.id: normalize_text(node.text)
        for node in spec.nodes
    }

    for edge in spec.edges:
        source_index = node_index.get(edge.source)
        target_index = node_index.get(edge.target)

        if source_index is None or target_index is None:
            continue

        label = (getattr(edge, "label", "") or "").strip()

        # 已经有 label 的边不在这里改。
        # 例如模型已经生成 label="返回"，这里不负责删除。
        if label:
            continue

        # 只有后向边才可能需要补“返回”。
        if target_index >= source_index:
            continue

        source_text = node_text_by_id.get(edge.source, "")

        # 关键变化：
        # 旧逻辑：只要 target_index < source_index 且没有 label，就补“返回”
        # 新逻辑：必须 source 节点文本本身具有明确 return 语义，才补“返回”
        if is_explicit_return_source(source_text):
            edge.label = "返回"

    return spec
def remove_invalid_end_back_edges(branch_diagram):
    """
    删除错误的“结束”回边。

    适用场景：
    L -->|结束| A

    这种边通常是模型为了避免空 target，
    把“结束”错误地连回了起点。
    """

    edges = branch_diagram.edges

    branch_diagram.edges = [
        edge
        for edge in edges
        if not (
            edge.label == "结束"
            and edge.target == branch_diagram.nodes[0].id
        )
    ]

    return branch_diagram