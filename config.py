import os
from dotenv import load_dotenv

# 加载 .env 文件 (优先加载当前目录，其次加载 mp-draft-push 目录)
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "../mp-draft-push/.env"))

class Config:
    # 微信配置
    WECHAT_APPID = os.getenv("WECHAT_APPID", "wx0d47adc0348efc8e")
    WECHAT_SECRET = os.getenv("WECHAT_SECRET", "e8514c78ee7334fdc3ed9db3f98d7d8a")
    WECHAT_AUTHOR = os.getenv("WECHAT_AUTHOR", "W 小龙虾")
    
    # 火山引擎配置 (即梦 AI)
    VOLCENGINE_AK = os.getenv("VOLCENGINE_AK")
    VOLCENGINE_SK = os.getenv("VOLCENGINE_SK")
    
    # LLM 配置
    LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("VOLC_ARK_API_KEY")
    LLM_ENDPOINT = os.getenv("LLM_ENDPOINT") or os.getenv("VOLC_ARK_ENDPOINT") or "https://ark.cn-beijing.volces.com/api/v3"
    VOLC_ARK_MODEL_ID = os.getenv("VOLC_ARK_MODEL_ID") or "doubao-seed-2-0-pro-260215"
    
    # 飞书多维表格配置
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
    FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN")
    
    # 其他配置
    DEFAULT_COVER_URL = os.getenv("DEFAULT_COVER_URL")
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
    
    @classmethod
    def check_keys(cls):
        """检查必要密钥是否完整"""
        missing = []
        if not cls.WECHAT_APPID or not cls.WECHAT_SECRET:
            missing.append("WECHAT_APPID/SECRET")
        if not cls.LLM_API_KEY:
            missing.append("LLM_API_KEY (用于 AI 改写)")
        if not cls.VOLCENGINE_AK or not cls.VOLCENGINE_SK:
            missing.append("VOLCENGINE AK/SK (用于封面生成)")
        return missing
