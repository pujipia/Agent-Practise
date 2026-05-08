from processors.flow_segmenter import split_flow_segments


def print_segments(title: str, text: str) -> None:
    """
    打印 split_flow_segments() 的测试结果。
    """
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    result = split_flow_segments(text)

    print(f"检测到 {len(result.flows)} 个流程")

    for segment in result.flows:
        print(f"\n{segment.id} - {segment.title}")
        print(segment.content)


single_flow_text = """
用户上传文件后，系统检查文件格式是否支持。
如果支持，则调用文件解析模块。
如果不支持，则提示用户重新上传。
"""

markdown_flow_text = """
# 登录流程

用户输入账号和密码。
系统检查登录信息是否完整。

# 文件上传流程

用户上传文件。
系统检查文件格式是否支持。
"""

named_flow_text = """
流程一：登录流程

用户输入账号和密码。
系统检查登录信息是否完整。

流程二：文件上传流程

用户上传文件。
系统检查文件格式是否支持。
"""

dash_flow_text = """
登录流程
用户输入账号和密码。
系统检查登录信息是否完整。

---

文件上传流程
用户上传文件。
系统检查文件格式是否支持。
"""


print_segments("Test 1：单流程输入", single_flow_text)
print_segments("Test 2：Markdown 标题多流程", markdown_flow_text)
print_segments("Test 3：流程一 / 流程二格式", named_flow_text)
print_segments("Test 4：--- 分隔线格式", dash_flow_text)