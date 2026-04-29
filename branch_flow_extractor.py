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

1. 如果出现“如果……则……；否则……”结构，必须生成一个 decision 节点和两条分支边。
2. 从 decision 节点出发的边必须有 label。
3. 常用 label：
   - 是 / 否
   - 成功 / 失败
   - 通过 / 不通过
   - 正确 / 错误
4. 不要把“是”“否”“成功”“失败”“通过”“不通过”“正确”“错误”生成为节点。
   这些词只能作为 edge 的 label。
5. 不要为同一个判断生成两个 decision 节点。
   例如“系统判断输入是否为空”和“输入是否为空？”只能合并成一个 decision 节点。
6. 每个 decision 节点通常至少有两个出口。

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

返回输入阶段规则：

如果用户文本明确出现“返回输入阶段”，可以生成一个 process 节点：

{
  "id": "K",
  "text": "返回输入阶段",
  "kind": "process"
}

然后连接为：

是否继续修改？ -->|是| 返回输入阶段
返回输入阶段 -->|返回| 用户输入业务描述
是否继续修改？ -->|否| 结束流程

注意：
1. 如果 edges 中使用了“返回输入阶段”节点的 id，必须在 nodes 中创建该节点。
2. “返回输入阶段”节点不是结束节点，它必须有一条回到输入节点的边。
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

    # 自动修复模型可能漏掉的确定性回边
    branch_spec = repair_missing_back_edges(branch_spec)

    # 2. 给已经存在的回边补 label="返回"，用于 Mermaid 虚线显示
    branch_spec = label_existing_back_edges(branch_spec)

    # 3. 删除模型多生成的孤立跳转节点，例如“再次检查”
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
        """
        lines = [
            '%%{init: {"flowchart": {"defaultRenderer": "elk"}}}%%',
            f"flowchart {self.direction}"
        ]

        # 1. 渲染节点
        for node in self.nodes:
            lines.append(self._render_node(node))

        lines.append("")

        # 2. 渲染边
        for edge in self.edges:
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
    
# ============================================================
# Part 7. 自动修复缺失回边
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
        从当前节点往前找最近的输入类节点。

        注意：
        这里按你的要求没有修改优化点 A。
        仍然要求 node.kind == "input_output"。
        """
        for i in range(current_index - 1, -1, -1):
            node = spec.nodes[i]
            text = node.text

            if node.kind == "input_output" and (
                "输入" in text or "上传" in text or "提交" in text
            ):
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