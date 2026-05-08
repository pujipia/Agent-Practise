import json
import re
import urllib.error
import urllib.request
from pathlib import Path
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
# Part 2. Prompt 文件路径
# 作用：
# 1. 优先读取 prompts/flowchart/branch_flow.md
# 2. 如果文件不存在，则使用代码内置 fallback prompt
# 3. 这样既兼容你之前做的 Prompt 分离，也避免路径问题导致程序崩溃
# ============================================================

BRANCH_PROMPT_PATH = Path("prompts") / "flowchart" / "branch_flow.md"


def _load_branch_prompt_template() -> str:
    """
    读取 branch flow prompt 模板。

    优先读取：
    prompts/flowchart/branch_flow.md

    如果文件不存在，则使用内置 fallback prompt。
    """

    if BRANCH_PROMPT_PATH.exists():
        return BRANCH_PROMPT_PATH.read_text(encoding="utf-8")

    return """
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
4. kind 只能是 start_end、process、decision、input_output、subroutine。
5. 开始节点和结束节点使用 start_end。
6. 普通动作、操作、处理步骤使用 process。
7. 判断、是否、检查、验证、校验、如果、若、条件类节点使用 decision。
8. 用户输入、上传、输出、提示类节点优先使用 input_output。
9. 调用模块、调用函数、调用 Agent、调用工具类节点优先使用 subroutine。

连线规则：
1. 普通顺序边 label 为 null 或空字符串。
2. decision 节点如果有两个结果，必须生成两条边。
3. 每条 decision 分支边必须有 label。
4. label 应尽量使用用户原文中的条件，例如：完整、不完整、支持、不支持、通过、不通过、成功、失败。
5. 如果流程中出现“返回”“重新输入”“重新上传”“补充材料”“退回修改”，边的 target 应该指向之前对应的输入或提交节点。
6. 不要把所有节点简单串成一条线。
7. 判断节点必须分叉。
8. 所有 edge 的 source 和 target 必须来自 nodes 里已经存在的 id。
9. 不要生成孤立节点。
10. 不允许出现 source 或 target 为空字符串的 edge。
11. 不要把“通过 / 不通过 / 成功 / 失败”单独作为节点，它们应该作为 edge.label。

示例：
用户输入：
用户上传文件。系统检查文件格式是否支持。如果支持，则调用文件解析模块。如果不支持，则提示用户重新上传。

输出：
{
  "diagram_type": "flowchart",
  "direction": "TD",
  "nodes": [
    {"id": "A", "text": "开始", "kind": "start_end"},
    {"id": "B", "text": "用户上传文件", "kind": "input_output"},
    {"id": "C", "text": "文件格式是否支持？", "kind": "decision"},
    {"id": "D", "text": "调用文件解析模块", "kind": "subroutine"},
    {"id": "E", "text": "提示用户重新上传", "kind": "input_output"},
    {"id": "F", "text": "结束", "kind": "start_end"}
  ],
  "edges": [
    {"source": "A", "target": "B", "label": null},
    {"source": "B", "target": "C", "label": null},
    {"source": "C", "target": "D", "label": "支持"},
    {"source": "C", "target": "E", "label": "不支持"},
    {"source": "D", "target": "F", "label": null},
    {"source": "E", "target": "B", "label": "返回"}
  ]
}

现在处理这个用户输入：
__USER_INPUT__
"""


def build_branch_prompt(user_input: str) -> str:
    """
    构建第一次普通 branch flow 抽取 prompt。

    输入：
    user_input：当前流程片段的自然语言文本

    输出：
    填充后的 prompt 字符串
    """

    template = _load_branch_prompt_template()

    if "__USER_INPUT__" in template:
        return template.replace("__USER_INPUT__", user_input)

    # 兼容旧 prompt 文件：如果旧文件没有占位符，就把用户输入追加到最后
    return template + f"\n\n现在处理这个用户输入：\n{user_input}\n"


# ============================================================
# Part 3. Ollama 调用与 JSON 清洗
# 作用：
# 1. 统一调用 Ollama
# 2. 清洗 DeepSeek 可能输出的 <think>、Markdown 代码块等内容
# 3. 把模型输出转换成 BranchFlowSpec
# ============================================================

def _call_ollama(prompt: str, timeout: int = 180) -> str:
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
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama 请求失败，请检查 Ollama 是否已启动：{e}")

    except TimeoutError:
        raise RuntimeError("Ollama 请求超时，请检查模型是否正在运行或输入是否过长。")

    return result["response"]


def clean_json_text(raw_text: str) -> str:
    """
    清洗模型输出。

    作用：
    1. 去掉 DeepSeek 可能输出的 <think>...</think>
    2. 去掉 ```json / ``` 代码块
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


def _parse_branch_response(raw_json: str) -> BranchFlowSpec:
    """
    将模型原始输出解析成 BranchFlowSpec。

    处理流程：
    1. 清洗模型输出
    2. json.loads 转成 dict
    3. 补充 diagram_type / direction 默认字段
    4. 用 BranchFlowSpec 做结构校验
    """

    cleaned_json = clean_json_text(raw_json)

    try:
        data = json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Branch Extractor 返回内容不是合法 JSON：{e}\n原始输出：\n{raw_json}"
        )

    # 兜底：如果模型漏掉 diagram_type / direction，就补默认值
    data.setdefault("diagram_type", "flowchart")
    data.setdefault("direction", "TD")

    return BranchFlowSpec.model_validate(data)


# ============================================================
# Part 4. Branch Flow 普通抽取
# 作用：
# 1. 第一次根据用户输入抽取 BranchFlowSpec
# 2. main.py 中正常调用 extract_branch_flow()
# ============================================================

def extract_branch_flow(user_input: str) -> BranchFlowSpec:
    """
    第一次普通 branch flow 抽取。

    输入：
    user_input：当前流程片段文本

    输出：
    BranchFlowSpec
    """

    prompt = build_branch_prompt(user_input)

    raw_json = _call_ollama(prompt)

    print("\nOllama 返回的 branch JSON：")
    print(raw_json)

    return _parse_branch_response(raw_json)


# ============================================================
# Part 5. Branch Flow Retry
# 作用：
# 1. 当第一次 branch JSON 未通过 validator 时，构建更强的 retry prompt
# 2. 把 errors 和上一次错误 JSON 一起交给模型
# 3. 重新生成一次 BranchFlowSpec
# ============================================================

def build_branch_retry_prompt(
    user_input: str,
    errors: list[str],
    previous_diagram: Optional[BranchFlowSpec] = None,
    decomposition_spec: Optional[Any] = None,
) -> str:
    """
    构建 branch retry prompt。

    这次 retry 不只依赖原始输入和上一次错误 JSON，
    还会参考 Decomposition Agent 的结构化 flows。
    """

    error_text = "\n".join(f"- {error}" for error in errors)

    if previous_diagram is not None:
        previous_json = json.dumps(
            previous_diagram.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    else:
        previous_json = "{}"

    if decomposition_spec is not None:
        if hasattr(decomposition_spec, "model_dump"):
            decomposition_data = decomposition_spec.model_dump()
        else:
            decomposition_data = decomposition_spec

        decomposition_json = json.dumps(
            decomposition_data,
            ensure_ascii=False,
            indent=2,
        )
    else:
        decomposition_json = "{}"

    return f"""
你是一个分支流程图 JSON 修复器。

你的任务：
根据用户原始输入、Decomposition Agent 的结构化拆解结果、上一次错误 JSON 和校验错误，
重新生成完整、合法、可通过校验的 branch JSON。

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

允许的 node.kind：
1. start_end
2. process
3. decision
4. input_output
5. subroutine

====================
用户原始输入
====================

{user_input}

====================
Decomposition Agent 结构化参考
====================

下面的 decomposition flows 是本次修复最重要的参考。
你必须尽量把每一条 flow 转换成 branch JSON 里的 edge。
如果 flow.condition 不为空，它应该作为 edge.label。

{decomposition_json}

====================
上一次 branch JSON 校验错误
====================

{error_text}

====================
上一次错误 branch JSON
====================

{previous_json}

====================
强制修复规则
====================

1. 每个 decision 节点必须至少有两个出口。
2. 每个“如果 A，则 B；如果非 A，则 C”必须生成两条 edge。
3. Decomposition Agent 的每一条 flows 都应尽量被保留为 branch edge。
4. flow.condition 应该作为 edge.label。
5. 不允许出现 source 或 target 为空字符串的 edge。
6. 不允许遗漏最后一个 decision 节点的任意分支。
7. 如果出现“退回修改”“重新输入”“重新上传”“补充材料”，应连接回合理的前置输入或提交节点。
8. 不要把“通过 / 不通过 / 成功 / 失败 / 完整 / 不完整”单独作为节点，它们应该作为 edge.label。
9. 如果上一次某个 decision 节点只有一个出口，本次必须补全另一个出口。
10. 如果 Decomposition flows 中存在：
    专家判断项目 -> 退回给用户修改 [评审不通过]
    专家判断项目 -> 生成审批结果 [评审通过]
    那么 branch JSON 中必须保留这两条分支边。

只输出 JSON。
"""

def extract_branch_flow_with_retry(
    user_input: str,
    errors: list[str],
    previous_diagram: Optional[BranchFlowSpec] = None,
    decomposition_spec: Optional[Any] = None,
) -> BranchFlowSpec:
    """
    当第一次 branch 抽取校验失败时，使用更强 prompt 重试一次。

    这版 retry 会额外参考 Decomposition Agent 的 flows。
    """

    retry_prompt = build_branch_retry_prompt(
        user_input=user_input,
        errors=errors,
        previous_diagram=previous_diagram,
        decomposition_spec=decomposition_spec,
    )

    raw_json = _call_ollama(retry_prompt)

    print("\nBranch retry 返回的 branch JSON：")
    print(raw_json)

    return _parse_branch_response(raw_json)

class BranchFlowExtractor:
    """
    将 BranchFlowSpec 转换成 Mermaid flowchart。
    """

    def __init__(self, branch_diagram: Any):
        self.diagram = self._to_dict(branch_diagram)
        self.nodes = self.diagram.get("nodes", [])
        self.edges = self.diagram.get("edges", [])
        self.direction = self.diagram.get("direction", "TD")

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """
        把 Pydantic model 或 dict 统一转成 dict。
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
        转义 Mermaid 节点文本。
        """

        if text is None:
            return ""

        return str(text).replace('"', '\\"').replace("\n", " ")

    def _is_return_edge(self, label: Optional[str]) -> bool:
        """
        判断一条边是否是返回 / 重试类边。
        返回边在 Mermaid 中用虚线显示。
        """

        if not label:
            return False

        label_text = str(label)

        return any(
            keyword in label_text
            for keyword in ["返回", "重新", "重试", "回到", "退回", "补充"]
        )

    def _render_node(self, node: Dict[str, Any]) -> str:
        """
        根据 node.kind 渲染 Mermaid 节点形状。
        """

        node_id = node.get("id", "")
        text = self._escape_text(node.get("text", ""))
        kind = node.get("kind", "process")

        if kind == "start_end":
            return f'{node_id}(["{text}"])'

        if kind == "decision":
            return f'{node_id}{{"{text}"}}'

        if kind == "input_output":
            return f'{node_id}[/"{text}"/]'

        if kind == "subroutine":
            return f'{node_id}[["{text}"]]'

        # 默认普通 process
        return f'{node_id}["{text}"]'

    def _render_edge(self, edge: Dict[str, Any]) -> Optional[str]:
        """
        渲染 Mermaid 连线。
        如果 source 或 target 为空，则跳过该边，避免 Mermaid 渲染失败。
        """

        source = edge.get("source")
        target = edge.get("target")
        label = edge.get("label")

        if not source or not target:
            print(f"[cleanup] skip invalid edge with empty source/target: {source} -> {target}")
            return None

        if label:
            label = self._escape_text(label)

            if self._is_return_edge(label):
                return f"{source} -.->|{label}| {target}"

            return f"{source} -->|{label}| {target}"

        return f"{source} --> {target}"

    def to_mermaid(self) -> str:
        """
        输出 Mermaid flowchart 字符串。
        """

        lines = [
            '%%{init: {"flowchart": {"defaultRenderer": "elk"}}}%%',
            f"flowchart {self.direction}",
        ]

        for node in self.nodes:
            lines.append(self._render_node(node))

        lines.append("")

        for edge in self.edges:
            rendered_edge = self._render_edge(edge)

            if rendered_edge:
                lines.append(rendered_edge)

        return "\n".join(lines)