import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from models.branch_flow_spec import BranchFlowSpec


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"


def extract_branch_flow(user_input: str) -> BranchFlowSpec:
    prompt = f"""
你是一个专业的流程图结构抽取器。

你的任务是：把用户输入的自然语言流程，转换成清晰、完整、适合 Mermaid 绘制的流程图 JSON。

非常重要：
你只能输出 JSON。
不要输出解释。
不要输出 Markdown。
不要输出思考过程。
不要在 JSON 外添加任何文字。

====================
JSON 输出格式
====================

必须输出如下结构：

{{
  "diagram_type": "flowchart",
  "direction": "TD",
  "nodes": [
    {{
      "id": "A",
      "text": "开始",
      "kind": "start_end"
    }}
  ],
  "edges": [
    {{
      "source": "A",
      "target": "B",
      "label": ""
    }}
  ]
}}
====================
重要禁止规则
====================

1. 不要把“是”“否”“成功”“失败”“通过”“不通过”“正确”“错误”单独生成为节点。
   这些词只能作为 decision 节点连线上的 label。

错误示例：
{{
  "id": "E",
  "text": "是",
  "kind": "process"
}}

正确示例：
{{
  "source": "C",
  "target": "D",
  "label": "是"
}}

2. 不要为同一个判断生成两个 decision 节点。

错误示例：
一个节点写“系统判断输入是否为空”，另一个节点写“输入为空？”

正确示例：
只生成一个 decision 节点：
{{
  "id": "C",
  "text": "输入是否为空？",
  "kind": "decision"
}}

3. decision 节点的 text 必须尽量写成问题形式，例如：
- 输入是否为空？
- JSON 是否符合规范？
- 是否继续修改？

4. 每个 decision 节点必须至少有两个出口。
   常见出口 label 为：
   - 是 / 否
   - 成功 / 失败
   - 通过 / 不通过
   - 正确 / 错误

5. 如果流程中出现“重新输入”“重新上传”“再次检查”“重新尝试”“返回输入阶段”等含义，必须生成回边。
   例如：
   提示重新输入 --> 输入业务描述
   JSON 修复模块 --> JSON 是否符合规范？
====================
分支生成规则
====================

当用户输入中出现“如果 A，则 B；如果不是 A，则 C”时：

1. 生成一个 decision 节点表示条件 A。
2. 生成两条从该 decision 节点出发的边。
3. 第一条边 label 为“是”，连接到 B。
4. 第二条边 label 为“否”，连接到 C。
5. 不要额外生成“是”节点或“否”节点。

示例：

用户输入：
如果输入为空，则提示重新输入；如果不为空，则调用流程抽取模块。

正确 JSON 结构应该是：

nodes:
- 输入是否为空？ decision
- 提示重新输入 process
- 调用流程抽取模块 process

edges:
- 输入是否为空？ -->|是| 提示重新输入
- 输入是否为空？ -->|否| 调用流程抽取模块

====================
节点规则
====================

1. diagram_type 固定为 "flowchart"。
2. direction 默认使用 "TD"。
3. nodes 是节点列表。
4. edges 是连线列表。
5. 每个节点必须包含 id、text、kind。
6. id 按顺序使用 A、B、C、D、E、F。
7. kind 只能是以下五种：

1. start_end
用于开始、结束、终止、完成等节点。

2. process
用于普通处理步骤，例如分析需求、清洗数据、生成结果、更新状态。

3. decision
用于判断条件，例如是否为空、是否成功、是否通过、是否符合规范、是否继续修改。
decision 节点的 text 必须尽量写成问题形式。

4. input_output
用于输入、输出、读取、写入、上传、下载、导出、保存、展示、提示等数据流相关步骤。

例如：
- 用户输入业务描述
- 读取配置文件
- 上传文件
- 保存结果
- 展示流程图
- 提示重新输入

5. subroutine
用于调用函数、调用模块、调用工具、调用 Agent、运行程序、执行子流程等步骤。

例如：
- 调用流程抽取模块
- 调用 JSON 修复模块
- 调用 Mermaid 渲染模块
- 调用代码 Agent
- 运行 Monte Carlo 仿真程序

节点类型选择优先级：
1. 如果一个节点同时符合多个类型，按照以上优先级选择最靠前的 kind。
2. 如果表示开始、结束、终止、完成，使用 start_end。
3. 如果表示是否、判断、检查是否、成功/失败、通过/不通过，使用 decision。
4. 如果表示调用模块、调用函数、调用 Agent、调用工具、运行程序、执行子流程，使用 subroutine。
5. 如果表示输入、输出、读取、写入、上传、下载、导出、保存、展示、提示，使用 input_output。
6. 其他普通动作使用 process。
====================
步骤拆分规则
====================

1. 每个节点只表达一个动作或一个判断，不要把多个动作塞进同一个节点。
2. 如果用户输入中包含多个连续动作，必须拆成多个 process 节点。
3. 如果用户输入中出现“如果、是否、判断、检查、满足、不满足、成功、失败、通过、不通过”等含义，必须生成 decision 节点。
4. decision 节点的 text 应该写成问题形式，例如：
   - 是否通过检查？
   - 是否满足条件？
   - 是否需要重新输入？
5. decision 节点通常至少有两条 outgoing edges，并且边上必须有 label，例如：
   - 是
   - 否
   - 成功
   - 失败
   - 通过
   - 不通过

====================
连线规则
====================

1. 每条边必须包含 source、target、label。
2. 普通顺序流程的 label 可以为空字符串 ""。
3. 从 decision 节点出发的边，label 不能为空。
4. 不要生成孤立节点，每个非开始节点都应该能从开始节点到达。
5. 不要生成没有意义的跳跃连接。
6. 如果流程有循环，例如“重新输入、返回检查、重新处理”，需要用边连接回前面的相关节点。

====================
清晰度规则
====================

1. 节点文字要简洁，但不能过度省略。
2. 优先使用动宾结构，例如：
   - 输入用户需求
   - 检查输入格式
   - 生成流程图结构
   - 输出 Mermaid 代码
3. 不要使用含糊文字，例如：
   - 处理
   - 操作
   - 进行下一步
4. 如果用户输入不完整，也要根据上下文补全合理流程，但不要编造无关步骤。

====================
回边强制规则
====================

1. 如果某个节点的 text 包含“重新输入”“重新上传”“重新检查”“再次检查”“再次尝试”“返回输入阶段”“返回上一步”等含义，该节点不能作为终点。

2. 这类节点后面必须有一条边连接回前面相关节点。

3. 回边目标选择规则：
   - “重新输入”或“返回输入阶段”必须连接回输入节点。
   - “重新上传”必须连接回上传节点。
   - “重新检查”或“再次检查”必须连接回对应的检查/判断节点。
   - “再次尝试解析”必须连接回解析节点。
   - “修复 JSON 后再次检查”必须连接回 JSON 是否符合规范的 decision 节点。

4. 示例：
   提示重新输入 --> 用户输入业务描述
   调用 JSON 修复模块 --> JSON 是否符合规范？
   返回输入阶段 --> 用户输入业务描述

特别注意：
如果节点 text 是“提示重新输入”“提示用户重新输入”“重新输入”，该节点必须连接回最近的用户输入节点。
例如：
提示重新输入 --> 用户输入业务描述
错误示例：
nodes:
D: 提示重新输入
但是 edges 中没有 D 的出边。

正确示例：
{{
  "source": "D",
  "target": "B",
  "label": ""
}}

含义：
提示重新输入后，流程必须回到“用户输入业务描述”节点。

====================
步骤保留规则
====================

1. 不要省略用户输入、系统读取、上传文件、提交申请、保存结果、展示结果等明确动作。
2. 如果用户文本中出现“用户输入……后，系统判断……”，必须先生成“用户输入……” process 节点，再生成 decision 节点。
3. 不要直接从开始节点连接到判断节点，除非原文没有任何前置动作。

====================
结束节点规则
====================

1. 如果节点 text 包含“结束”“结束流程”“终止”“完成”“流程结束”，kind 必须是 start_end。
2. 结束节点通常不需要出边。

====================
用户输入
====================
{user_input}
"""

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

    data = json.loads(raw_json)
    branch_spec = BranchFlowSpec.model_validate(data)

    branch_spec = repair_missing_back_edges(branch_spec)

    return branch_spec


class BranchFlowExtractor:
    def __init__(self, branch_diagram: Any):
        self.diagram = self._to_dict(branch_diagram)
        self.nodes = self.diagram.get("nodes", [])
        self.edges = self.diagram.get("edges", [])
        self.direction = self.diagram.get("direction", "TD")
        self.spec = branch_diagram

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        if isinstance(obj, dict):
            return obj

        if hasattr(obj, "model_dump"):
            return obj.model_dump()

        if hasattr(obj, "dict"):
            return obj.dict()

        raise TypeError("Unsupported branch diagram type. Expected dict or Pydantic model.")

    def _escape_text(self, text: Optional[str]) -> str:
        if text is None:
            return ""
        return str(text).replace('"', '\\"')

    def to_mermaid(self) -> str:
        lines = [
        '%%{init: {"flowchart": {"defaultRenderer": "elk"}}}%%',
        f"flowchart {self.direction}"
        ]

    # 1. 节点
        for node in self.nodes:
            node_id = node["id"]
            text = self._escape_text(node["text"])
            kind = node["kind"]

            if kind == "decision":
                lines.append(f'{node_id}{{"{text}"}}')

            elif kind == "start_end":
                lines.append(f'{node_id}(["{text}"])')

            elif kind == "input_output":
                lines.append(f'{node_id}[/"{text}"/]')

            elif kind == "subroutine":
                lines.append(f'{node_id}[["{text}"]]')

            else:
                lines.append(f'{node_id}["{text}"]')

        lines.append("")

        # 2. 边
        for edge in self.edges:
            source = edge["source"]
            target = edge["target"]
            label = edge.get("label")

            if label:
                label = self._escape_text(label)

                if label == "返回":
                    lines.append(f"{source} -.->|{label}| {target}")
                else:
                    lines.append(f"{source} -->|{label}| {target}")
            else:
                lines.append(f"{source} --> {target}")

        return "\n".join(lines)
#add a new function for automatically repair
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

    def add_edge(source: str, target: str, label: str = ""):
        if (source, target) not in existing_edges:
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
        for i in range(current_index - 1, -1, -1):
            node = spec.nodes[i]
            text = node.text

            if node.kind == "input_output" and (
                "输入" in text or "上传" in text or "提交" in text
            ):
                return node

        return None

    def find_previous_json_decision(current_index: int):
        for i in range(current_index - 1, -1, -1):
            node = spec.nodes[i]
            text = node.text

            if node.kind == "decision" and "JSON" in text:
                return node

        return None

    for index, node in enumerate(spec.nodes):
        text = node.text

        # 情况 1：提示重新输入 / 返回输入阶段
        if (
            "重新输入" in text or "返回输入阶段" in text
        ) and node.id not in outgoing_sources:
            target_node = find_previous_input_node(index)

            if target_node:
                add_edge(node.id, target_node.id)

        # 情况 2：JSON 修复后应该回到 JSON 检查
        if (
            "JSON 修复" in text or "修复模块" in text
        ) and node.id not in outgoing_sources:
            target_node = find_previous_json_decision(index)

            if target_node:
                add_edge(node.id, target_node.id)

    return spec