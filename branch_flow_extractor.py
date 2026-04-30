import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from models.branch_flow_spec import BranchFlowSpec


# ============================================================
# Part 1. Ollama 基础配置
# 作用：
# 1. 指定本地 Ollama API 地址
# 2. 指定使用的模型
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"


# ============================================================
# Part 2. Mermaid 节点模板映射
# 作用：
# 1. 用经典 Mermaid 语法渲染 5 kinds
# 2. 避免使用 A@{ shape: ... } 这种本地 CLI 容易报错的新语法
# 3. 后续如果增加 kind，只需要扩展这个 map
# ============================================================

NODE_TEMPLATE_MAP = {
    "start_end": '{id}(["{text}"])',
    "process": '{id}["{text}"]',
    "decision": '{id}{{"{text}"}}',
    "input_output": '{id}[/"{text}"/]',
    "subroutine": '{id}[["{text}"]]',
}


# ============================================================
# Part 3. Prompt 构建函数
# 作用：
# 1. 集中管理 branch flow 的 Prompt
# 2. 使用普通字符串 + replace，避免 f-string 中 JSON 大括号报错
# 3. 精简原来过长、重复的规则
# 4. 保留 5 kinds、分支规则、回边规则等核心约束
# ============================================================

def build_branch_prompt(user_input: str) -> str:
    prompt = """
你是一个专业的分支流程图结构抽取器。

你的任务是：把用户输入的自然语言流程，转换成清晰、完整、适合 Mermaid flowchart 绘制的结构化 JSON。

你只能输出 JSON。
不要输出解释。
不要输出 Markdown。
不要输出代码块标记。
不要输出思考过程。
不要在 JSON 外添加任何文字。

====================
最高优先级规则：decision 与 edge.label
====================

decision 节点分为两类：

1. 分类型 decision
用于判断一个对象属于哪一类。
这类 decision 不需要写成“是否为 A / 是否为 B”。
正确写法应是：
- 流程类型？
- 文件类型？
- 路由结果？
- 处理结果？
- 用户角色？

例如：
用户说“如果流程是线性流程……如果流程是分支流程……”
正确：
node: 流程类型？ kind="decision"
edge: 流程类型？ -> 调用 linear extractor, label="线性流程"
edge: 流程类型？ -> 调用 branch extractor, label="分支流程"

错误：
不要生成“流程是线性流程？”和“流程是分支流程？”两个 decision。

2. 检查型 decision
用于判断某个属性是否满足。
这类 decision 应尽量使用正向属性问题：
- JSON 是否完整？
- JSON 是否合法？
- Mermaid 代码是否可以编译？
- API 请求是否成功？
- 参数是否完整？
- 权限是否通过？

不要生成负向问题：
- JSON 是否不完整？
- JSON 不完整？
- JSON 不合法？
- Mermaid 代码是否不能编译？
- API 请求是否失败？

负向结果只能作为 edge.label：
- 不完整
- 不合法
- 不能编译
- 失败
- 不通过

判断结果不能作为节点，只能作为 edge.label。
禁止把以下内容作为 node：
- 是 / 否
- 成功 / 失败
- 通过 / 不通过
- 线性流程 / 分支流程
- 完整 / 不完整
- 合法 / 不合法
- 可以编译 / 不能编译

正确结构：
- decision 节点表示“要判断什么”
- edge.label 表示“判断结果”
- edge.target 连接到对应动作节点

不要把不同属性的判断结果混在同一个 decision 节点下。

例如：
“JSON 是否完整？” 只能使用 “完整 / 不完整” 作为 edge.label。
“JSON 是否合法？” 只能使用 “合法 / 不合法” 作为 edge.label。
“Mermaid 代码是否可以编译？” 只能使用 “可以编译 / 不能编译” 作为 edge.label。

如果用户先说“JSON 不完整”，后面又说“JSON 不合法 / JSON 合法”，必须生成两个 decision：
1. JSON 是否完整？
2. JSON 是否合法？

错误：
JSON 是否完整？ -> 提示用户重新输入需求, label="不合法"
JSON 是否完整？ -> 调用 Mermaid 生成模块, label="合法"

正确：
JSON 是否完整？ -> JSON 是否合法？, label="完整"
JSON 是否合法？ -> 提示用户重新输入需求, label="不合法"
JSON 是否合法？ -> 调用 Mermaid 生成模块, label="合法"

====================
输出 JSON 格式
====================

必须输出如下结构：

{
  "diagram_type": "flowchart",
  "direction": "TD",
  "nodes": [
    {
      "id": "A",
      "text": "开始",
      "kind": "start_end"
    }
  ],
  "edges": [
    {
      "source": "A",
      "target": "B",
      "label": ""
    }
  ]
}

====================
节点规则
====================

1. diagram_type 固定为 "flowchart"。
2. direction 默认使用 "TD"。
3. nodes 是节点列表。
4. edges 是连线列表。
5. 每个节点必须包含 id、text、kind。
6. id 使用大写字母按顺序编号，例如 A、B、C、D、E……，不要跳号。
7. 每个节点只表达一个动作或一个判断，不要把多个动作塞进同一个节点。
8. 明确出现的输入、调用、检查、展示、保存、结束等步骤都应该保留。
9. 节点 text 要简洁清楚，尽量控制在 4 到 16 个中文字符。
10. 不要使用含糊文字，例如“处理”“操作”“进行下一步”。

====================
编译检查规则
====================

当用户提到：
“系统检查 Mermaid 代码是否可以编译”
“如果不能编译，则调用 Mermaid 修复模块”
“如果可以编译，则生成 SVG 图片”

必须生成一个 decision 节点：
- Mermaid 代码是否可以编译？

它必须至少有两个出口：
1. label="不能编译" -> 调用 Mermaid 修复模块
2. label="可以编译" -> 生成 SVG 图片

调用 Mermaid 修复模块后，必须返回到：
- Mermaid 代码是否可以编译？

不要把“Mermaid 代码可以编译”或“Mermaid 代码不能编译”生成成节点。
它们只能作为 edge.label。

====================
节点与连线一致性规则
====================

1. edges 中每一条边的 source 和 target，必须都能在 nodes 的 id 中找到。
2. 禁止在 edges 中引用不存在的节点 id。
3. 如果流程需要连接到某个步骤，必须先在 nodes 中创建该步骤。
4. 输出 JSON 前必须自检：
   - 所有 edge.source 都存在于 nodes
   - 所有 edge.target 都存在于 nodes
   - 不存在未定义的节点 id

====================
流程顺序与分支汇合规则
====================

必须严格保持用户描述中的先后顺序。

当一个 decision 产生多个普通业务分支时，分支动作完成后必须连接到用户描述中紧接着出现的共同后续步骤。

共同后续步骤不能绕过分支动作，不能直接从分支前的节点连接。

抽象结构：
前置步骤 -> 判断节点？
判断节点？ -> 动作 A, label="条件 A"
判断节点？ -> 动作 B, label="条件 B"
动作 A -> 共同后续步骤
动作 B -> 共同后续步骤

错误结构：
前置步骤 -> 共同后续步骤
动作 A 没有出边
动作 B 没有出边

如果用户说“随后、之后、接着、然后、再检查……”，这个步骤通常是前面所有分支完成后的共同后续步骤。

【edge.label 与目标动作一致性】

decision 的 edge.label 必须和 target 动作语义一致。

正向 label，例如：
完整、合法、正确、成功、通过、可以编译

应该连接到正常后续动作，例如：
调用模块、检查下一项、生成、解析、进入系统、输出结果。

负向 label，例如：
不完整、不合法、错误、失败、不通过、不能编译

应该连接到异常处理动作，例如：
提示补充、提示重新输入、记录错误、修复、重试、拒绝访问。

错误：
登录信息是否完整？ -> 返回输入阶段, label="完整"

正确：
登录信息是否完整？ -> 调用登录验证模块, label="完整"
====================
重新检查/重新编译规则
====================

“重新检查 JSON”“重新编译”“重新验证”通常表示回到前面的检查节点，不要把它们当作新的普通流程继续向后连接。

正确做法：
调用 JSON 修复模块 -> JSON 是否合法？，label="返回"
调用 Mermaid 修复模块 -> Mermaid 代码是否可以编译？，label="返回"

不要生成：
调用 JSON 修复模块 -> 重新检查 JSON -> JSON 不合法

====================
kind 类型规则
====================

kind 只能是以下五种：

1. start_end
用于开始、结束、终止、完成。

例如：
- 开始
- 结束流程
- 终止程序
- 项目完成

2. decision
用于条件判断。

例如：
- 输入是否为空？
- JSON 是否符合规范？
- 是否继续修改？
- API 调用是否成功？

如果节点 text 包含“是否”“选择是否”“判断是否”“是否继续”“是否需要”“能否”，必须优先使用 decision。

decision 节点的 text 必须尽量写成问题形式。

3. subroutine
用于调用模块、调用函数、调用 Agent、调用工具、运行程序、执行子流程。

例如：
- 调用流程抽取模块
- 调用 JSON 修复模块
- 调用 Mermaid 渲染模块
- 调用代码 Agent
- 运行 Monte Carlo 仿真程序

4. input_output
用于输入、输出、读取、写入、上传、下载、导出、保存、展示、提示、返回信息。

例如：
- 用户输入业务描述
- 上传文件
- 读取输出数据
- 保存结果
- 展示流程图
- 提示重新输入
- 返回错误信息

5. process
用于其他普通处理动作。

例如：
- 分析需求
- 清洗数据
- 生成报告
- 整合结果
- 检查参数

类型选择优先级固定为：
start_end > decision > subroutine > input_output > process

如果一个节点同时符合多个类型，必须选择优先级更靠前的 kind。

====================
分支结构规则
====================

1. 如果出现“如果……则……；否则……”结构，必须生成一个 decision 节点和至少两条分支边。
2. 从 decision 节点出发的边必须尽量填写 label。
3. 同一个判断只能生成一个 decision 节点，不要重复生成。
4. 每个 decision 节点通常至少有两个出口。

====================
步骤拆分规则
====================

1. 如果用户输入中包含多个连续动作，必须拆成多个节点，并根据 kind 类型规则分别选择合适的 kind。
2. 如果用户文本中出现“用户输入……后，系统判断……”，必须先生成“用户输入……” input_output 节点，再生成 decision 节点。
3. 不要直接从开始节点连接到判断节点，除非原文没有任何前置动作。
4. 如果节点 text 包含“结束”“结束流程”“终止”“完成”“流程结束”，kind 必须是 start_end。

====================
回边规则
====================

如果流程中出现以下含义，应尽量生成回边：

1. “提示重新输入”应回到最近的输入节点。
2. “重新上传”应回到最近的上传节点。
3. “再次检查”“重新检查”“再次解析”通常表示回边，应连接回对应检查或判断节点。
4. “返回输入阶段”可以作为 process 节点保留，但它必须连接回输入节点。
5. “重新调用”通常表示流程跳转，应连接回对应的调用节点或判断节点。
6. “调用 JSON 修复模块”后通常应连接回 JSON 是否符合规范的 decision 节点。
注意：
如果回边没有完全生成，系统后续会进行自动修复。
但你应该尽量直接生成正确回边。

====================
返回/重新输入规则
====================

“返回输入阶段”“返回输入”“重新输入”“再次输入”通常表示回到前面的真实输入节点。

优先把这类语义表达为 edge.label="返回"，不要单独生成“返回输入阶段”节点。

正确：
提示用户补充信息 -> 用户输入信息, label="返回"
提示用户重新输入 -> 用户输入信息, label="返回"

如果模型确实生成了“返回输入阶段”节点，则该节点必须连接回真实输入节点。
后处理可能会把这类纯跳转节点压缩成 label="返回" 的回边。

真实输入节点通常包含：
- 用户输入
- 用户提交
- 读取用户输入
- 输入参数
- 输入账号
- 提交需求

不要把以下节点当作真实输入节点：
- 提示用户补充信息
- 提示用户重新输入
- 输出结果
- 显示欢迎信息
====================
简短示例
====================

用户输入：
用户输入内容后，系统判断输入是否为空。如果为空，则提示重新输入；如果不为空，则调用处理模块并输出结果。

正确结构应包含：
- 用户输入内容：input_output
- 输入是否为空？：decision
- 提示重新输入：input_output
- 调用处理模块：subroutine
- 输出结果：input_output

正确边关系应包含：
- 输入是否为空？ -->|是| 提示重新输入
- 提示重新输入 --> 用户输入内容
- 输入是否为空？ -->|否| 调用处理模块

====================
用户输入
====================

__USER_INPUT__
"""
    return prompt.replace("__USER_INPUT__", user_input)


# ============================================================
# Part 4. Branch Flow 抽取主函数
# 作用：
# 1. 构建 Prompt
# 2. 请求 Ollama
# 3. 读取模型返回 JSON
# 4. 使用 BranchFlowSpec 做结构校验
# 5. 调用 repair_missing_back_edges() 自动补充确定性回边
# ============================================================

def extract_branch_flow(user_input: str) -> BranchFlowSpec:
    prompt = build_branch_prompt(user_input)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": BranchFlowSpec.model_json_schema(),
        "options": {
            "temperature": 0
        }
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama 请求失败，请检查 Ollama 是否已启动：{e}")

    except TimeoutError:
        raise RuntimeError("Ollama 请求超时，请检查模型是否正在运行或输入是否过长。")

    raw_json = result["response"]

    print("\nOllama 返回的 branch JSON：")
    print(raw_json)

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ollama 返回内容不是合法 JSON：{e}\n原始输出：\n{raw_json}")

    branch_spec = BranchFlowSpec.model_validate(data)

    # 0. 修复或删除非法 edge，例如 target=""
    branch_spec = repair_or_remove_invalid_edges(branch_spec)

    # 1. 自动修复模型可能漏掉的确定性回边
    branch_spec = repair_missing_back_edges(branch_spec)

    # 2. 修复 decision 分支生成后没有汇合到后续步骤的问题
    branch_spec = repair_decision_branch_join(branch_spec)

    # 3. 通用修复无入边节点
   # branch_spec = repair_missing_incoming_edges_generic(branch_spec)

    # 4. 通用反馈回路修复：修复、重试、重新检查、返回输入等
    branch_spec = repair_feedback_loop_edges(branch_spec)

    # 5. 把“返回 / 重新检查 / 重新编译”等纯跳转节点压缩成 edge.label
    branch_spec = contract_feedback_jump_nodes_to_previous_decision(branch_spec)

    # 6. 通用 decision 出边 label 修复
    branch_spec = repair_decision_edge_labels_generic(branch_spec)

    # 7. 给已有回边补 label="返回"，用于 Mermaid 虚线显示
    branch_spec = label_existing_back_edges(branch_spec)

    # 8. 删除模型多生成的孤立跳转节点
    branch_spec = remove_orphan_jump_nodes(branch_spec)

    return branch_spec


# ============================================================
# Part 5. BranchFlowExtractor 类
# 作用：
# 1. 接收 BranchFlowSpec 或 dict
# 2. 转换成 Mermaid flowchart 文本
# 3. 支持 5 kinds 的经典 Mermaid 渲染
# 4. 将 label 为“返回”的边渲染为虚线回边
# ============================================================

class BranchFlowExtractor:
    def __init__(self, branch_diagram: Any):
        self.diagram = self._to_dict(branch_diagram)
        self.nodes = self.diagram.get("nodes", [])
        self.edges = self.diagram.get("edges", [])
        self.direction = self.diagram.get("direction", "TD")
        self.spec = branch_diagram

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """
        作用：
        兼容 dict 和 Pydantic model。
        因为 extract_branch_flow() 返回的是 BranchFlowSpec，
        但后续也可能直接传 dict 进来。
        """
        if isinstance(obj, dict):
            return obj

        if hasattr(obj, "model_dump"):
            return obj.model_dump()

        if hasattr(obj, "dict"):
            return obj.dict()

        raise TypeError("Unsupported branch diagram type. Expected dict or Pydantic model.")

    def _escape_text(self, text: Optional[str]) -> str:
        """
        作用：
        转义 Mermaid 节点文本中的双引号，避免 Mermaid 解析失败。
        """
        if text is None:
            return ""
        return str(text).replace('"', '\\"')

    def _render_node(self, node: Dict[str, Any]) -> str:
        """
        作用：
        根据 node.kind 选择 Mermaid 节点模板。
        这样比大量 if / elif 更清晰，也方便后续扩展 kind。
        """
        node_id = node["id"]
        text = self._escape_text(node["text"])
        kind = node.get("kind", "process")

        template = NODE_TEMPLATE_MAP.get(kind, NODE_TEMPLATE_MAP["process"])

        return template.format(
            id=node_id,
            text=text,
        )

    def _render_edge(self, edge: Dict[str, Any]) -> str:
        """
        作用：
        渲染 Mermaid 连线。
        普通边：A --> B
        判断边：A -->|是| B
        回边：A -.->|返回| B
        """
        source = edge["source"]
        target = edge["target"]
        label = edge.get("label")

        if label:
            label = self._escape_text(label)

            if label == "返回":
                return f"{source} -.->|{label}| {target}"

            return f"{source} -->|{label}| {target}"

        return f"{source} --> {target}"

    def to_mermaid(self) -> str:
        """
        作用：
        生成完整 Mermaid flowchart 文本。
        defaultRenderer 使用 elk，可以在复杂图上尽量改善布局。

        这里会在 Mermaid 输出阶段去掉重复 edge。
        注意：只影响最终显示，不修改原始 spec.edges。
        """
        lines = [
            '%%{init: {"flowchart": {"defaultRenderer": "elk"}}}%%',
            f"flowchart {self.direction}"
        ]

        # 1. 渲染节点
        for node in self.nodes:
            lines.append(self._render_node(node))

        lines.append("")

        # 2. 渲染边：去掉完全重复的 edge
        seen_edges = set()

        for edge in self.edges:
            source = edge.get("source")
            target = edge.get("target")
            label = edge.get("label") or ""

            # 去掉 label 前后空格，避免 "" 和 None / 空格造成重复线
            label = str(label).strip()

            edge_key = (source, target, label)

            if edge_key in seen_edges:
                continue

            seen_edges.add(edge_key)
            lines.append(self._render_edge(edge))

        return "\n".join(lines)
# ============================================================
# Part 6. Branch 后处理辅助函数
# 作用：
# 1. 给模型已经生成的回边补充 label="返回"
# 2. 删除模型多生成的孤立跳转节点
# 3. 这些函数用于修复 LLM 输出中的小结构问题
# ============================================================
def label_existing_back_edges(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    给模型已经生成但 label 为空的回边补充 label='返回'。

    作用：
    1. 如果一条边从后面的节点指向前面的节点，说明它大概率是回边。
    2. 给这类边加上 label='返回'。
    3. Mermaid 渲染时 label='返回' 会被画成虚线。
    """

    node_index = {
        node.id: index
        for index, node in enumerate(spec.nodes)
    }

    for edge in spec.edges:
        source_index = node_index.get(edge.source)
        target_index = node_index.get(edge.target)

        if source_index is None or target_index is None:
            continue

        is_back_edge = target_index < source_index

        if is_back_edge and not edge.label:
            edge.label = "返回"

    return spec

def remove_orphan_jump_nodes(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    删除模型多生成的孤立跳转节点。

    适用场景：
    模型已经用回边表达了“再次检查”，
    例如：
    调用 JSON 修复模块 --> JSON 是否符合规范？

    但模型又额外生成了一个没有任何连线的节点：
    G: 再次检查

    如果这个节点没有入边、没有出边，并且只是跳转含义，就删除它。
    """

    connected_node_ids = set()

    for edge in spec.edges:
        connected_node_ids.add(edge.source)
        connected_node_ids.add(edge.target)

    jump_keywords = [
        "再次检查",
        "重新检查",
        "再次解析",
        "重新解析",
        "返回上一步",
        "重新尝试",
    ]

    cleaned_nodes = []

    for node in spec.nodes:
        is_orphan = node.id not in connected_node_ids
        is_jump_node = any(keyword in node.text for keyword in jump_keywords)

        if is_orphan and is_jump_node:
            continue

        cleaned_nodes.append(node)

    spec.nodes = cleaned_nodes

    return spec

def repair_feedback_loop_edges(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    通用反馈回路修复函数。

    自动识别以下类型的回路：
    1. JSON 修复 / 重新检查 -> 返回 JSON 检查节点
    2. Mermaid 修复 / 重新编译 -> 返回 Mermaid 编译检查节点
    3. API 重试请求 -> 返回 API 请求模块或 API 成功判断节点
    4. 返回输入阶段 / 重新输入 -> 返回最近的输入节点
    5. 其他“修复 / 重试 / 重新验证” -> 返回最近的 decision 节点

    这个函数只补充缺失的回边，不主动删除节点。
    """

    if not spec.edges:
        return spec

    def norm(text: str) -> str:
        if text is None:
            return ""
        return str(text).replace(" ", "").replace("\n", "")

    node_by_id = {node.id: node for node in spec.nodes}
    node_index = {node.id: i for i, node in enumerate(spec.nodes)}
    existing_pairs = {(edge.source, edge.target) for edge in spec.edges}

    outgoing = {}
    for edge in spec.edges:
        outgoing.setdefault(edge.source, []).append(edge)

    EdgeType = type(spec.edges[0])

    def has_backward_edge(node_id: str) -> bool:
        """
        如果节点已经有指向前面节点的边，就认为它已经有回边。
        """
        source_idx = node_index.get(node_id)

        if source_idx is None:
            return False

        for edge in outgoing.get(node_id, []):
            target_idx = node_index.get(edge.target)

            if target_idx is not None and target_idx < source_idx:
                return True

            label = norm(getattr(edge, "label", "") or "")
            if label == "返回":
                return True

        return False

    def latest_before(source_id: str, candidates):
        """
        从候选节点中找出位于当前节点之前、且最靠近当前节点的目标节点。
        """
        source_idx = node_index.get(source_id)

        if source_idx is None:
            return None

        valid_candidates = [
            node for node in candidates
            if node.id in node_index and node_index[node.id] < source_idx
        ]

        if not valid_candidates:
            return None

        return max(valid_candidates, key=lambda node: node_index[node.id])

    def find_loop_target(node):
        """
        根据当前节点文本，判断它应该返回到哪里。
        """
        text = norm(node.text)

        # 1. 返回输入 / 重新输入 / 补充参数 -> 回到最近的输入节点
        if (
            "返回输入" in text
            or "重新输入" in text
            or "再次输入" in text
            or "补充参数" in text
            or "补充信息" in text
            or "补充需求" in text
        ):
            input_keywords = [
                "用户输入",
                "用户提交",
                "读取用户输入",
                "输入账号",
                "输入参数",
                "提交需求",
                "提交流程",
                "上传",
            ]

            output_like_keywords = [
                "提示",
                "输出",
                "显示",
                "生成成功",
                "欢迎信息",
                "结果摘要",
            ]

            input_nodes = []

            for n in spec.nodes:
                n_text = norm(n.text)

                if n.kind != "input_output":
                    continue

                # 排除提示 / 输出 / 显示类节点
                if any(keyword in n_text for keyword in output_like_keywords):
                    continue

                # 只保留真正的输入入口
                if any(keyword in n_text for keyword in input_keywords):
                    input_nodes.append(n)

            return latest_before(node.id, input_nodes)

        # 2. JSON 修复 / 重新检查 JSON -> 回到 JSON 判断/检查节点
        if "JSON" in text:
            json_check_nodes = [
                n for n in spec.nodes
                if (
                    "JSON" in norm(n.text)
                    and (
                        n.kind == "decision"
                        or "检查" in norm(n.text)
                        or "验证" in norm(n.text)
                    )
                )
            ]
            return latest_before(node.id, json_check_nodes)

        # 3. Mermaid 修复 / 重新编译 -> 回到 Mermaid 编译检查节点
        if "Mermaid" in text or "编译" in text:
            mermaid_check_nodes = [
                n for n in spec.nodes
                if (
                    (
                        "Mermaid" in norm(n.text)
                        or "编译" in norm(n.text)
                    )
                    and (
                        n.kind == "decision"
                        or "检查" in norm(n.text)
                    )
                )
            ]
            return latest_before(node.id, mermaid_check_nodes)

        # 4. API 重试请求 -> 优先回到 API 请求模块
        if "API" in text or "请求" in text:
            api_request_modules = [
                n for n in spec.nodes
                if (
                    n.kind == "subroutine"
                    and (
                        "API" in norm(n.text)
                        or "请求" in norm(n.text)
                    )
                )
            ]

            target = latest_before(node.id, api_request_modules)
            if target is not None:
                return target

            api_decision_nodes = [
                n for n in spec.nodes
                if (
                    n.kind == "decision"
                    and (
                        "API" in norm(n.text)
                        or "请求" in norm(n.text)
                    )
                )
            ]
            return latest_before(node.id, api_decision_nodes)

        # 5. 其他修复 / 重试 / 重新验证 -> 回到最近的 decision 节点
        generic_check_nodes = [
            n for n in spec.nodes
            if n.kind == "decision"
        ]
        return latest_before(node.id, generic_check_nodes)

    feedback_keywords = [
        "修复",
        "重试",
        "重新检查",
        "重新验证",
        "重新编译",
        "重新登录",
        "返回输入",
        "重新输入",
        "再次输入",
        "回到",
    ]

    new_edges = []

    for node in spec.nodes:
        text = norm(node.text)

        # 只处理带有反馈/回路语义的节点
        if not any(keyword in text for keyword in feedback_keywords):
            continue

        # 如果已经有回边，就不重复添加
        if has_backward_edge(node.id):
            continue

        target_node = find_loop_target(node)

        if target_node is None:
            continue

        if (node.id, target_node.id) in existing_pairs:
            continue

        new_edges.append(
            EdgeType(
                source=node.id,
                target=target_node.id,
                label="返回"
            )
        )

        existing_pairs.add((node.id, target_node.id))

    spec.edges.extend(new_edges)

    return spec

def contract_feedback_jump_nodes_to_previous_decision(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    通用压缩反馈跳转节点。

    目标：
        A -> 返回 -> 上一个 decision
    压缩为：
        A ->|返回| 上一个 decision

        A -> 重新检查 JSON -> JSON 是否完整？
    压缩为：
        A ->|重新检查| JSON 是否完整？

        A -> 重新编译 -> Mermaid 代码是否可以编译？
    压缩为：
        A ->|重新编译| Mermaid 代码是否可以编译？

    注意：
    1. 只处理纯跳转语义节点。
    2. 不处理“解析返回数据”这种业务节点。
    3. 不处理“返回输入阶段 / 重新输入”这种应返回 input 节点的情况。
    """

    if not spec.edges:
        return spec

    def norm(text) -> str:
        if text is None:
            return ""
        return str(text).replace(" ", "").replace("\n", "").replace("\t", "")

    node_by_id = {node.id: node for node in spec.nodes}
    node_index = {node.id: i for i, node in enumerate(spec.nodes)}

    incoming = {}
    outgoing = {}

    for edge in spec.edges:
        incoming.setdefault(edge.target, []).append(edge)
        outgoing.setdefault(edge.source, []).append(edge)

    existing_pairs = {(edge.source, edge.target) for edge in spec.edges}
    EdgeType = type(spec.edges[0])


    def is_feedback_jump_node(node) -> bool:
        text = norm(node.text)

        # 只压缩普通 process，不压缩 subroutine / input_output / decision
        if node.kind != "process":
            return False

        # 包含真实动作词的节点，不是纯跳转节点
        action_keywords = [
            "调用",
            "模块",
            "修复",
            "生成",
            "保存",
            "输出",
            "解析",
            "检查",
            "读取",
            "提交",
            "提示用户",
        ]

        if any(keyword in text for keyword in action_keywords):
            # 注意：“重新检查 JSON”虽然有检查，但它更像跳转。
            # 如果你希望保留它为纯跳转，可以把“重新检查”单独放行。
            if not text.startswith("重新检查") and not text.startswith("再次检查"):
                return False

        pure_jump_keywords = [
            "返回",
            "重新检查",
            "再次检查",
            "重新判断",
            "再次判断",
            "重新验证",
            "重新编译",
        ]

        return any(text == keyword or text.startswith(keyword) for keyword in pure_jump_keywords)

    def get_jump_label(node) -> str:
        """
        把跳转节点文本转成 edge.label。
        """
        text = norm(node.text)

        if "重新编译" in text:
            return "重新编译"

        if "重新检查" in text or "再次检查" in text:
            return "重新检查"

        if "重新验证" in text:
            return "重新验证"

        if "重新判断" in text or "再次判断" in text:
            return "重新判断"

        return "返回"

    def find_previous_decision_for_jump(node):
        """
        为跳转节点找最合理的上一个 decision 节点。

        优先级：
        1. 如果 jump 节点已有出边指向前面的 decision，就直接用这个 target。
        2. 否则根据关键词找同语义领域的最近 decision。
        3. 最后退回到最近的 decision。
        """
        node_text = norm(node.text)
        current_index = node_index.get(node.id)

        if current_index is None:
            return None

        # 1. 优先使用已有出边里的 decision target
        for edge in outgoing.get(node.id, []):
            target_node = node_by_id.get(edge.target)

            if target_node is None:
                continue

            target_index = node_index.get(target_node.id)

            if (
                target_node.kind == "decision"
                and target_index is not None
                and target_index < current_index
            ):
                return target_node

        previous_decisions = [
            n for n in spec.nodes
            if n.kind == "decision"
            and node_index.get(n.id, 999999) < current_index
        ]

        if not previous_decisions:
            return None

        # 2. 根据语义关键词优先匹配同类 decision
        semantic_keywords = []

        if "JSON" in node_text:
            semantic_keywords.extend(["JSON", "合法", "完整", "规范"])

        if "Mermaid" in node_text or "编译" in node_text:
            semantic_keywords.extend(["Mermaid", "编译"])

        if "API" in node_text or "请求" in node_text:
            semantic_keywords.extend(["API", "请求", "成功"])

        if semantic_keywords:
            matched_decisions = [
                n for n in previous_decisions
                if any(keyword in norm(n.text) for keyword in semantic_keywords)
            ]

            if matched_decisions:
                return max(matched_decisions, key=lambda n: node_index[n.id])

        # 3. 默认返回最近的 decision
        return max(previous_decisions, key=lambda n: node_index[n.id])

    remove_node_ids = set()
    remove_edge_ids = set()
    new_edges = []

    for node in spec.nodes:
        if not is_feedback_jump_node(node):
            continue

        in_edges = incoming.get(node.id, [])
        out_edges = outgoing.get(node.id, [])

        # 只处理一入一出的纯跳转节点，避免误伤复杂结构
        if len(in_edges) != 1 or len(out_edges) != 1:
            continue

        in_edge = in_edges[0]
        out_edge = out_edges[0]

        source = in_edge.source
        target = out_edge.target

        if source == target:
            continue

        jump_label = get_jump_label(node)

        # 优先使用原本 out_edge 的 target，不要强行找 previous decision
        if (source, target) not in existing_pairs:
            new_edges.append(
                EdgeType(
                    source=source,
                    target=target,
                    label=jump_label
                )
            )
            existing_pairs.add((source, target))
        else:
            # 如果 source -> target 已经存在，但 label 为空，则补 label
            for edge in spec.edges:
                if edge.source == source and edge.target == target:
                    current_label = getattr(edge, "label", None)
                    if current_label is None or str(current_label).strip() == "":
                        edge.label = jump_label

        # 删除 jump 节点及其相关边
        remove_node_ids.add(node.id)

        remove_edge_ids.add(id(in_edge))
        remove_edge_ids.add(id(out_edge))

        print(
            f"[repair] contract feedback jump node: "
            f"{node.id}({node.text}) -> {source} -> {target}, label={jump_label}"
        )

    spec.nodes = [
        node for node in spec.nodes
        if node.id not in remove_node_ids
    ]

    spec.edges = [
        edge for edge in spec.edges
        if id(edge) not in remove_edge_ids
        and edge.source not in remove_node_ids
        and edge.target not in remove_node_ids
    ]

    spec.edges.extend(new_edges)

    return spec

def repair_missing_incoming_edges_generic(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    通用无入边节点修复函数。

    目标：
    1. 不针对 JSON / Mermaid / API 写死规则
    2. 只修复高置信度的无入边节点
    3. 不删除节点，只补充可能缺失的边
    4. 低置信度情况不乱连，继续交给 validator warning

    主要修复三类情况：
    A. 中间步骤没有入边，但前一个节点没有出边 -> 补 prev -> current
    B. “提示/补充/重新输入/修复/重试/错误/失败”等异常处理节点没有入边 -> 从最近 decision 连过来
    C. decision 可能少了一个分支动作 -> 从最近 decision 连到该节点
    """

    if not spec.edges:
        return spec

    def norm(text) -> str:
        if text is None:
            return ""
        return str(text).replace(" ", "").replace("\n", "").replace("\t", "")

    node_index = {node.id: i for i, node in enumerate(spec.nodes)}
    node_by_id = {node.id: node for node in spec.nodes}

    incoming = {}
    outgoing = {}

    for edge in spec.edges:
        incoming.setdefault(edge.target, []).append(edge)
        outgoing.setdefault(edge.source, []).append(edge)

    existing_pairs = {(edge.source, edge.target) for edge in spec.edges}
    EdgeType = type(spec.edges[0])

    def is_allowed_entry_node(node) -> bool:
        """
        这些节点即使没有入边，也可能是合法入口。
        """
        text = norm(node.text)
        index = node_index.get(node.id, 999999)

        if index == 0:
            return True

        if node.kind == "start_end" and ("开始" in text or "Start" in text):
            return True

        if "外部触发" in text or "定时触发" in text or "用户启动" in text:
            return True

        return False

    def is_feedback_jump_node(node) -> bool:
        """
        判断节点是否是纯跳转节点。

        只压缩：
        - 返回
        - 重新检查 JSON
        - 重新编译
        - 再次判断
        这类纯跳转 process 节点。

        不压缩：
        - 调用 Mermaid 修复模块修改语法并重新编译
        - 调用 JSON 修复模块
        - 解析返回数据
        - 提示用户重新输入需求
        """

        text = norm(node.text)

        # 只处理 process。subroutine / decision / input_output 都不能压缩。
        if node.kind != "process":
            return False

        # 排除业务语义：这些不是跳转
        business_return_keywords = [
            "返回数据",
            "返回结果",
            "返回值",
            "返回内容",
            "API返回",
            "解析返回数据",
        ]

        if any(keyword in text for keyword in business_return_keywords):
            return False

        # 返回输入阶段 / 重新输入属于用户交互回路，不在这里压缩到 decision
        input_return_keywords = [
            "返回输入阶段",
            "返回输入",
            "重新输入",
            "再次输入",
            "提示用户重新输入",
        ]

        if any(keyword in text for keyword in input_return_keywords):
            return False

        # 排除真实动作节点
        action_keywords = [
            "调用",
            "模块",
            "修复",
            "生成",
            "保存",
            "输出",
            "解析",
            "读取",
            "提交",
            "提示用户",
            "记录",
        ]

        if any(keyword in text for keyword in action_keywords):
            return False

        # 明确的纯跳转节点
        exact_jump_texts = [
            "返回",
            "回到",
            "重新检查",
            "再次检查",
            "重新判断",
            "再次判断",
            "重新验证",
            "重新编译",
        ]

        if text in exact_jump_texts:
            return True

        # 带对象的纯跳转节点，必须以这些词开头
        # 例如：重新检查JSON、重新编译Mermaid代码
        allowed_prefixes = [
            "重新检查",
            "再次检查",
            "重新判断",
            "再次判断",
            "重新验证",
            "重新编译",
            "返回检查",
            "回到检查",
            "返回判断",
            "回到判断",
        ]

        return any(text.startswith(prefix) for prefix in allowed_prefixes)

    def latest_previous_decision(node):
        """
        找当前节点之前最近的 decision 节点。
        """
        current_index = node_index.get(node.id)

        if current_index is None:
            return None

        candidates = [
            n for n in spec.nodes
            if n.kind == "decision"
            and node_index.get(n.id, 999999) < current_index
        ]

        if not candidates:
            return None

        return max(candidates, key=lambda n: node_index[n.id])

    def latest_previous_leaf_node(node):
        """
        找当前节点之前最近的“没有出边的普通节点”。
        这通常表示模型漏掉了顺序连接。
        """
        current_index = node_index.get(node.id)

        if current_index is None:
            return None

        candidates = []

        for n in spec.nodes:
            n_index = node_index.get(n.id, 999999)

            if n_index >= current_index:
                continue

            if n.kind == "start_end":
                continue

            if n.kind == "decision":
                continue

            if outgoing.get(n.id):
                continue

            candidates.append(n)

        if not candidates:
            return None

        return max(candidates, key=lambda n: node_index[n.id])

    def decision_has_room_for_branch(decision_node) -> bool:
        """
        如果一个 decision 当前出口少于 2 个，说明它可能漏了一个分支。
        """
        return len(outgoing.get(decision_node.id, [])) < 2

    new_edges = []

    for node in spec.nodes:
        # 已经有入边，不处理
        if incoming.get(node.id):
            continue

        # 合法入口，不处理
        if is_allowed_entry_node(node):
            continue

        source_node = None

        # 情况 A：如果前面最近的普通节点没有出边，优先认为是顺序断裂
        previous_leaf = latest_previous_leaf_node(node)

        if previous_leaf is not None:
            source_node = previous_leaf

        # 情况 B：如果这是异常处理 / 反馈节点，则从最近 decision 连过来
        # 但只有当该 decision 出口少于 2 个时才补边，避免强行制造三出口判断
        if source_node is None and is_exception_or_feedback_node(node):
            decision_node = latest_previous_decision(node)

            if (
                decision_node is not None
                and decision_has_room_for_branch(decision_node)
            ):
                source_node = decision_node

        # 情况 C：如果最近 decision 少于两个出口，当前节点可能是漏掉的分支动作
        if source_node is None:
            decision_node = latest_previous_decision(node)

            if decision_node is not None and decision_has_room_for_branch(decision_node):
                source_node = decision_node

        # 没有高置信度来源，不强行修
        if source_node is None:
            continue

        if (source_node.id, node.id) in existing_pairs:
            continue

        new_edges.append(
            EdgeType(
                source=source_node.id,
                target=node.id,
                label=""
            )
        )

        existing_pairs.add((source_node.id, node.id))

        print(
            f"[repair] add missing incoming edge: "
            f"{source_node.id}({source_node.text}) -> {node.id}({node.text})"
        )

    spec.edges.extend(new_edges)

    return spec

def repair_decision_edge_labels_generic(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    通用 decision 出边 label 修复函数。

    作用：
    1. 只处理 source 是 decision 的边
    2. 只处理 label 为空的边
    3. 不针对 JSON / Mermaid / API 写死规则
    4. 根据 decision 文本和 target 文本的正负语义自动补 label

    例子：
        “是否完整？” + target=“修复/补全/重新输入”  -> label="不完整"
        “是否合法？” + target=“生成/输出/保存”      -> label="合法"
        “是否成功？” + target=“记录错误/重试”       -> label="失败"
        “是否可以编译？” + target=“修复语法”        -> label="不能编译"
    """

    def norm(text) -> str:
        if text is None:
            return ""
        return str(text).replace(" ", "").replace("\n", "").replace("\t", "")

    def strip_question_marks(text: str) -> str:
        return (
            text.replace("？", "")
            .replace("?", "")
            .replace("吗", "")
            .strip()
        )

    def get_label_pair(question_text: str):
        """
        根据 decision 节点文本，推断正向 label 和负向 label。
        不依赖具体业务名词，只依赖通用判断词。
        """
        text = strip_question_marks(norm(question_text))

        # 1. 是否完整
        if "完整" in text:
            return "完整", "不完整"

        # 2. 是否合法 / 合规 / 符合规范
        if "合法" in text:
            return "合法", "不合法"

        if "合规" in text:
            return "合规", "不合规"

        if "规范" in text:
            return "符合规范", "不符合规范"

        # 3. 是否成功
        if "成功" in text:
            return "成功", "失败"

        # 4. 是否通过
        if "通过" in text:
            return "通过", "不通过"

        # 5. 是否正常
        if "正常" in text:
            return "正常", "异常"

        # 6. 是否存在
        if "存在" in text:
            return "存在", "不存在"

        # 7. 是否有效
        if "有效" in text:
            return "有效", "无效"

        # 8. 是否匹配
        if "匹配" in text:
            return "匹配", "不匹配"

        # 9. 是否可用
        if "可用" in text:
            return "可用", "不可用"

        # 10. 是否可以 + 动作
        # 例如：Mermaid 代码是否可以编译？
        # 自动变成：可以编译 / 不能编译
        if "是否可以" in text:
            action = text.split("是否可以", 1)[1]
            action = strip_question_marks(action)

            if action:
                return f"可以{action}", f"不能{action}"

            return "可以", "不可以"

        # 11. 能否 + 动作
        # 例如：能否连接数据库？
        # 自动变成：能连接数据库 / 不能连接数据库
        if "能否" in text:
            action = text.split("能否", 1)[1]
            action = strip_question_marks(action)

            if action:
                return f"能{action}", f"不能{action}"

            return "能", "不能"

        # 12. 是否 + 动作，但没有明显属性词
        # 例如：是否继续？
        if "是否" in text:
            action = text.split("是否", 1)[1]
            action = strip_question_marks(action)

            if action:
                return action, f"不{action}"

            return "是", "否"

        # 13. 默认二元判断
        return "是", "否"

    def classify_target(target_text: str, positive_label: str, negative_label: str):
        """
        根据 target 节点文本判断它更像正向分支还是负向分支。
        返回：
            "positive"
            "negative"
            None
        """
        text = norm(target_text)

        positive_label_norm = norm(positive_label)
        negative_label_norm = norm(negative_label)

        # 如果 target 文本里直接包含 label 语义，优先使用
        if negative_label_norm and negative_label_norm in text:
            return "negative"

        if positive_label_norm and positive_label_norm in text:
            return "positive"

        negative_keywords = [
            "修复",
            "补全",
            "补充",
            "错误",
            "失败",
            "异常",
            "无效",
            "缺失",
            "不完整",
            "不合法",
            "不合规",
            "不符合",
            "不通过",
            "不匹配",
            "不能",
            "无法",
            "不可",
            "重新",
            "重试",
            "返回",
            "提示用户",
            "拒绝",
            "终止",
        ]

        positive_keywords = [
            "生成",
            "保存",
            "输出",
            "解析",
            "进入",
            "继续",
            "成功",
            "通过",
            "合法",
            "合规",
            "符合",
            "完整",
            "可以",
            "正常",
            "存在",
            "有效",
            "匹配",
            "完成",
        ]

        negative_score = sum(1 for keyword in negative_keywords if keyword in text)
        positive_score = sum(1 for keyword in positive_keywords if keyword in text)

        if negative_score > positive_score:
            return "negative"

        if positive_score > negative_score:
            return "positive"

        return None

    node_by_id = {node.id: node for node in spec.nodes}

    outgoing = {}
    for edge in spec.edges:
        outgoing.setdefault(edge.source, []).append(edge)

    for node in spec.nodes:
        if node.kind != "decision":
            continue

        decision_edges = outgoing.get(node.id, [])

        if not decision_edges:
            continue

        positive_label, negative_label = get_label_pair(node.text)

        # 先根据 target 文本推断空 label
        for edge in decision_edges:
            current_label = norm(getattr(edge, "label", "") or "")

            if current_label:
                continue

            target_node = node_by_id.get(edge.target)

            if target_node is None:
                continue

            branch_type = classify_target(
                target_node.text,
                positive_label,
                negative_label
            )

            if branch_type == "positive":
                edge.label = positive_label

            elif branch_type == "negative":
                edge.label = negative_label

        # 如果是两个出口，且其中一个已经有 label，另一个没有，
        # 尝试用互补 label 补上。
        refreshed_edges = outgoing.get(node.id, [])

        if len(refreshed_edges) == 2:
            labeled_edges = [
                edge for edge in refreshed_edges
                if norm(getattr(edge, "label", "") or "")
            ]

            unlabeled_edges = [
                edge for edge in refreshed_edges
                if not norm(getattr(edge, "label", "") or "")
            ]

            if len(labeled_edges) == 1 and len(unlabeled_edges) == 1:
                existing_label = norm(getattr(labeled_edges[0], "label", "") or "")

                if existing_label == norm(positive_label):
                    unlabeled_edges[0].label = negative_label

                elif existing_label == norm(negative_label):
                    unlabeled_edges[0].label = positive_label

    return spec
# ============================================================
# Part 7. 修复或删除非法连线
# 作用：
# 1. 删除 source 或 target 为空的非法 edge
# 2. 删除 source 或 target 引用不存在节点的非法 edge
# 3. 如果 target 为空，但 source 节点具有明显终止语义
#    例如“拒绝访问 / 终止 / 结束 / 停止”，则尝试连接到已有结束节点
# 4. 避免非法 edge 进入后续 repair / validator / Mermaid 渲染流程
#
# 注意：
# 这是结构安全清理函数，不负责推断复杂业务逻辑。
# 它只处理明显非法的连线，例如：
#     K -> ""
#     X -> A   其中 X 不存在于 nodes
#     A -> Z   其中 Z 不存在于 nodes
#
# 调用位置：
# 应放在 BranchFlowSpec.model_validate(data) 之后，
# 并且放在所有其他后处理函数之前。
# ============================================================

def repair_or_remove_invalid_edges(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    修复或删除非法 edge。

    处理情况：
    1. source 或 target 为空
    2. source 或 target 不存在于 nodes
    3. 如果 target 为空，但 source 节点有明显终止语义，
       则尝试连接到已有的结束节点
    4. 如果无法安全修复，则删除该 edge

    典型修复：
        拒绝访问 -> ""
    修复为：
        拒绝访问 -> 结束流程
    """

    if not spec.edges:
        return spec

    def norm(text) -> str:
        if text is None:
            return ""
        return str(text).replace(" ", "").replace("\n", "").replace("\t", "")

    node_by_id = {node.id: node for node in spec.nodes}
    valid_node_ids = set(node_by_id.keys())
    EdgeType = type(spec.edges[0])

    def is_terminal_like_node(node) -> bool:
        """
        判断一个节点是否具有终止语义。
        这类节点如果 target 为空，可以安全地连到结束节点。
        """
        text = norm(node.text)

        terminal_keywords = [
            "结束",
            "终止",
            "停止",
            "拒绝访问",
            "访问拒绝",
            "流程结束",
            "任务结束",
            "退出",
            "失败结束",
            "不再处理",
        ]

        return any(keyword in text for keyword in terminal_keywords)

    def find_end_node():
        """
        找已有的结束节点。
        优先找 kind=start_end 且文本包含结束/终止的节点。
        """
        for node in spec.nodes:
            text = norm(node.text)

            if node.kind == "start_end" and (
                "结束" in text
                or "终止" in text
                or "完成" in text
                or "End" in text
            ):
                return node

        for node in spec.nodes:
            text = norm(node.text)

            if "结束" in text or "终止" in text or "完成" in text:
                return node

        return None

    end_node = find_end_node()
    cleaned_edges = []
    existing_pairs = set()

    for edge in spec.edges:
        source = getattr(edge, "source", None)
        target = getattr(edge, "target", None)
        label = getattr(edge, "label", "") or ""

        source = str(source).strip() if source is not None else ""
        target = str(target).strip() if target is not None else ""

        # 情况 1：source 为空，无法修复，删除
        if not source:
            print(
                f"[cleanup] remove invalid edge with empty source: "
                f"{source} -> {target}"
            )
            continue

        # 情况 2：source 不存在，无法修复，删除
        if source not in valid_node_ids:
            print(
                f"[cleanup] remove invalid edge with unknown source: "
                f"{source} -> {target}"
            )
            continue

        # 情况 3：target 为空，尝试修复到结束节点
        if not target:
            source_node = node_by_id.get(source)

            if (
                source_node is not None
                and end_node is not None
                and is_terminal_like_node(source_node)
                and source != end_node.id
            ):
                repaired_edge = EdgeType(
                    source=source,
                    target=end_node.id,
                    label=label
                )

                edge_key = (
                    repaired_edge.source,
                    repaired_edge.target,
                    getattr(repaired_edge, "label", "") or ""
                )

                if edge_key not in existing_pairs:
                    cleaned_edges.append(repaired_edge)
                    existing_pairs.add(edge_key)

                print(
                    f"[repair] repair empty target edge: "
                    f"{source_node.id}({source_node.text}) -> "
                    f"{end_node.id}({end_node.text})"
                )

            else:
                print(
                    f"[cleanup] remove invalid edge with empty target: "
                    f"{source} -> {target}"
                )

            continue

        # 情况 4：target 不存在，删除
        if target not in valid_node_ids:
            print(
                f"[cleanup] remove invalid edge with unknown target: "
                f"{source} -> {target}"
            )
            continue

        # 情况 5：合法 edge，保留，同时做一次完全重复去重
        edge_key = (source, target, label)

        if edge_key in existing_pairs:
            continue

        cleaned_edges.append(edge)
        existing_pairs.add(edge_key)

    spec.edges = cleaned_edges

    return spec

# ============================================================
# Part 8. 自动修复缺失回边
# 作用：
# 1. 修复“提示重新输入”没有回到输入节点的问题
# 2. 修复“返回输入阶段”没有回到输入节点的问题
# 3. 修复“JSON 修复模块”没有回到 JSON 检查节点的问题
# 4. 自动补充的回边 label 使用“返回”，从而在 Mermaid 中渲染为虚线
#
# 注意：
# 按你的要求，这里没有修改优化点 A。
# find_previous_input_node() 仍然保留：
# node.kind == "input_output"
# ============================================================

def repair_missing_back_edges(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    自动修复常见缺失回边：
    1. 提示重新输入 -> 最近的输入节点
    2. 返回输入阶段 -> 最近的输入节点
    3. 调用 JSON 修复模块 -> 最近的 JSON 检查 decision 节点
    """

    existing_edges = {
        (edge.source, edge.target)
        for edge in spec.edges
    }

    outgoing_sources = {
        edge.source
        for edge in spec.edges
    }
    return spec
    
def repair_decision_branch_join(spec: BranchFlowSpec) -> BranchFlowSpec:
    """
    修复 decision 分支没有汇合到共同后续步骤的问题。

    支持两种情况：

    情况 1：
        decision -> branch_1
        decision -> branch_2
        decision -> join_node

    修复为：
        branch_1 -> join_node
        branch_2 -> join_node

    情况 2：
        decision -> branch_1 -> join_node
        decision -> branch_2

    修复为：
        branch_2 -> join_node
    """
    def norm(text) -> str:
        if text is None:
            return ""
        return str(text).replace(" ", "").replace("\n", "").replace("\t", "")


    def is_feedback_branch_node(node) -> bool:
        """
        判断一个分支节点是否属于反馈/异常处理分支。
        这类节点不应该被自动汇合到普通成功路径。
        """
        text = norm(node.text)

        feedback_keywords = [
            "修复",
            "重试",
            "重新",
            "返回",
            "补全",
            "补充",
            "提示用户",
            "错误",
            "失败",
            "异常",
            "不能",
            "无法",
            "不合法",
            "不完整",
            "不通过",
        ]

        return any(keyword in text for keyword in feedback_keywords)

    node_by_id = {node.id: node for node in spec.nodes}
    node_index = {node.id: index for index, node in enumerate(spec.nodes)}

    outgoing = {}
    incoming = {}

    for edge in spec.edges:
        outgoing.setdefault(edge.source, []).append(edge)
        incoming.setdefault(edge.target, []).append(edge)

    existing_pairs = {(edge.source, edge.target) for edge in spec.edges}

    new_edges = []
    remove_edge_ids = set()

    for node in spec.nodes:
        if node.kind != "decision":
            continue

        decision_edges = outgoing.get(node.id, [])

        branch_edges = [
            edge for edge in decision_edges
            if edge.target in node_by_id
        ]

        if len(branch_edges) < 2:
            continue

        # 情况 1：decision 直接连到了一个无 label 的后续公共节点
        possible_join_edges = [
            edge for edge in branch_edges
            if not (edge.label or "").strip()
        ]

        labeled_branch_edges = [
            edge for edge in branch_edges
            if (edge.label or "").strip()
        ]

        for join_edge in possible_join_edges:
            join_target = join_edge.target

            leaf_branch_targets = []

            for edge in branch_edges:
                target_node = node_by_id.get(edge.target)

                if target_node is None:
                    continue

                # 已经有出边，不是 leaf
                if outgoing.get(edge.target):
                    continue

                # 修复、重试、返回、重新编译这类反馈分支，不参与普通汇合
                if is_feedback_branch_node(target_node):
                    continue

                leaf_branch_targets.append(edge.target)

            if len(leaf_branch_targets) >= 2:
                remove_edge_ids.add(id(join_edge))

                for branch_target in leaf_branch_targets:
                    if (branch_target, join_target) not in existing_pairs:
                        new_edges.append(
                            type(join_edge)(
                                source=branch_target,
                                target=join_target,
                                label=""
                            )
                        )
                        existing_pairs.add((branch_target, join_target))

        # 情况 2：多个分支中，有的分支已经连到后续节点，有的分支没出边
        branch_targets = [edge.target for edge in branch_edges]

        branch_next_targets = []
        leaf_branch_targets = []

        for branch_target in branch_targets:
            branch_node = node_by_id.get(branch_target)

            if branch_node is None:
                continue

            # 反馈/异常分支不参与普通汇合
            if is_feedback_branch_node(branch_node):
                continue

            branch_outgoing = outgoing.get(branch_target, [])

            if not branch_outgoing:
                leaf_branch_targets.append(branch_target)
            else:
                first_next = branch_outgoing[0].target

                if first_next in node_by_id:
                    branch_next_targets.append(first_next)

        if leaf_branch_targets and branch_next_targets:
            join_target = branch_next_targets[0]

            for branch_target in leaf_branch_targets:
                if (branch_target, join_target) not in existing_pairs:
                    new_edges.append(
                        type(branch_edges[0])(
                            source=branch_target,
                            target=join_target,
                            label=""
                        )
                    )
                    existing_pairs.add((branch_target, join_target))
                # 情况 3：
        # pre_node -> decision
        # decision -> branch_1
        # decision -> branch_2
        # pre_node -> join_node
        #
        # 修复为：
        # branch_1 -> join_node
        # branch_2 -> join_node
        #
        # 典型错误：
        # 用户输入 -> JSON 是否完整？
        # 流程类型？ -> linear extractor
        # 流程类型？ -> branch extractor
        #
        # 正确：
        # linear extractor -> JSON 是否完整？
        # branch extractor -> JSON 是否完整？

        branch_targets = [edge.target for edge in branch_edges]

        leaf_branch_targets = []

        for branch_target in branch_targets:
            branch_node = node_by_id.get(branch_target)

            if branch_node is None:
                continue

            # 修复、返回、重试等反馈分支不参与普通汇合
            if is_feedback_branch_node(branch_node):
                continue

            # 只处理没有出边的分支动作
            if outgoing.get(branch_target):
                continue

            leaf_branch_targets.append(branch_target)

        if len(leaf_branch_targets) >= 2:
            decision_in_edges = incoming.get(node.id, [])

            for decision_in_edge in decision_in_edges:
                pre_node_id = decision_in_edge.source

                bypass_edges = []

                for edge in outgoing.get(pre_node_id, []):
                    # 保留 pre_node -> decision
                    if edge.target == node.id:
                        continue

                    # 不连接到 branch 自身
                    if edge.target in branch_targets:
                        continue

                    target_node = node_by_id.get(edge.target)

                    if target_node is None:
                        continue

                    # 目标必须在分支节点之后，否则不像共同后续步骤
                    target_index = node_index.get(edge.target, -1)
                    max_branch_index = max(
                        node_index.get(branch_target, -1)
                        for branch_target in leaf_branch_targets
                    )

                    if target_index <= max_branch_index:
                        continue

                    # 反馈/异常节点不作为普通共同后续步骤
                    if is_feedback_branch_node(target_node):
                        continue

                    bypass_edges.append(edge)

                if not bypass_edges:
                    continue

                # 选择最近的共同后续步骤
                join_edge = min(
                    bypass_edges,
                    key=lambda edge: node_index.get(edge.target, 999999)
                )

                join_target = join_edge.target

                # 删除 pre_node -> join_node 这条绕过分支的错误边
                remove_edge_ids.add(id(join_edge))

                # 补 branch -> join_node
                for branch_target in leaf_branch_targets:
                    if (branch_target, join_target) not in existing_pairs:
                        new_edges.append(
                            type(join_edge)(
                                source=branch_target,
                                target=join_target,
                                label=""
                            )
                        )
                        existing_pairs.add((branch_target, join_target))

    spec.edges = [
        edge for edge in spec.edges
        if id(edge) not in remove_edge_ids
    ]

    spec.edges.extend(new_edges)

    return spec

    def add_edge(source: str, target: str, label: str = "返回"):
        """
        作用：
        添加一条新的边。
        默认 label 使用“返回”，这样 to_mermaid() 会把它渲染成虚线。
        """
        if (source, target) not in existing_edges:
            if not spec.edges:
                return

            edge_model = type(spec.edges[0])

            spec.edges.append(
                edge_model(
                    source=source,
                    target=target,
                    label=label,
                )
            )

            existing_edges.add((source, target))
            outgoing_sources.add(source)

    def find_previous_input_node(current_index: int):
        """
        作用：
        从当前节点往前找最近的“真实输入节点”。

        注意：
        这里不能只根据 node.kind == "input_output" 判断。
        因为 input_output 既可能是输入节点，也可能是输出/提示节点。

        真实输入节点示例：
        - 用户输入账号和密码
        - 用户提交流程图生成需求
        - 用户输入 API 请求参数

        非输入节点示例：
        - 提示用户补充登录信息
        - 提示用户重新输入
        - 输出给用户
        - 显示欢迎信息
        """

        input_keywords = [
            "用户输入",
            "用户提交",
            "读取用户输入",
            "输入账号",
            "输入参数",
            "提交需求",
            "提交流程",
            "上传",
        ]

        output_like_keywords = [
            "提示",
            "输出",
            "显示",
            "生成成功",
            "欢迎信息",
            "结果摘要",
        ]

        for i in range(current_index - 1, -1, -1):
            node = spec.nodes[i]
            text = node.text or ""

            if node.kind != "input_output":
                continue

            # 排除提示/输出类 input_output，避免返回到“提示用户补充信息”
            if any(keyword in text for keyword in output_like_keywords):
                continue

            # 只返回真正的输入类节点
            if any(keyword in text for keyword in input_keywords):
                return node

        return None

    def find_previous_json_decision(current_index: int):
        """
        作用：
        从当前节点往前找最近的 JSON 检查 decision 节点。
        用于修复：
        调用 JSON 修复模块 --> JSON 是否符合规范？
        """
        for i in range(current_index - 1, -1, -1):
            node = spec.nodes[i]
            text = node.text

            if node.kind == "decision" and "JSON" in text:
                return node

        return None

    for index, node in enumerate(spec.nodes):
        text = node.text

        # 情况 1：
        # 提示重新输入 / 返回输入阶段
        # 如果没有出边，则自动回到最近的输入节点
        if (
            "重新输入" in text or "返回输入阶段" in text
        ) and node.id not in outgoing_sources:
            target_node = find_previous_input_node(index)

            if target_node:
                add_edge(node.id, target_node.id, label="返回")

        # 情况 2：
        # JSON 修复模块后应该回到 JSON 检查 decision 节点
        if (
            "JSON 修复" in text or "修复模块" in text
        ) and node.id not in outgoing_sources:
            target_node = find_previous_json_decision(index)

            if target_node:
                add_edge(node.id, target_node.id, label="返回")

    return spec