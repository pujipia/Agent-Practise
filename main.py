import json
import urllib.request

from builders.flowchart_builder import build_flowchart_from_linear
from compilers.flowchart_compiler import compile_flowchart
from models.linear_flow_spec import LinearFlowSpec


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"

prompt = """
你是一个流程抽取器。

请把用户输入提取成 JSON。
不要解释，不要输出思考过程。
只能返回符合 schema 的 JSON。

规则：
1. steps 是按执行顺序排列的步骤列表。
2. text 只保留核心步骤名称，不要保留连接词或说明词。
3. 删除类似“起点是”“开始是”“然后到”“然后”“终点是”“结束是”等表达。
4. role 只能是 start、process、decision、end。
5. 起点/开始类步骤用 start。
6. 普通动作步骤用 process。
7. 判断/是否/检查类步骤用 decision。
8. 终点/结束类步骤用 end。

示例：
用户输入：起点是开始，然后到读取，终点是下载
输出：
{"steps":[{"text":"开始","role":"start"},{"text":"读取","role":"process"},{"text":"下载","role":"end"}]}

现在处理这个用户输入：
起点是开始，然后到读取，终点是下载
"""

payload = {
    "model": MODEL_NAME,
    "prompt": prompt,
    "stream": False,
    "format": LinearFlowSpec.model_json_schema(),
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

with urllib.request.urlopen(request, timeout=120) as response:
    result = json.loads(response.read().decode("utf-8"))

raw_json = result["response"]

print("Ollama 返回的 JSON：")
print(raw_json)

data = json.loads(raw_json)
linear_spec = LinearFlowSpec.model_validate(data)

print("\nPydantic 校验后的结果：")
print(linear_spec)

flowchart_spec = build_flowchart_from_linear(linear_spec)
mermaid_code = compile_flowchart(flowchart_spec)

print("\n生成的 Mermaid 代码：")
print(mermaid_code)
from pathlib import Path

diagram_dir = Path("diagrams")
diagram_dir.mkdir(exist_ok=True)

output_path = diagram_dir / "flowchart.mmd"
output_path.write_text(mermaid_code, encoding="utf-8")

print(f"\n已保存到：{output_path}")