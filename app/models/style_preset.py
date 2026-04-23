"""
风格预设模型
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class WritingTone(str, Enum):
    """写作语气"""
    PROFESSIONAL = "professional"      # 专业严谨
    CASUAL = "casual"                  # 轻松随意
    HUMOROUS = "humorous"              # 幽默风趣
    SERIOUS = "serious"                # 严肃正式
    FRIENDLY = "friendly"              # 亲切友好
    AUTHORITATIVE = "authoritative"    # 权威可信


class WritingStyle(str, Enum):
    """写作风格"""
    NARRATIVE = "narrative"            # 叙事型
    ANALYTICAL = "analytical"          # 分析型
    PERSUASIVE = "persuasive"          # 说服型
    DESCRIPTIVE = "descriptive"        # 描述型
    TECHNICAL = "technical"            # 技术型
    STORYTELLING = "storytelling"      # 讲故事型


class StylePreset(BaseModel):
    """风格预设模型"""
    id: str = Field(..., description="唯一标识")
    name: str = Field(..., description="显示名称")
    description: str = Field(default="", description="描述")
    system_prompt: str = Field(..., description="系统提示词")
    tone: WritingTone = Field(default=WritingTone.PROFESSIONAL, description="语气")
    style: WritingStyle = Field(default=WritingStyle.ANALYTICAL, description="风格")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=4000, ge=100, le=8000, description="最大token数")
    is_builtin: bool = Field(default=False, description="是否内置")
    is_active: bool = Field(default=True, description="是否启用")
    params: Dict[str, Any] = Field(default_factory=dict, description="额外参数")
    usage_count: int = Field(default=0, description="使用次数")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "tech_expert",
                "name": "科技专家",
                "description": "深入浅出解读技术，专业但不晦涩",
                "system_prompt": "你是一位资深科技媒体主编...",
                "tone": "professional",
                "style": "analytical",
                "temperature": 0.7,
                "is_builtin": True,
                "is_active": True
            }
        }
    }
