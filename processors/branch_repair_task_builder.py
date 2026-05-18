from typing import Any, List
MAX_REPAIR_TASKS = 5

def build_repair_tasks(errors: list[str]) -> str:
    """
    将 validator errors 转换成 retry prompt 中更清晰的 repair tasks。

    当前第一版只做文本整理，不直接改图。
    """

    if not errors:
        return "无。"

    task_lines = []

    for index, error in enumerate(errors[:MAX_REPAIR_TASKS], start=1):
        task_lines.append(f"Task {index}:")
        task_lines.append(f"错误来源：{error}")

        if "Decomposition decision 未被 Branch 图覆盖" in error:
            task_lines.append("修复类型：补充缺失 decision 节点")
            task_lines.append("修复要求：")
            task_lines.append("- 在 nodes 中新增或保留该 decision 节点")
            task_lines.append("- kind 必须是 decision")
            task_lines.append("- 必须根据相关 flows 补全入边和出边")

        elif "Decomposition decision flow 未被 Branch 图覆盖" in error:
            task_lines.append("修复类型：补充缺失 flow edge")
            task_lines.append("修复要求：")
            task_lines.append("- 找到 flow source 对应节点")
            task_lines.append("- 找到 flow target 对应节点")
            task_lines.append("- 在 edges 中补充 source -> target")
            task_lines.append("- 如果 condition 存在，edge.label 使用 condition 核心语义")

        elif "edge.label 不匹配" in error:
            task_lines.append("修复类型：修正 edge.label")
            task_lines.append("修复要求：")
            task_lines.append("- 保留原 source 和 target")
            task_lines.append("- 只修改 label，使其匹配 Decomposition flow condition")

        elif "至少应该有两个出口" in error:
            task_lines.append("修复类型：补充分支出口")
            task_lines.append("修复要求：")
            task_lines.append("- 不要删除该 decision")
            task_lines.append("- 根据 Decomposition flows 补齐缺失出口")

        elif "孤立节点" in error:
            task_lines.append("修复类型：连接孤立节点")
            task_lines.append("修复要求：")
            task_lines.append("- 根据 Decomposition flows 找到该节点的前驱或后继")
            task_lines.append("- 补充缺失 edge")

        elif "像是分支结果" in error:
            task_lines.append("修复类型：判断结果节点修正")
            task_lines.append("修复要求：")
            task_lines.append("- 删除或避免生成该结果型 decision 节点")
            task_lines.append("- 该文本只能作为 edge.label")
            task_lines.append("- 必须保留或恢复真正的判断节点，判断节点通常包含“是否 / 能否 / 判断 / 检查”等词")
            task_lines.append("- 例如“库存充足 / 库存不足”不能作为 decision；应使用“库存是否充足”作为 decision")
            task_lines.append("- 例如“支付成功 / 支付失败”不能作为 decision；应使用“支付是否成功”作为 decision")
            task_lines.append("- 例如“风控通过 / 风控不通过”不能作为 decision；应使用“风控是否通过”作为 decision")

        else:
            task_lines.append("修复类型：普通结构修复")
            task_lines.append("修复要求：根据错误描述做最小修改")

        task_lines.append("")

    return "\n".join(task_lines)