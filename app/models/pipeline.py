"""
流水线模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field
from .base import BaseDBModel


class PipelineStatus(str, Enum):
    """流水线状态"""
    PENDING_REWRITE = "🧲 待改写"
    REWRITING = "✍️ 改写中"
    PENDING_REVIEW = "🧾 待审核"
    PENDING_PUBLISH = "🚀 待发布"
    PUBLISHING = "📤 发布中"
    PUBLISHED = "✅ 已发布"
    REWRITE_FAILED = "❌ 改写失败"
    PUBLISH_FAILED = "❌ 发布失败"


class PipelineRecord(BaseDBModel):
    """流水线记录"""
    
    # 关联
    article_id: str = Field(description="文章ID")
    account_id: str = Field(description="账户ID")
    
    # 状态
    status: PipelineStatus = Field(default=PipelineStatus.PENDING_REWRITE, description="状态")
    
    # 改写配置
    role: str = Field(default="tech_expert", description="改写角色")
    model: str = Field(default="auto", description="改写模型")
    
    # 时间追踪
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    
    # 执行结果
    result: Dict[str, Any] = Field(default_factory=dict, description="执行结果")
    error_message: str = Field(default="", description="错误信息")
    
    # 重试次数
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    
    # 审核信息
    reviewer: str = Field(default="", description="审核人")
    review_note: str = Field(default="", description="审核备注")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "article_id": "article_123",
                "account_id": "main",
                "status": "🧲 待改写",
                "role": "tech_expert",
            }
        }
    }
