"""
RSS 信息源模型
支持 RSS 2.0 和 Atom 格式的订阅源管理
"""

from datetime import datetime
from typing import Optional
from pydantic import Field
from .base import BaseDBModel


class FeedSource(BaseDBModel):
    """RSS 信息源"""

    name: str = Field(default="", description="订阅名称")
    url: str = Field(default="", description="RSS 订阅地址")
    account_id: str = Field(default="", description="所属账户")
    category: str = Field(default="未分类", description="分类标签")
    fetch_interval: int = Field(default=60, description="抓取间隔（分钟）")
    last_fetched_at: Optional[datetime] = Field(default=None, description="上次抓取时间")
    item_count: int = Field(default=0, description="累计抓取条数")
    is_active: bool = Field(default=True, description="是否启用")
    metadata: dict = Field(default_factory=dict, description="额外信息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "feed_36kr",
                "name": "36氪",
                "url": "https://36kr.com/feed",
                "account_id": "default",
                "category": "科技",
                "fetch_interval": 60,
                "is_active": True,
            }
        }
    }
