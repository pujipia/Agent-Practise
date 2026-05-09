from ingest.document_loader import load_document
from typing import Optional

def read_multiline_input() -> str:
    print("请输入流程描述。")
    print("可以输入多行内容，输入完成后，单独输入 END 结束：")

    lines = [] #存储用户输入

    while True:
        line = input() #一直遍历输入，直到主动BREAK

        if line.strip() == "END":
            break

        lines.append(line) #如果输入不是END，就保存在lines中

    return "\n".join(lines).strip()  # .strip()去掉前后空格; "\n".join(lines)将多行内容重新拼接成完整字符串

def read_user_input() -> Optional[str]:
    """
    让用户选择输入方式：
    1. 手动输入多行自然语言流程
    2. 从 .txt / .md 文档读取流程描述
    3. 运行内置回归测试
    """

    print("请选择输入方式：")
    print("1. 手动输入流程描述")
    print("2. 从 .txt / .md 文档读取")
    print("3. 运行内置回归测试")

    choice = input("请输入选项 1、2 或 3：").strip()

    # ------------------------------------------------------------
    # 选项 3：运行内置回归测试
    # ------------------------------------------------------------
    if choice == "3":
        # 放在函数内部 import，可以避免不必要的启动加载，
        # 也能降低循环 import 的风险。
        from tests.regression_runner import run_builtin_regression_tests

        run_builtin_regression_tests()

        # 返回空字符串，告诉 main.py：
        # 这次只是跑测试，任务到此已经跑完，不需要继续生成流程图。
        return None

    # ------------------------------------------------------------
    # 选项 2：从 .txt / .md 文件读取流程描述
    # ------------------------------------------------------------
    if choice == "2":
        file_path = input("请输入文档路径：").strip().strip('"').strip("'")
        user_input = load_document(file_path)

        print("\n文档读取成功，内容预览如下：")
        print("-" * 50)
        print(user_input[:1000])
        print("-" * 50)

        confirm = input("是否继续生成流程图？[y/n]: ").strip().lower()

        if confirm != "y":
            print("已取消。")
            return ""

        return user_input

    # ------------------------------------------------------------
    # 选项 1：手动输入流程描述
    # ------------------------------------------------------------
    if choice == "1":
        return read_multiline_input()

    # ------------------------------------------------------------
    # 其他输入：提示错误，并返回空字符串
    # ------------------------------------------------------------
    print("无效选项，已取消。")
    return ""