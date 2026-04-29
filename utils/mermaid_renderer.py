#import python for automatically generate .png/.svg
import shutil
import subprocess
from pathlib import Path


def render_mermaid_to_image(input_path: Path, output_path: Path) -> bool:
    """
    使用 Mermaid CLI 把 .mmd 文件渲染成 .svg / .png / .pdf。
    """

    mmdc_cmd = shutil.which("mmdc.cmd") or shutil.which("mmdc")

    if not mmdc_cmd:
        print("\n未找到 mmdc 命令，请确认 Mermaid CLI 已安装。")
        return False

    puppeteer_config = Path("puppeteer-config.json")

    cmd = [
        mmdc_cmd,
        "-i",
        str(input_path),
        "-o",
        str(output_path),
    ]

    if puppeteer_config.exists():
        cmd.extend(["-p", str(puppeteer_config)])

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        print(f"\n已生成图片：{output_path}")
        return True

    except subprocess.CalledProcessError as e:
        print("\nMermaid 图片生成失败。")

        if e.stdout:
            print("\n标准输出：")
            print(e.stdout)

        if e.stderr:
            print("\n错误输出：")
            print(e.stderr)

        return False