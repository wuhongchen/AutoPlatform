"""
基础模型定义
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class BaseDBModel(BaseModel):
    """数据库基础模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[str] = Field(default=None, description="记录ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
