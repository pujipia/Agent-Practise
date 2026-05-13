from ingest.document_loader import load_document
from typing import Optional
from pathlib import Path

def read_multiline_input() -> str:
    """
    手动输入多行流程描述。

    支持：
    1. 多行输入
    2. 单独输入 END 结束
    3. 第一行输入 0 返回主菜单
    4. 直接输入 END / 空内容时返回空字符串
    5. Ctrl + C 时友好退出
    """

    print("\n请输入流程描述。")
    print("支持多行输入，输入完成后请单独输入 END 结束。")
    print("输入 0 可以返回主菜单。")
    print("\n示例：")
    print("用户上传文件。")
    print("系统检查文件格式是否支持。")
    print("如果支持，则调用文件解析模块。")
    print("如果不支持，则提示用户重新上传。")
    print("END")
    print("\n请输入：")

    lines = [] #存储用户输入

    try:
        while True:
            line = input()

            # 第一行输入 0：返回主菜单
            if not lines and line.strip() == "0":
                print("\n已取消手动输入，返回主菜单。")
                return ""

            # 单独输入 END：结束输入
            if line.strip().upper() == "END":
                break

            lines.append(line)

    except KeyboardInterrupt:
        raise

    user_input = "\n".join(lines).strip()

    return user_input

def ask_yes_no(prompt: str) -> bool:
    """
    统一处理 y/n 输入。

    返回：
    - True: 用户输入 y / yes / Y
    - False: 用户输入 n / no / N

    作用：
    避免用户输入其他内容时程序直接退出。
    """

    while True:
        answer = input(prompt).strip().lower()

        if answer in ("y", "yes", "Y"):
            return True

        if answer in ("n", "no", "N"):
            return False

        print("请输入 y 或 n。")

def read_user_input() -> Optional[str]:
    """
    让用户选择输入方式：
    0. 退出程序
    1. 手动输入多行自然语言流程
    2. 从 .txt / .md 文档读取流程描述
    3. 运行内置回归测试

    返回：
    - str: 用户输入或文档内容
    - None: 用户选择退出 / 取消 / 已完成自测试
    """

    while True:
        print("\n" + "=" * 60)
        print(" File Agent Flowchart Generator")
        print("=" * 60)
        print("\n请选择运行模式：")
        print("[1] 手动输入流程描述")
        print("[2] 从 .txt / .md 文档读取")
        print("[3] 运行内置回归测试")
        print("[4] 更改日志模式")
        print("[0] 退出程序")

        try:
            choice = input("\n请输入选项 0 / 1 / 2 / 3 / 4：").strip()
        except KeyboardInterrupt:
            raise

        # ------------------------------------------------------------
        # 选项 0：退出程序
        # ------------------------------------------------------------
        if choice == "0":
            return None

        # ------------------------------------------------------------
        # 选项 1：手动输入流程描述
        # ------------------------------------------------------------
        if choice == "1":
            print("\n已选择：手动输入流程描述。")

            user_input = read_multiline_input()

            # Ctrl + C 中断：直接结束程序
            if user_input is None:
                return None

            # 输入 0 / 直接 END / 空内容：返回主菜单
            if user_input.strip() == "":
                print("\n未输入有效流程描述，返回主菜单。")
                continue

            print("\n已接收手动输入，准备生成流程图...")
            return user_input

        # ------------------------------------------------------------
        # 选项 2：从 .txt / .md 文件读取流程描述
        # ------------------------------------------------------------
        if choice == "2":
            print("\n已选择：从文档读取流程描述。")
            print("当前仅支持 .txt 和 .md 文件。")
            print("输入 0 可以返回主菜单。")

            while True:
                file_path_text = input("\n请输入 .txt 或 .md 文档路径：").strip().strip('"').strip("'")

                # 用户输入 0：返回主菜单
                if file_path_text == "0":
                    print("\n已返回主菜单。")
                    break

                # 路径为空：重新输入
                if not file_path_text:
                    print("\n文件路径不能为空，请重新输入。")
                    continue

                file_path = Path(file_path_text)

                # 检查文件格式,取得文件后缀并且同意转成小写
                if file_path.suffix.lower() not in [".txt", ".md"]:
                    print("\n文件格式不支持。")
                    print(f"当前文件类型：{file_path.suffix or '无后缀'}")
                    print("当前仅支持 .txt 和 .md 文件。")

                    retry = ask_yes_no("是否重新输入文件路径？[y/n]: ")

                    if retry:
                        continue

                    print("\n已取消本次文件读取，返回主菜单。")
                    break

                # 检查文件是否存在
                if not file_path.exists():
                    print("\n文件读取失败：找不到该文件。")
                    print("请检查：")
                    print("1. 文件路径是否正确")
                    print("2. 文件名是否包含空格或特殊符号")
                    print("3. 是否需要使用引号包裹路径")

                    retry = ask_yes_no("是否重新输入文件路径？[y/n]: ")

                    if retry:
                        continue

                    print("\n已取消本次文件读取，返回主菜单。")
                    break

                # 尝试读取文件
                try:
                    user_input = load_document(str(file_path))

                except Exception as error:
                    print("\n文件读取失败。")
                    print(f"错误信息：{error}")

                    retry = ask_yes_no("是否重新输入文件路径？[y/n]: ")

                    if retry:
                        continue

                    print("\n已取消本次文件读取，返回主菜单。")
                    break

                # 文件读取成功
                print("\n文档读取成功。")
                print(f"文件路径：{file_path}")
                print("\n内容预览：")
                print("-" * 50)
                print(user_input[:1000])
                print("-" * 50)

                confirm = ask_yes_no("\n是否继续生成流程图？[y/n]: ")

                if not confirm:
                    print("\n已取消本次生成，返回主菜单。")
                    break

                print("\n已确认，准备生成流程图...")
                return user_input

            # 从文件读取模式返回主菜单
            continue

        # ------------------------------------------------------------
        # 选项 3：运行内置回归测试
        # ------------------------------------------------------------
        if choice == "3":
            print("\n已选择：运行内置回归测试。")

            confirm = input("是否开始测试？[y/n]: ").strip().lower()

            if confirm != "y":
                print("\n已取消内置回归测试，返回主菜单。")
                continue

            try:
                from tests.regression_runner import run_builtin_regression_tests

                run_builtin_regression_tests()

            except KeyboardInterrupt:
                raise

            return None
        
        if choice == "4":
            return "__CHANGE_LOGGING_MODE__"

        # ------------------------------------------------------------
        # 无效输入：重新提示，而不是直接退出
        # ------------------------------------------------------------
        print(f"\n无效选项：{choice}")
        print("请输入 0、1、2 或 3。")