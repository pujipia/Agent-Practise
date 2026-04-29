import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from models.branch_flow_spec import BranchFlowSpec


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"


def extract_branch_flow(user_input: str) -> BranchFlowSpec:
    prompt = f"""
你是一个分支流程图抽取器。

你的任务：把用户输入转换成流程图结构 JSON。

只输出 JSON，不要解释，不要输出思考过程。

JSON 必须包含：
1. diagram_type，固定为 "flowchart"
2. direction，默认 "TD"
3. nodes，节点列表
4. edges，连线列表

节点规则：
1. 每个节点必须有 id、text、kind。
2. id 按顺序使用 A、B、C、D、E、F、G。
3. kind 只能是 start_end、process、decision。
4. 开始/结束节点用 start_end。
5. 普通动作节点用 process。
6. 判断、是否、检查、如果类节点用 decision。

连线规则：
1. 普通顺序边 label 为 null。
2. decision 节点如果有两个结果，必须生成两条边。
3. 正确、通过、成功路径 label 用 "正确" 或 "通过"。
4. 不正确、不通过、失败、否则路径 label 用 "不正确" 或 "不通过"。
5. 不要把所有节点简单串成一条线，判断节点必须分叉。

示例：
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
    {{"source": "B", "target": "C", "label": "正确"}},
    {{"source": "B", "target": "D", "label": "不正确"}}
  ]
}}

现在处理这个用户输入：
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
