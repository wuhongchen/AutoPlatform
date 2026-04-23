"""
任务模型
所有功能操作都以任务形式异步执行
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import Field
from .base import BaseDBModel


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"       # ⏳ 待执行
    RUNNING = "running"       # 🔄 执行中
    COMPLETED = "completed"   # ✅ 已完成
    FAILED = "failed"         # ❌ 失败
    CANCELLED = "cancelled"   # 🚫 已取消


class TaskName(str, Enum):
    """任务类型"""
    COLLECT = "collect"       # 采集灵感
    REWRITE = "rewrite"       # 改写文章
    PUBLISH = "publish"       # 发布文章
    BATCH = "batch"           # 批量处理


class Task(BaseDBModel):
    """任务记录"""
    
    # 任务类型与参数
    name: TaskName = Field(description="任务类型")
    payload: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    
    # 状态
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="状态")
    
    # 执行结果
    result: Dict[str, Any] = Field(default_factory=dict, description="执行结果")
    error_message: str = Field(default="", description="错误信息")
    
    # 关联
    account_id: str = Field(default="", description="所属账户ID")
    target_id: str = Field(default="", description="目标对象ID（如文章ID）")
    
    # 时间追踪
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    
    # 重试
    retry_count: int = Field(default=0, description="已重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "rewrite",
                "payload": {"article_id": "article_123", "style": "tech_expert"},
                "status": "pending",
                "account_id": "default"
            }
        }
    }
