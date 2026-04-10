"""
账户模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import Field
from .base import BaseDBModel


class AccountStatus(str, Enum):
    """账户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"


class Account(BaseDBModel):
    """账户模型"""
    
    # 基础信息
    name: str = Field(description="账户名称")
    account_id: str = Field(description="账户唯一标识")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="账户状态")
    
    # 微信配置
    wechat_appid: str = Field(default="", description="微信AppID")
    wechat_secret: str = Field(default="", description="微信AppSecret")
    wechat_author: str = Field(default="W 小龙虾", description="默认作者")
    
    # 流水线配置
    pipeline_role: str = Field(default="tech_expert", description="默认改写角色")
    pipeline_model: str = Field(default="auto", description="默认改写模型")
    pipeline_batch_size: int = Field(default=3, description="批处理大小")
    
    # 内容方向
    content_direction: str = Field(default="", description="内容方向")
    prompt_direction: str = Field(default="", description="提示词方向")
    wechat_prompt_direction: str = Field(default="", description="公众号方向")
    
    # 统计信息
    last_run_at: Optional[datetime] = Field(default=None, description="最后运行时间")
    run_count: int = Field(default=0, description="运行次数")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "主账号",
                "account_id": "main",
                "wechat_appid": "wx...",
                "wechat_author": "作者名",
            }
        }
