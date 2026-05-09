from typing import Any, Optional


def _normalize_text(text: Any) -> str:
    """
    将任意输入转换成统一的小写字符串。

    作用：
    1. 避免 None 导致报错
    2. 英文判断时不区分大小写
    3. 去掉空格和换行，方便匹配 not empty / notempty 这类表达
    """

    if text is None:
        return ""

    return str(text).lower().replace(" ", "").replace("\n", "")


def _get_items(obj: Any, field_name: str) -> list:
    """
    安全读取 Pydantic model 或 dict 中的列表字段。

    例如：
    1. decomposition_spec.flows
    2. decomposition_spec["flows"]
    """

    if obj is None:
        return []

    if isinstance(obj, dict):
        value = obj.get(field_name, [])
        return value if isinstance(value, list) else []

    value = getattr(obj, field_name, [])
    return value if isinstance(value, list) else []


def _get_attr(item: Any, field_name: str, default: str = "") -> str:
    """
    安全读取 Pydantic item 或 dict 中的字段。

    例如：
    1. flow.condition
    2. flow["condition"]
    """

    if item is None:
        return default

    if isinstance(item, dict):
        return item.get(field_name, default) or default

    return getattr(item, field_name, default) or default


def _has_branch_signal_in_user_input(user_input: str) -> bool:
    """
    判断原始输入中是否存在明显的分支语义。

    中文：
    如果 / 是否 / 判断 / 检查 / 成功失败 / 通过不通过

    英文：
    if / whether / check / validate / success / failure / pass / fail
    """

    normalized = _normalize_text(user_input)

    branch_keywords = [
        # Chinese
        "如果",
        "是否",
        "判断",
        "检查",
        "校验",
        "验证",
        "正确",
        "不正确",
        "通过",
        "不通过",
        "成功",
        "失败",
        "否则",
        "若",
        "条件",
        "为空",
        "不为空",
        "支持",
        "不支持",
        "完整",
        "不完整",
        "合法",
        "不合法",
        "需要",
        "不需要",

        # English
        "if",
        "whether",
        "check",
        "validate",
        "verify",
        "success",
        "failure",
        "pass",
        "fail",
        "otherwise",
        "condition",
        "empty",
        "notempty",
        "supported",
        "unsupported",
        "complete",
        "incomplete",
        "correct",
        "incorrect",
        "valid",
        "invalid",
        "required",
        "notrequired",
    ]

    return any(keyword in normalized for keyword in branch_keywords)


def _has_branch_condition_in_decomposition(decomposition_spec: Any) -> bool:
    """
    根据 Decomposition Agent 的 flows 判断是否存在分支条件。

    核心逻辑：
    如果 flows 里出现明显的 condition，例如：
    - 为空 / 不为空
    - 支持 / 不支持
    - 成功 / 失败
    - 通过 / 不通过
    - complete / incomplete
    - supported / unsupported

    则认为这是 branch。
    """

    flows = _get_items(decomposition_spec, "flows")

    branch_condition_keywords = [
        # Chinese
        "是",
        "否",
        "为空",
        "不为空",
        "支持",
        "不支持",
        "成功",
        "失败",
        "通过",
        "不通过",
        "完整",
        "不完整",
        "正确",
        "不正确",
        "合法",
        "不合法",
        "需要",
        "不需要",

        # English
        "yes",
        "no",
        "empty",
        "notempty",
        "supported",
        "unsupported",
        "success",
        "failure",
        "pass",
        "fail",
        "passed",
        "failed",
        "complete",
        "incomplete",
        "correct",
        "incorrect",
        "valid",
        "invalid",
        "required",
        "notrequired",
    ]

    for flow in flows:
        condition = _normalize_text(_get_attr(flow, "condition", ""))

        if not condition:
            continue

        if any(keyword in condition for keyword in branch_condition_keywords):
            return True

    return False


def _has_decision_in_decomposition(decomposition_spec: Any) -> bool:
    """
    根据 Decomposition Agent 的 decisions 判断是否存在判断节点。

    注意：
    这里只作为辅助判断。
    如果 Decomposition Agent 明确拆出了 decisions，
    通常说明输入中存在判断、检查、是否、if / whether 等结构。
    """

    decisions = _get_items(decomposition_spec, "decisions")

    if not decisions:
        return False

    decision_keywords = [
        # Chinese
        "是否",
        "判断",
        "检查",
        "验证",
        "校验",
        "能否",
        "是否需要",
        "是否可以",
        "是否成功",
        "是否通过",

        # English
        "whether",
        "check",
        "validate",
        "verify",
        "if",
        "success",
        "pass",
        "fail",
        "supported",
        "complete",
        "valid",
    ]

    for decision in decisions:
        question = _normalize_text(_get_attr(decision, "question", ""))
        description = _normalize_text(_get_attr(decision, "description", ""))

        combined_text = question + description

        if any(keyword in combined_text for keyword in decision_keywords):
            return True

    return False


def _has_branch_signal_in_concepts(concept_spec: Any) -> bool:
    """
    根据 Research Agent 的 concepts 辅助判断是否存在分支信号。

    如果 concepts 里出现 decision 类型，说明可能是 branch。
    这一步不是主判断，只作为兜底增强。
    """

    concepts = _get_items(concept_spec, "concepts")

    for concept in concepts:
        concept_type = _normalize_text(_get_attr(concept, "type", ""))

        if concept_type == "decision":
            return True

    return False


def route_flow_type(
    user_input: str,
    concept_spec: Optional[Any] = None,
    decomposition_spec: Optional[Any] = None,
) -> str:
    """
    根据原始输入、Research Agent 结果和 Decomposition Agent 结果判断流程类型。

    返回：
    - "linear"：普通线性流程
    - "branch"：带判断、条件、成功失败、通过不通过等分支结构的流程

    当前 Router 不处理 topology / unsupported。
    """

    # 1. 优先根据原始输入判断
    if _has_branch_signal_in_user_input(user_input):
        return "branch"

    # 2. 再根据 Decomposition Agent 的 flows.condition 判断
    if _has_branch_condition_in_decomposition(decomposition_spec):
        return "branch"

    # 3. 再根据 Decomposition Agent 的 decisions 辅助判断
    if _has_decision_in_decomposition(decomposition_spec):
        return "branch"

    # 4. 最后根据 Research Agent concepts 兜底判断
    if _has_branch_signal_in_concepts(concept_spec):
        return "branch"

    # 5. 默认线性流程
    return "linear"