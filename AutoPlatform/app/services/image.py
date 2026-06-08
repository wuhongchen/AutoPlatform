"""
图片服务
"""

import base64
from typing import Dict, Any

import openai
import requests

from app.config import get_settings


class ImageService:
    """图片生成服务"""

    def __init__(self):
        settings = get_settings()
        self.config = settings.image
        api_key = self.config.api_key or settings.ai.api_key
        endpoint = self.config.endpoint or settings.ai.endpoint
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=endpoint,
            timeout=120,
        )

    def generate(self, prompt: str, size: str = "") -> Dict[str, Any]:
        """生成图片并返回字节内容"""
        if not prompt.strip():
            raise ValueError("图片提示词不能为空")
        if not self.client.api_key:
            raise ValueError("图片生成 API Key 未配置")

        response = self.client.images.generate(
            model=self.config.model,
            prompt=prompt,
            size=size or self.config.size,
            response_format="b64_json",
        )
        data = response.data[0]

        if getattr(data, "b64_json", None):
            return {
                "bytes": base64.b64decode(data.b64_json),
                "mime_type": "image/png",
                "revised_prompt": getattr(data, "revised_prompt", ""),
            }

        image_url = getattr(data, "url", "")
        if image_url:
            image_resp = requests.get(image_url, timeout=120)
            image_resp.raise_for_status()
            return {
                "bytes": image_resp.content,
                "mime_type": image_resp.headers.get("Content-Type", "image/png"),
                "revised_prompt": getattr(data, "revised_prompt", ""),
            }

        raise ValueError("图片生成结果为空")
