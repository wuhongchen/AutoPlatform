"""
灵感库模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field
from .base import BaseDBModel


class InspirationStatus(str, Enum):
    """灵感状态"""
    PENDING_ANALYSIS = "待分析"
    ANALYZING = "分析中"
    PENDING_DECISION = "待决策"
    APPROVED = "已采纳"
    REJECTED = "已跳过"
    IN_PIPELINE = "已进入流水线"


class InspirationRecord(BaseDBModel):
    """灵感记录"""
    
    # 来源
    source_url: str = Field(description="来源URL")
    source_type: str = Field(default="wechat", description="来源类型")
    source_account: str = Field(default="", description="来源账号")
    
    # 基本信息
    title: str = Field(default="", description="标题")
    author: str = Field(default="", description="作者")
    summary: str = Field(default="", description="摘要")
    
    # 内容
    content: str = Field(default="", description="内容")
    content_html: str = Field(default="", description="HTML内容")
    images: List[str] = Field(default_factory=list, description="图片列表")
    
    # 互动数据
    read_count: Optional[int] = Field(default=None, description="阅读量")
    like_count: Optional[int] = Field(default=None, description="点赞数")
    
    # AI分析
    ai_score: Optional[float] = Field(default=None, description="AI评分 0-100")
    ai_reason: str = Field(default="", description="推荐理由")
    ai_direction: str = Field(default="", description="建议方向")
    ai_insight: str = Field(default="", description="核心洞察")
    
    # 状态
    status: InspirationStatus = Field(default=InspirationStatus.PENDING_ANALYSIS, description="状态")
    
    # 关联
    account_id: str = Field(description="所属账户ID")
    article_id: Optional[str] = Field(default=None, description="关联文章ID")
    
    # 采集时间
    collected_at: datetime = Field(default_factory=datetime.now, description="采集时间")
    analyzed_at: Optional[datetime] = Field(default=None, description="分析时间")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    # 错误信息
    error_message: str = Field(default="", description="错误信息")
