import json
import urllib.request
from pathlib import Path
from processors.role_normalizer import normalize_roles_by_input

from builders.flowchart_builder import build_flowchart_from_linear
from compilers.flowchart_compiler import compile_flowchart
from models.linear_flow_spec import LinearFlowSpec

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"

user_input = input("请输入流程描述：")
prompt = f"""
你是一个流程抽取器。

你的任务：把用户输入的自然语言流程，转换成 JSON。

只输出 JSON，不要解释，不要输出思考过程。

JSON 格式必须是：
{{
  "steps": [
    {{"text": "步骤名称", "role": "start/process/decision/end"}}
  ]
}}

字段规则：
1. steps 必须按执行顺序排列。
2. text 只保留核心动作或核心步骤名称。
3. text 不要包含“起点是”“然后”“然后到”“接着”“最后”“终点是”“就可以了”等连接词。
4. role 只能是 start、process、decision、end。
5. 用户表达“起点是X”“从X开始”“首先X”时，X 的 role 是 start。
6. 用户表达“终点是X”“最后X”“最终X”“X就可以了”时，X 的 role 是 end。
7. 含有“是否”“判断”“检查”“校验”“验证”“如果”的步骤，role 是 decision。
8. 其他普通动作，role 是 process。

示例1：
用户输入：起点是开始，然后到读取，终点是下载
输出：
{{"steps":[{{"text":"开始","role":"start"}},{{"text":"读取","role":"process"}},{{"text":"下载","role":"end"}}]}}

示例2：
用户输入：首先打开系统，接着上传文件，然后检查格式是否正确，最后生成报告
输出：
{{"steps":[{{"text":"打开系统","role":"start"}},{{"text":"上传文件","role":"process"}},{{"text":"检查格式是否正确","role":"decision"}},{{"text":"生成报告","role":"end"}}]}}

示例3：
用户输入：从找到手机开始，然后联网，打开VPN，注册GitHub账号，最后上传代码就可以了
输出：
{{"steps":[{{"text":"找到手机","role":"start"}},{{"text":"联网","role":"process"}},{{"text":"打开VPN","role":"process"}},{{"text":"注册GitHub账号","role":"process"}},{{"text":"上传代码","role":"end"}}]}}

现在处理这个用户输入：
{user_input}
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

print("\nOllama 原始返回的 JSON（修正前）：")
print(raw_json)

data = json.loads(raw_json)
linear_spec = LinearFlowSpec.model_validate(data)

linear_spec = normalize_roles_by_input(linear_spec, user_input) #The additional PART of 3rd version

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