import os
from dotenv import load_dotenv

# 确保加载环境变量
load_dotenv()

# 模型池配置
MODEL_POOL = {
    "kimi": {
        "name": "Moonshot KIMI",
        "api_key": (os.getenv("KIMI_API_KEY") or "").strip(),
        "endpoint": "https://api.moonshot.cn/v1/chat/completions",
        "model": (os.getenv("KIMI_MODEL_ID") or "moonshot-v1-8k").strip()
    },
    "volcengine": {
        "name": "火山方舟",
        "api_key": (os.getenv("VOLC_ARK_API_KEY") or "").strip(),
        "endpoint": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model": (os.getenv("VOLC_ARK_MODEL_ID") or "ep-20250101-xxxx").strip()
    },
    "bailian": {
        "name": "阿里云百炼 (Qwen)",
        "api_key": (os.getenv("BAILIAN_API_KEY") or "").strip(),
        "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": (os.getenv("BAILIAN_MODEL_ID") or "qwen-plus").strip()
    },
    "openai": {
        "name": "OpenAI / Generic",
        "api_key": (os.getenv("LLM_API_KEY") or "").strip(),
        "endpoint": (os.getenv("LLM_ENDPOINT") or "https://api.openai.com/v1/chat/completions").strip(),
        "model": (os.getenv("LLM_MODEL") or "gpt-3.5-turbo").strip()
    }
}

DEFAULT_MODEL = "volcengine"
