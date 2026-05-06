#This code is aim to  judge whether the Input should be put in linear flow or in branch flow
def route_flow_type(user_input: str) -> str:
    """
    根据用户输入判断流程类型。

    返回：
    - "linear"：普通线性流程
    - "branch"：带判断分支的流程
    """

    branch_keywords = [
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
    ]

    if any(keyword in user_input for keyword in branch_keywords):
        return "branch"

    return "linear"