def clean_step_text(text: str) -> str:
    remove_phrases = [
        "起点是",
        "起点为",
        "开始是",
        "从",
        "首先",
        "第一步",
        "然后到",
        "然后",
        "接着",
        "随后",
        "再",
        "终点是",
        "终点为",
        "结束是",
        "最后是",
        "最后",
        "最终",
        "就可以了",
        "即可",
    ]

    cleaned = text.strip()

    for phrase in remove_phrases:
        cleaned = cleaned.replace(phrase, "")

    return cleaned.strip(" ，,。.")
    #Purpose: delete the word which describe the connection and remain the description of flow