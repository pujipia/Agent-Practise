from pathlib import Path


def load_document(path: str) -> str:
    """
    读取 .txt / .md 文档内容，并返回字符串。
    当前阶段只支持纯文本和 Markdown，暂不处理 PDF / Word。
    """

    file_path = Path(path).expanduser()

    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    if not file_path.is_file():
        raise ValueError(f"路径不是文件：{file_path}")

    if file_path.suffix.lower() not in [".txt", ".md"]:
        raise ValueError("当前只支持 .txt 和 .md 文件。")

    text = file_path.read_text(encoding="utf-8").strip()

    if not text:
        raise ValueError("文档内容为空。")

    return text