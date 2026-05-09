from typing import Any, Optional


def _normalize_text(text: Any) -> str:
    """
    将任意输入转换成统一的小写字符串。

    作用：
    1. 避免 None 报错
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
    判断原始输入中是否存在明显的“结构性分支语义”。

    注意：
    不要把“成功 / 失败 / 支持 / 不支持 / 完整 / 不完整”这类结果词
    单独作为 user_input 的 branch 判断依据。

    原因：
    “系统显示提交成功信息”是线性输出，不是分支判断。
    """

    normalized = _normalize_text(user_input)

    branch_keywords = [
        # Chinese structural branch signals
        "如果",
        "是否",
        "判断",
        "检查",
        "校验",
        "验证",
        "否则",
        "若",
        "能否",

        # English structural branch signals
        "if",
        "whether",
        "check",
        "validate",
        "verify",
        "otherwise",
    ]

    return any(keyword in normalized for keyword in branch_keywords)


def _has_branch_condition_in_decomposition(decomposition_spec: Any) -> bool:
    """
    根据 Decomposition Agent 的 flows.condition 判断是否存在真正的分支条件。

    注意：
    不能只要 condition 非空就判断为 branch。

    例如：
    - 无条件
    - none
    - no condition
    - unconditional

    这些都不是分支。
    """

    flows = _get_items(decomposition_spec, "flows")

    neutral_conditions = [
        "",
        "无",
        "无条件",
        "none",
        "nocondition",
        "no条件",
        "unconditional",
        "n/a",
        "na",
    ]

    branch_condition_keywords = [
        # Chinese branch outcomes
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
        "为true",
        "为false",
        "true",
        "false",

        # English branch outcomes
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

        # 明确排除“无条件”
        if condition in neutral_conditions:
            continue

        if any(keyword in condition for keyword in branch_condition_keywords):
            return True

    return False


def route_flow_type(
    user_input: str,
    concept_spec: Optional[Any] = None,
    decomposition_spec: Optional[Any] = None,
) -> str:
    """
    根据原始输入和 Decomposition flows.condition 判断流程类型。

    返回：
    - "linear"
    - "branch"

    当前 Router 不处理 topology / unsupported。
    """

    # 1. 原始输入中有明确结构性分支词，才判断为 branch
    if _has_branch_signal_in_user_input(user_input):
        return "branch"

    # 2. Decomposition flows.condition 中有真实分支结果，才判断为 branch
    if _has_branch_condition_in_decomposition(decomposition_spec):
        return "branch"

    # 3. 默认 linear
    return "linear"

def route_flow_type(
    user_input: str,
    concept_spec: Optional[Any] = None,
    decomposition_spec: Optional[Any] = None,
) -> str:
    if _has_branch_signal_in_user_input(user_input):
        return "branch"

    if _has_branch_condition_in_decomposition(decomposition_spec):
        return "branch"

    return "linear"