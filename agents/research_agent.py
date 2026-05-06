import json
import urllib.request
import urllib.error

from models.concept_spec import ConceptListSpec
from utils.prompt_loader import load_prompt


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:8b"

RESEARCH_PROMPT_PATH = "prompts/research/extract_concepts.md"


def build_research_prompt(user_input: str) -> str:
    """
    构建 Research Agent Prompt。
    从 prompts/research/extract_concepts.md 读取模板，
    并把 __USER_INPUT__ 替换为真实输入。
    """

    template = load_prompt(RESEARCH_PROMPT_PATH)

    if "__USER_INPUT__" not in template:
        raise ValueError(
            "Research prompt missing required placeholder: __USER_INPUT__"
        )

    return template.replace("__USER_INPUT__", user_input)


def extract_concepts(user_input: str) -> ConceptListSpec:
    """
    调用 Ollama，从用户输入或文档内容中抽取关键概念。
    """

    prompt = build_research_prompt(user_input)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": ConceptListSpec.model_json_schema(),
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

    print("\nResearch Agent 返回的 concepts JSON：")
    print(raw_json)

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Research Agent 返回内容不是合法 JSON：{e}\n原始输出：\n{raw_json}")

    return ConceptListSpec.model_validate(data)