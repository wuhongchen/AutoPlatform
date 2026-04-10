"""
服务层
提供各类业务服务
"""

from .storage import StorageService
from .ai import AIService
from .wechat import WechatService
from .collector import CollectorService

__all__ = [
    "StorageService",
    "AIService",
    "WechatService",
    "CollectorService",
]
