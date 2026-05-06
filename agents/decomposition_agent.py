import json
import urllib.request
import urllib.error

from models.concept_spec import ConceptListSpec
from models.decomposition_spec import DecompositionSpec
from utils.prompt_loader import load_prompt


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"

DECOMPOSITION_PROMPT_PATH = "prompts/decomposition/decompose.md"


def build_decomposition_prompt(
    user_input: str,
    concept_spec: ConceptListSpec,
) -> str:
    """
    构建 Decomposition Agent Prompt。

    输入：
    1. user_input：用户原始输入或文档内容
    2. concept_spec：Research Agent 抽取出的概念列表

    输出：
    填充后的 Prompt 字符串
    """

    template = load_prompt(DECOMPOSITION_PROMPT_PATH)  #Read Prompts

#ckeckout the placeholder (占位符)
    required_placeholders = [
        "__USER_INPUT__",
        "__CONCEPTS_JSON__",
    ]
    for placeholder in required_placeholders:
        if placeholder not in template:
            raise ValueError(
                f"Decomposition prompt missing required placeholder: {placeholder}"
            )
#convert the concepts into JSON string
    concepts_json = json.dumps(
        concept_spec.model_dump(),
        ensure_ascii=False,
        indent=2,
    )
#Convert the Prompt to a more complete Prompt then senting to Ollama
    prompt = template.replace("__USER_INPUT__", user_input)
    prompt = prompt.replace("__CONCEPTS_JSON__", concepts_json)

    return prompt

#Function used to call Ollama
def extract_decomposition(
    user_input: str,
    concept_spec: ConceptListSpec,
) -> DecompositionSpec:
    """
    调用 Ollama，根据用户输入和 concepts 生成系统拆解结果。
    """

    prompt = build_decomposition_prompt(user_input, concept_spec)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": DecompositionSpec.model_json_schema(),
        "options": {
            "temperature": 0 #to be stable instead of random
        }
    }
#create a request for HTTP and sent to local Ollama interface
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

    print("\nDecomposition Agent 返回的 decomposition JSON：")
    print(raw_json)

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Decomposition Agent 返回内容不是合法 JSON：{e}\n原始输出：\n{raw_json}"
        )

    decomposition_spec = DecompositionSpec.model_validate(data)

    if (
        not decomposition_spec.modules
        and not decomposition_spec.decisions
        and not decomposition_spec.flows
        and not decomposition_spec.dependencies
    ):
        print("[warning] Decomposition Agent 返回了空拆解结果。")

    return decomposition_spec