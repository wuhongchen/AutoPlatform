"""
图片素材模型
"""

from enum import Enum
from typing import Dict, Any
from pydantic import Field

from .base import BaseDBModel


class ImageAssetSource(str, Enum):
    """图片素材来源"""

    UPLOAD = "upload"
    AI = "ai"


class ImageAsset(BaseDBModel):
    """图片素材"""

    title: str = Field(default="", description="素材标题")
    prompt: str = Field(default="", description="AI 生成提示词")
    source_type: ImageAssetSource = Field(default=ImageAssetSource.UPLOAD, description="来源类型")
    image_url: str = Field(description="可访问的图片地址")
    file_path: str = Field(default="", description="图片相对存储路径")
    mime_type: str = Field(default="", description="图片 MIME 类型")
    account_id: str = Field(description="所属账户")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展信息")
