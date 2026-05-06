from pathlib import Path #import a tool called "Path"


def load_prompt(relative_path: str) -> str:
    """
    从项目根目录读取 Prompt 模板文件。

    relative_path 示例：
    prompts/flowchart/branch_flow.md
    """
    project_root = Path(__file__).resolve().parents[1]
    prompt_path = project_root / relative_path

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8")