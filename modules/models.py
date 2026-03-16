import os
from dotenv import load_dotenv

# 确保加载环境变量
load_dotenv()

def _normalize_chat_endpoint(endpoint, default_base):
    """将 base URL 或 completions URL 统一为 chat/completions endpoint。"""
    raw = (endpoint or default_base or "").strip()
    if not raw:
        return ""
    if raw.endswith("/chat/completions"):
        return raw
    return raw.rstrip("/") + "/chat/completions"

# 统一 endpoint
KIMI_ENDPOINT = _normalize_chat_endpoint(
    os.getenv("KIMI_ENDPOINT"),
    "https://api.moonshot.cn/v1"
)
VOLC_ENDPOINT = _normalize_chat_endpoint(
    os.getenv("VOLC_ARK_ENDPOINT"),
    "https://ark.cn-beijing.volces.com/api/v3"
)
BAILIAN_ENDPOINT = _normalize_chat_endpoint(
    os.getenv("BAILIAN_ENDPOINT"),
    "https://coding.dashscope.aliyuncs.com/v1"
)
ZHIPU_ENDPOINT = _normalize_chat_endpoint(
    os.getenv("ZHIPU_ENDPOINT"),
    "https://open.bigmodel.cn/api/paas/v4"
)
MINIMAX_ENDPOINT = _normalize_chat_endpoint(
    os.getenv("MINIMAX_ENDPOINT"),
    "https://api.minimax.chat/v1"
)
OPENAI_ENDPOINT = _normalize_chat_endpoint(
    os.getenv("LLM_ENDPOINT"),
    "https://api.openai.com/v1"
)

# 统一 key
KIMI_API_KEY = (os.getenv("KIMI_API_KEY") or "").strip()
VOLC_API_KEY = (os.getenv("VOLC_ARK_API_KEY") or os.getenv("LLM_API_KEY") or "").strip()
BAILIAN_API_KEY = (os.getenv("BAILIAN_API_KEY") or "").strip()
ZHIPU_API_KEY = (os.getenv("ZHIPU_API_KEY") or "").strip()
MINIMAX_API_KEY = (os.getenv("MINIMAX_API_KEY") or "").strip()
OPENAI_API_KEY = (os.getenv("LLM_API_KEY") or "").strip()

# 模型池配置
MODEL_POOL = {
    "kimi": {
        "name": "Moonshot KIMI",
        "api_key": KIMI_API_KEY,
        "endpoint": KIMI_ENDPOINT,
        "model": (os.getenv("KIMI_MODEL_ID") or "moonshot-v1-8k").strip()
    },
    "kimi-k2.5": {
        "name": "Moonshot Kimi K2.5",
        "api_key": KIMI_API_KEY,
        "endpoint": KIMI_ENDPOINT,
        "model": "kimi-k2.5",
        "capabilities": ["text_generation", "reasoning", "vision"]
    },
    "volcengine": {
        "name": "火山方舟",
        "api_key": VOLC_API_KEY,
        "endpoint": VOLC_ENDPOINT,
        "model": (os.getenv("VOLC_ARK_MODEL_ID") or "ep-20250101-xxxx").strip()
    },
    "bailian": {
        "name": "阿里云百炼 (Qwen)",
        "api_key": BAILIAN_API_KEY,
        "endpoint": BAILIAN_ENDPOINT,
        "model": (os.getenv("BAILIAN_MODEL_ID") or "qwen-plus").strip()
    },
    "qwen3.5-plus": {
        "name": "阿里百炼 Qwen3.5 Plus",
        "api_key": BAILIAN_API_KEY,
        "endpoint": BAILIAN_ENDPOINT,
        "model": "qwen3.5-plus",
        "capabilities": ["text_generation", "reasoning", "vision"]
    },
    "qwen3-max-2026-01-23": {
        "name": "阿里百炼 Qwen3 Max 2026-01-23",
        "api_key": BAILIAN_API_KEY,
        "endpoint": BAILIAN_ENDPOINT,
        "model": "qwen3-max-2026-01-23",
        "capabilities": ["text_generation", "reasoning"]
    },
    "qwen3-coder-next": {
        "name": "阿里百炼 Qwen3 Coder Next",
        "api_key": BAILIAN_API_KEY,
        "endpoint": BAILIAN_ENDPOINT,
        "model": "qwen3-coder-next",
        "capabilities": ["text_generation"]
    },
    "qwen3-coder-plus": {
        "name": "阿里百炼 Qwen3 Coder Plus",
        "api_key": BAILIAN_API_KEY,
        "endpoint": BAILIAN_ENDPOINT,
        "model": "qwen3-coder-plus",
        "capabilities": ["text_generation"]
    },
    "zhipu": {
        "name": "智谱 GLM",
        "api_key": ZHIPU_API_KEY,
        "endpoint": ZHIPU_ENDPOINT,
        "model": (os.getenv("ZHIPU_MODEL_ID") or "glm-5").strip()
    },
    "glm-5": {
        "name": "智谱 GLM-5",
        "api_key": ZHIPU_API_KEY,
        "endpoint": ZHIPU_ENDPOINT,
        "model": "glm-5",
        "capabilities": ["text_generation", "reasoning"]
    },
    "glm-4.7": {
        "name": "智谱 GLM-4.7",
        "api_key": ZHIPU_API_KEY,
        "endpoint": ZHIPU_ENDPOINT,
        "model": "glm-4.7",
        "capabilities": ["text_generation", "reasoning"]
    },
    "minimax": {
        "name": "MiniMax",
        "api_key": MINIMAX_API_KEY,
        "endpoint": MINIMAX_ENDPOINT,
        "model": (os.getenv("MINIMAX_MODEL_ID") or "MiniMax-M2.5").strip()
    },
    "MiniMax-M2.5": {
        "name": "MiniMax M2.5",
        "api_key": MINIMAX_API_KEY,
        "endpoint": MINIMAX_ENDPOINT,
        "model": "MiniMax-M2.5",
        "capabilities": ["text_generation", "reasoning"]
    },
    "openai": {
        "name": "OpenAI / Generic",
        "api_key": OPENAI_API_KEY,
        "endpoint": OPENAI_ENDPOINT,
        "model": (os.getenv("LLM_MODEL") or "gpt-3.5-turbo").strip()
    }
}

DEFAULT_MODEL = "volcengine"
