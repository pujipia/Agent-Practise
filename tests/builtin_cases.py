#存放测试题和标准答案

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass  #自动帮助生成__init__()
class BuiltinTestCase:
    """
    内置回归测试用例。

    字段说明：
    - name: 测试名称
    - input_text: 测试输入文本
    - expected_flow_type: 预期 Router 判断结果，linear 或 branch
    - must_have_node_texts: 最终图中必须出现的节点文本
    - must_have_edge_labels: 最终图中必须出现的边标签
    - must_have_edges: 最终图中必须出现的边，格式为：
      (source_node_text, target_node_text)
    """

    name: str
    input_text: str
    expected_flow_type: str
    must_have_node_texts: List[str] = field(default_factory=list) #自动给一个空列表
    must_have_edge_labels: List[str] = field(default_factory=list)
    must_have_edges: List[Tuple[str, str]] = field(default_factory=list)
    #Use tuple (two strings) to describe an edge (Source and Target)

BUILTIN_TEST_CASES = [
    BuiltinTestCase(
        name="TEST1 中文线性流程：订单提交",
        input_text=(
            "用户提交订单。"
            "系统接收订单信息。"
            "系统保存订单数据。"
            "系统生成订单编号。"
            "系统向用户显示订单提交成功信息。"
            "流程结束。"
        ),
        expected_flow_type="linear",
        must_have_node_texts=[
            "用户提交订单",
            "系统接收订单信息",
            "系统保存订单数据",
            "系统生成订单编号",
            "系统向用户显示订单提交成功信息",
        ],
    ),
    BuiltinTestCase(
        name="TEST2 中文简单分支流程：文件上传",
        input_text=(
            "用户上传文件。"
            "系统检查文件格式是否支持。"
            "如果文件格式支持，则调用文件解析模块。"
            "如果文件格式不支持，则提示用户重新上传文件。"
            "文件解析完成后，系统输出解析结果。"
            "流程结束。"
        ),
        expected_flow_type="branch",
        must_have_node_texts=[
            "用户上传文件",
            "文件格式是否支持",
            "调用文件解析模块",
            "提示用户重新上传文件",
            "输出解析结果",
        ],
        must_have_edge_labels=[
            "支持",
            "不支持",
        ],
    ),
    BuiltinTestCase(
        name="TEST3 中文带返回分支流程：登录验证",
        input_text=(
            "用户输入账号和密码。"
            "系统检查账号和密码是否为空。"
            "如果账号或密码为空，则提示用户重新输入，并返回账号密码输入步骤。"
            "如果账号和密码不为空，则调用登录验证模块。"
            "系统判断登录是否成功。"
            "如果登录失败，则提示登录失败，并返回账号密码输入步骤。"
            "如果登录成功，则进入系统首页。"
            "流程结束。"
        ),
        expected_flow_type="branch",
        must_have_node_texts=[
            "用户输入账号",
            "密码是否为空",
            "重新输入",
            "登录验证模块",
            "登录是否成功",
            "登录失败",
            "系统首页",
        ],
        must_have_edge_labels=[
            "为空",
            "不为空",
            "失败",
            "成功",
            "返回",
        ],
    ),
    BuiltinTestCase(
        name="TEST4 English Simple Branch Flow: File Upload",
        input_text=(
            "The user uploads a file. "
            "The system checks whether the file format is supported. "
            "If the file format is supported, the system calls the file parsing module. "
            "If the file format is not supported, the system asks the user to upload the file again. "
            "After the file is parsed, the system outputs the parsing result. "
            "The process ends."
        ),
        expected_flow_type="branch",
    ),
    BuiltinTestCase(
        name="TEST5 English Simple Branch Flow: Login",
        input_text=(
            "The user enters a username and password. "
            "The system checks whether the login information is complete. "
            "If the login information is incomplete, the system asks the user to enter the information again. "
            "If the login information is complete, the system calls the authentication module. "
            "The system checks whether authentication is successful. "
            "If authentication fails, the system displays a login failure message. "
            "If authentication succeeds, the system enters the dashboard. "
            "The process ends."
        ),
        expected_flow_type="branch",
    ),
    BuiltinTestCase(
        name="TEST6 Agent Pipeline Flow",
        input_text=(
            "用户输入流程描述或上传文档。"
            "系统判断输入内容是否为空。"
            "如果输入为空，则提示用户重新输入。"
            "如果输入不为空，则调用 Flow Segmenter 切分流程。"
            "系统判断是否检测到多个流程。"
            "如果检测到多个流程，则逐个处理每个流程片段。"
            "如果只检测到一个流程，则直接处理默认流程。"
            "系统调用 Research Agent 抽取关键概念。"
            "系统判断 concepts 是否为空。"
            "如果 concepts 为空，则触发 retry 重新抽取。"
            "如果 concepts 不为空，则调用 Decomposition Agent 进行系统拆解。"
            "系统调用 Router 判断流程类型。"
            "如果流程类型是 linear，则调用 linear rule extractor。"
            "如果流程类型是 branch，则调用 branch flow extractor。"
            "如果流程类型不支持，则提示暂不支持该流程类型。"
            "系统生成 Mermaid 代码。"
            "系统检查 Mermaid 是否可以渲染。"
            "如果不能渲染，则提示用户检查流程描述或 Mermaid 代码。"
            "如果可以渲染，则保存 Mermaid 文件和 SVG 图片。"
            "流程结束。"
        ),
        expected_flow_type="branch",
        must_have_node_texts=[
            "用户输入流程描述",
            "输入是否为空",
            "调用 Flow Segmenter",
            "检测到多个流程",
            "调用 Research Agent",
            "concepts 是否为空",
            "调用 Decomposition Agent",
            "流程类型",
            "调用 linear rule extractor",
            "调用 branch flow extractor",
            "生成 Mermaid 代码",
            "Mermaid 代码是否可以渲染",
            "保存 Mermaid 文件和 SVG 图片",
        ],
        must_have_edge_labels=[
            "为空",
            "不为空",
            "linear",
            "branch",
            "不能渲染",
            "可以渲染",
        ],
        must_have_edges=[
            ("调用 linear rule extractor", "生成 Mermaid 代码"),
            ("调用 branch flow extractor", "生成 Mermaid 代码"),
            ("生成 Mermaid 代码", "Mermaid 代码是否可以渲染"),
        ],
    ),
]