"""
AI 模型配置
支持在线管理多个 AI 模型配置，无需重启服务即可切换
"""

from datetime import datetime
from typing import Optional
from pydantic import Field
from .base import BaseDBModel


class AIProvider(str):
    """预定义的 AI 提供商"""


class AIModelConfig(BaseDBModel):
    """AI 模型配置"""

    name: str = Field(default="", description="显示名称，如 DeepSeek V3")
    provider: str = Field(default="custom", description="提供商: deepseek / volcengine / openai / custom")
    api_key: str = Field(default="", description="API Key")
    endpoint: str = Field(default="https://api.deepseek.com/v1", description="API 端点")
    model: str = Field(default="deepseek-chat", description="模型 ID")
    is_active: bool = Field(default=True, description="是否启用")
    is_default: bool = Field(default=False, description="是否默认使用")
    timeout: int = Field(default=240, description="请求超时（秒）")
    metadata: dict = Field(default_factory=dict, description="额外元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "deepseek-chat",
                "name": "DeepSeek V3",
                "provider": "deepseek",
                "api_key": "sk-xxx",
                "endpoint": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "is_active": True,
                "is_default": True,
                "timeout": 240,
            }
        }
    }

    def to_dict(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_row(cls, row: dict) -> "AIModelConfig":
        """从数据库行创建实例"""
        return cls(
            id=row.get("id"),
            name=row.get("name", ""),
            provider=row.get("provider", "custom"),
            api_key=row.get("api_key", ""),
            endpoint=row.get("endpoint", ""),
            model=row.get("model", ""),
            is_active=bool(row.get("is_active", True)),
            is_default=bool(row.get("is_default", False)),
            timeout=int(row.get("timeout", 240)),
            metadata=row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {},
            created_at=row.get("created_at", datetime.now()),
            updated_at=row.get("updated_at", datetime.now()),
        )


# 系统内置预设
BUILTIN_AI_CONFIGS = [
    {
        "id": "doubao-seed-pro",
        "name": "火山引擎 Doubao Pro",
        "provider": "volcengine",
        "endpoint": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-seed-2-0-pro-260215",
        "is_active": True,
        "is_default": True,
        "timeout": 240,
    },
    {
        "id": "deepseek-chat",
        "name": "DeepSeek V3",
        "provider": "deepseek",
        "endpoint": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "is_active": True,
        "is_default": False,
        "timeout": 240,
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek R1",
        "provider": "deepseek",
        "endpoint": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner",
        "is_active": True,
        "is_default": False,
        "timeout": 300,
    },
]
