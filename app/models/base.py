"""
基础模型定义
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BaseDBModel(BaseModel):
    """数据库基础模型"""
    id: Optional[str] = Field(default=None, description="记录ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        from_attributes = True
