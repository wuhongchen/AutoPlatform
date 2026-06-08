"""
文章模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field, HttpUrl
from .base import BaseDBModel


class ArticleStatus(str, Enum):
    """文章状态"""
    PENDING = "pending"           # 待处理
    COLLECTING = "collecting"     # 采集中
    COLLECTED = "collected"       # 采集完成
    REWRITING = "rewriting"       # 改写中
    REWRITTEN = "rewritten"       # 改写完成
    REVIEWING = "reviewing"       # 审核中
    APPROVED = "approved"         # 已审核
    PUBLISHING = "publishing"     # 发布中
    PUBLISHED = "published"       # 已发布
    FAILED = "failed"             # 失败
    SKIPPED = "skipped"           # 已跳过


class Article(BaseDBModel):
    """文章模型"""
    
    # 来源信息
    source_url: str = Field(description="原文URL")
    source_title: str = Field(default="", description="原文标题")
    source_author: str = Field(default="", description="原文作者")
    
    # 内容
    original_content: str = Field(default="", description="原文内容")
    original_html: str = Field(default="", description="原文HTML")
    rewritten_content: str = Field(default="", description="改写后内容")
    rewritten_html: str = Field(default="", description="改写后HTML")
    
    # 媒体
    images: List[str] = Field(default_factory=list, description="图片列表")
    cover_image: str = Field(default="", description="封面图片")
    
    # 状态
    status: ArticleStatus = Field(default=ArticleStatus.PENDING, description="文章状态")
    
    # AI评分
    ai_score: Optional[float] = Field(default=None, description="AI评分")
    ai_reason: str = Field(default="", description="AI推荐理由")
    ai_direction: str = Field(default="", description="AI建议方向")
    
    # 改写风格
    rewrite_style: str = Field(default="tech_expert", description="改写风格预设")
    rewrite_references: List[str] = Field(default_factory=list, description="引用的参考文章ID")
    custom_instructions: str = Field(default="", description="自定义改写指令")
    
    # 发布信息
    wechat_draft_id: str = Field(default="", description="微信草稿ID")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")
    published_url: str = Field(default="", description="发布链接")
    
    # 关联
    account_id: str = Field(description="所属账户ID")
    pipeline_id: Optional[str] = Field(default=None, description="流水线记录ID")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    # 错误信息
    error_message: str = Field(default="", description="错误信息")
