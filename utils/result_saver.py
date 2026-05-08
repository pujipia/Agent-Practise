import json  #把 Python 字典转换成 JSON 字符串
from pathlib import Path
from typing import Any #表示这个函数可以接收任意类型的数据

#通用保存函数
def save_json_result(data: Any, output_path: str | Path) -> Path:
    """
    将 Python 对象或 Pydantic model 保存为 JSON 文件。
    """

    output_path = Path(output_path)

    # 如果目标文件夹不存在，自动创建
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果 data 是 Pydantic model，先转成 dict
    if hasattr(data, "model_dump"):
        data = data.model_dump()

    # 写入 JSON 文件，ensure_ascii=False 用于正常保存中文
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def save_research_result(
    concept_spec: Any,
    output_prefix: str = "latest",
) -> Path:
    """
    保存 Research Agent 的 concepts 结果。

    output_prefix 用于区分不同流程。
    例如：
    flow_01_research_concepts.json
    flow_02_research_concepts.json
    """

    return save_json_result(
        concept_spec,
        Path("artifacts") / f"{output_prefix}_research_concepts.json",
    )


def save_decomposition_result(
    decomposition_spec: Any,
    output_prefix: str = "latest",
) -> Path:
    """
    保存 Decomposition Agent 的 decomposition 结果。

    output_prefix 用于区分不同流程。
    例如：
    flow_01_decomposition.json
    flow_02_decomposition.json
    """

    return save_json_result(
        decomposition_spec,
        Path("artifacts") / f"{output_prefix}_decomposition.json",
    )