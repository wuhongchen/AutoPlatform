"""
信息源模型
支持 RSS / Discourse / HackerNews / Reddit / Dev.to / GitHub 等多平台信息源管理
"""

from datetime import datetime
from typing import Optional
from pydantic import Field
from .base import BaseDBModel


class FeedSource(BaseDBModel):
    """信息源（RSS + 三方平台）"""

    name: str = Field(default="", description="订阅名称")
    url: str = Field(default="", description="RSS/API 地址")
    account_id: str = Field(default="", description="所属账户")
    category: str = Field(default="未分类", description="分类标签")

    # 新增：信息源类型
    source_type: str = Field(default="rss", description="信息源类型: rss/discourse/hackernews/reddit/devto/github")
    source_config: dict = Field(default_factory=dict, description="信息源配置（forum_url/subreddit/tag/language等）")

    fetch_interval: int = Field(default=60, description="抓取间隔（分钟）")
    last_fetched_at: Optional[datetime] = Field(default=None, description="上次抓取时间")
    item_count: int = Field(default=0, description="累计抓取条数")
    is_active: bool = Field(default=True, description="是否启用")
    metadata: dict = Field(default_factory=dict, description="额外信息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "feed_linuxdo",
                "name": "linux.do 最新",
                "url": "https://linux.do",
                "account_id": "default",
                "category": "技术社区",
                "source_type": "discourse",
                "source_config": {"forum_url": "https://linux.do", "sort": "latest"},
                "is_active": True,
            }
        }
    }
