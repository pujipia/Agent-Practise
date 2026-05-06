from ingest.document_loader import load_document

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

def read_user_input() -> str:
    """
    让用户选择输入方式：
    1. 手动输入多行自然语言流程
    2. 从 .txt / .md 文档读取流程描述
    """

    print("请选择输入方式：")
    print("1. 手动输入流程描述")
    print("2. 从 .txt / .md 文档读取")
    
    choice = input("请输入选项 1 或 2：").strip()

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

    return read_multiline_input() 