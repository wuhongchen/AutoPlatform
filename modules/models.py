import os
from dotenv import load_dotenv

# 确保加载环境变量
load_dotenv()

def _first_non_empty(*keys):
    """从多个环境变量中取第一个非空值。"""
    for key in keys:
        val = (os.getenv(key) or "").strip()
        if val:
            return val
    return ""

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
    _first_non_empty("LLM_ENDPOINT", "OPENAI_BASE_URL", "OPENAI_API_BASE"),
    "https://api.openai.com/v1"
)
OPENCLAW_PROXY_ENDPOINT = _normalize_chat_endpoint(
    _first_non_empty(
        "OPENCLAW_PROXY_ENDPOINT",
        "OPENCLAW_LLM_ENDPOINT",
        "OPENCLAW_CHAT_ENDPOINT",
        "OPENCLAW_ENDPOINT",
        "OPENCLAW_BASE_URL",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
    ),
    ""
)

# 统一 key
KIMI_API_KEY = (os.getenv("KIMI_API_KEY") or "").strip()
VOLC_API_KEY = (os.getenv("VOLC_ARK_API_KEY") or os.getenv("LLM_API_KEY") or "").strip()
BAILIAN_API_KEY = (os.getenv("BAILIAN_API_KEY") or "").strip()
ZHIPU_API_KEY = (os.getenv("ZHIPU_API_KEY") or "").strip()
MINIMAX_API_KEY = (os.getenv("MINIMAX_API_KEY") or "").strip()
OPENAI_API_KEY = _first_non_empty("LLM_API_KEY", "OPENAI_API_KEY")
OPENCLAW_PROXY_API_KEY = _first_non_empty(
    "OPENCLAW_PROXY_API_KEY",
    "OPENCLAW_LLM_API_KEY",
    "OPENCLAW_API_KEY",
    "OPENAI_API_KEY",
)
OPENCLAW_PROXY_MODEL = _first_non_empty(
    "OPENCLAW_PROXY_MODEL",
    "OPENCLAW_LLM_MODEL",
    "OPENCLAW_MODEL",
    "OPENAI_MODEL",
    "LLM_MODEL",
    "OPENCLAW_MODEL_NAME",
) or "gpt-4o-mini"

def has_openclaw_proxy_config():
    return bool(OPENCLAW_PROXY_ENDPOINT and OPENCLAW_PROXY_API_KEY)

def get_runtime_default_model_key():
    """
    运行时默认模型选择：
    1) OPENCLAW_DEFAULT_MODEL（显式指定，且在模型池中）
    2) OPENCLAW_MODEL_PROVIDER=openclaw|independent|auto（默认 auto）
    3) auto 模式：若检测到 OpenClaw 代理配置则用 openclaw，否则回退独立模型
    """
    provider_mode = (_first_non_empty("OPENCLAW_MODEL_PROVIDER", "OPENCLAW_MODEL_SOURCE") or "auto").lower()
    explicit_default = _first_non_empty("OPENCLAW_DEFAULT_MODEL")
    independent_default = _first_non_empty("OPENCLAW_INDEPENDENT_MODEL") or "kimi-k2.5"
    if independent_default not in MODEL_POOL:
        independent_default = "volcengine"

    if explicit_default and explicit_default in MODEL_POOL:
        return explicit_default

    if provider_mode == "openclaw":
        return "openclaw" if has_openclaw_proxy_config() else independent_default
    if provider_mode == "independent":
        return independent_default

    # auto
    if has_openclaw_proxy_config():
        return "openclaw"
    return independent_default

# 模型池配置
MODEL_POOL = {
    "openclaw": {
        "name": "OpenClaw Proxy",
        "api_key": OPENCLAW_PROXY_API_KEY,
        "endpoint": OPENCLAW_PROXY_ENDPOINT,
        "model": OPENCLAW_PROXY_MODEL
    },
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

DEFAULT_MODEL = get_runtime_default_model_key()
