import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from models.branch_flow_spec import BranchFlowSpec


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"


def build_branch_prompt(user_input: str, previous_error: str | None = None) -> str:
    """
    构建 branch flow 抽取 prompt。
    支持长流程、多判断、多分支、回退路径。
    """

    error_part = ""
    if previous_error:
        error_part = f"""
上一次输出有错误，请修正。

错误信息：
{previous_error}

请重新输出严格合法的 JSON。
"""

    return f"""
你是一个分支流程图抽取器。

你的任务：把用户输入转换成流程图结构 JSON。

你必须只输出 JSON。
不要解释。
不要输出 Markdown。
不要输出 ```json。
不要输出思考过程。

JSON 必须包含：
1. diagram_type，固定为 "flowchart"
2. direction，默认 "TD"
3. nodes，节点列表
4. edges，连线列表

节点规则：
1. 每个节点必须有 id、text、kind。
2. id 按顺序使用 A、B、C、D、E...Z。
3. 如果节点超过 26 个，继续使用 N1、N2、N3。
4. kind 只能是 start_end、process、decision。
5. 开始节点和结束节点使用 start_end。
6. 普通动作、操作、处理步骤使用 process。
7. 判断、是否、检查、验证、校验、如果、若、条件类节点使用 decision。

连线规则：
1. 普通顺序边 label 为 null。
2. decision 节点如果有两个结果，必须生成两条边。
3. 正确、通过、成功、是、满足条件路径，label 用 "是" 或 "通过"。
4. 不正确、不通过、失败、否、不满足条件、否则路径，label 用 "否" 或 "不通过"。
5. 如果流程中出现“返回”“重新输入”“回到上一步”，边的 target 应该指向之前对应的节点。
6. 不要把所有节点简单串成一条线。
7. 判断节点必须分叉。
8. 所有 edge 的 source 和 target 必须来自 nodes 里已经存在的 id。
9. 不要生成孤立节点。

示例一：
用户输入：
上传文件后检查格式是否正确，如果正确就生成报告，如果不正确就提示错误

输出：
{{
  "diagram_type": "flowchart",
  "direction": "TD",
  "nodes": [
    {{"id": "A", "text": "上传文件", "kind": "process"}},
    {{"id": "B", "text": "检查格式是否正确", "kind": "decision"}},
    {{"id": "C", "text": "生成报告", "kind": "process"}},
    {{"id": "D", "text": "提示错误", "kind": "process"}}
  ],
  "edges": [
    {{"source": "A", "target": "B", "label": null}},
    {{"source": "B", "target": "C", "label": "是"}},
    {{"source": "B", "target": "D", "label": "否"}}
  ]
}}

示例二：
用户输入：
用户输入账号密码，系统检查密码是否正确。如果不正确，提示错误并返回重新输入账号密码。如果正确，进入验证码验证。系统检查验证码是否通过，如果通过进入主页，如果不通过则重新输入验证码。

输出：
{{
  "diagram_type": "flowchart",
  "direction": "TD",
  "nodes": [
    {{"id": "A", "text": "用户输入账号密码", "kind": "process"}},
    {{"id": "B", "text": "检查密码是否正确", "kind": "decision"}},
    {{"id": "C", "text": "提示错误", "kind": "process"}},
    {{"id": "D", "text": "进入验证码验证", "kind": "process"}},
    {{"id": "E", "text": "检查验证码是否通过", "kind": "decision"}},
    {{"id": "F", "text": "进入主页", "kind": "start_end"}},
    {{"id": "G", "text": "重新输入验证码", "kind": "process"}}
  ],
  "edges": [
    {{"source": "A", "target": "B", "label": null}},
    {{"source": "B", "target": "C", "label": "否"}},
    {{"source": "C", "target": "A", "label": null}},
    {{"source": "B", "target": "D", "label": "是"}},
    {{"source": "D", "target": "E", "label": null}},
    {{"source": "E", "target": "F", "label": "通过"}},
    {{"source": "E", "target": "G", "label": "不通过"}},
    {{"source": "G", "target": "E", "label": null}}
  ]
}}

示例三：
用户输入：
客户提交订单，系统检查库存是否充足。如果库存充足，系统生成订单并请求支付。系统判断支付是否成功，如果成功则安排发货并结束，如果失败则取消订单。如果库存不足，则通知客户缺货并结束。

输出：
{{
  "diagram_type": "flowchart",
  "direction": "TD",
  "nodes": [
    {{"id": "A", "text": "客户提交订单", "kind": "process"}},
    {{"id": "B", "text": "检查库存是否充足", "kind": "decision"}},
    {{"id": "C", "text": "生成订单", "kind": "process"}},
    {{"id": "D", "text": "请求支付", "kind": "process"}},
    {{"id": "E", "text": "判断支付是否成功", "kind": "decision"}},
    {{"id": "F", "text": "安排发货", "kind": "process"}},
    {{"id": "G", "text": "订单完成", "kind": "start_end"}},
    {{"id": "H", "text": "取消订单", "kind": "start_end"}},
    {{"id": "I", "text": "通知客户缺货", "kind": "start_end"}}
  ],
  "edges": [
    {{"source": "A", "target": "B", "label": null}},
    {{"source": "B", "target": "C", "label": "是"}},
    {{"source": "C", "target": "D", "label": null}},
    {{"source": "D", "target": "E", "label": null}},
    {{"source": "E", "target": "F", "label": "成功"}},
    {{"source": "F", "target": "G", "label": null}},
    {{"source": "E", "target": "H", "label": "失败"}},
    {{"source": "B", "target": "I", "label": "否"}}
  ]
}}

{error_part}

现在处理这个用户输入：
{user_input}
"""


def call_ollama(prompt: str) -> str:
    """
    调用本地 Ollama。
    返回模型原始 response 字符串。
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
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama 请求失败，请检查 Ollama 是否已启动：{e}")

    except TimeoutError:
        raise RuntimeError("Ollama 请求超时，请检查模型是否正在运行或输入是否过长。")

    return result["response"]


def clean_json_text(raw_text: str) -> str:
    """
    清洗模型输出。
    目的：
    1. 去掉 DeepSeek 可能输出的 <think>...</think>
    2. 去掉 ```json
    3. 从混杂文本中提取 JSON 主体
    """

    text = raw_text.strip()

    # 去掉 deepseek-r1 可能出现的思考标签
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 去掉 markdown 代码块
    text = text.replace("```json", "").replace("```", "").strip()

    # 如果已经是纯 JSON，直接返回
    if text.startswith("{") and text.endswith("}"):
        return text

    # 否则提取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型输出中没有找到合法 JSON 对象。")

    return text[start:end + 1]


def validate_branch_graph(branch_spec: BranchFlowSpec) -> None:
    """
    对 branch flow 做基础结构检查。
    如果有问题，主动抛错，触发重试。
    """

    nodes = branch_spec.nodes
    edges = branch_spec.edges

    if not nodes:
        raise ValueError("nodes 不能为空。")

    if not edges:
        raise ValueError("edges 不能为空。")

    node_ids = [node.id for node in nodes]

    if len(node_ids) != len(set(node_ids)):
        raise ValueError("存在重复的 node id。")

    node_id_set = set(node_ids)

    for edge in edges:
        if edge.source not in node_id_set:
            raise ValueError(f"edge source 不存在：{edge.source}")

        if edge.target not in node_id_set:
            raise ValueError(f"edge target 不存在：{edge.target}")

    decision_ids = [node.id for node in nodes if node.kind == "decision"]

    for decision_id in decision_ids:
        outgoing_edges = [edge for edge in edges if edge.source == decision_id]

        if len(outgoing_edges) < 2:
            raise ValueError(
                f"decision 节点 {decision_id} 至少应该有两条 outgoing edges。"
            )


def extract_branch_flow(user_input: str) -> BranchFlowSpec:
    """
    从用户输入中抽取 branch flow。
    如果第一次模型输出不合法，会自动重试。
    """

    max_attempts = 2
    previous_error = None

    for attempt in range(1, max_attempts + 1):
        prompt = build_branch_prompt(user_input, previous_error)

        raw_json = call_ollama(prompt)

        print(f"\nOllama 返回的 branch JSON，第 {attempt} 次：")
        print(raw_json)

        try:
            cleaned_json = clean_json_text(raw_json)
            data = json.loads(cleaned_json)

            branch_spec = BranchFlowSpec.model_validate(data)

            validate_branch_graph(branch_spec)

            return branch_spec

        except Exception as e:
            previous_error = str(e)

            print(f"\n第 {attempt} 次 branch JSON 解析或校验失败：")
            print(previous_error)

            if attempt == max_attempts:
                raise RuntimeError(
                    "branch flow 抽取失败。模型连续输出了不合法的 JSON 或不合法的流程结构。"
                ) from e

    raise RuntimeError("branch flow 抽取失败。")


class BranchFlowExtractor:
    def __init__(self, branch_diagram: Any):
        self.diagram = self._to_dict(branch_diagram)
        self.nodes = self.diagram.get("nodes", [])
        self.edges = self.diagram.get("edges", [])
        self.direction = self.diagram.get("direction", "TD")

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
        shape_map = {
            "start_end": "stadium",
            "process": "rect",
            "decision": "diamond",
        }

        lines = [f"flowchart {self.direction}"]

        for node in self.nodes:
            node_id = node["id"]
            text = self._escape_text(node["text"])
            kind = node["kind"]

            if kind == "decision":
                lines.append(f'{node_id}{{"{text}"}}')
            elif kind == "start_end":
                lines.append(f'{node_id}(["{text}"])')
            else:
                lines.append(f'{node_id}["{text}"]')

        for edge in self.edges:
            source = edge["source"]
            target = edge["target"]
            label = edge.get("label")

            if label:
                label = self._escape_text(label)
                lines.append(f"{source} -->|{label}| {target}")
            else:
                lines.append(f"{source} --> {target}")

        return "\n".join(lines)