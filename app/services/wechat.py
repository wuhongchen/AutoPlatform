"""
微信服务
提供公众号发布、素材管理等功能
"""

import json
import time
from typing import Dict, Optional, BinaryIO
import requests
from app.config import get_settings


class WechatService:
    """微信公众号服务"""
    
    API_BASE = "https://api.weixin.qq.com/cgi-bin"
    
    def __init__(self, appid: Optional[str] = None, secret: Optional[str] = None):
        settings = get_settings()
        self.appid = appid or settings.wechat.appid
        self.secret = secret or settings.wechat.secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
    
    def _get_access_token(self) -> str:
        """获取access_token"""
        # 检查缓存
        if self._access_token and time.time() < self._token_expires_at - 300:
            return self._access_token
        
        url = f"{self.API_BASE}/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.secret
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if "access_token" not in data:
            raise Exception(f"获取access_token失败: {data}")
        
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 7200)
        
        return self._access_token
    
    def upload_image(self, image_data: bytes, filename: str = "image.jpg") -> str:
        """上传图片到素材库"""
        token = self._get_access_token()
        url = f"{self.API_BASE}/media/uploadimg?access_token={token}"
        
        files = {"media": (filename, image_data, "image/jpeg")}
        response = requests.post(url, files=files, timeout=60)
        data = response.json()
        
        if "url" not in data:
            raise Exception(f"上传图片失败: {data}")
        
        return data["url"]
    
    def upload_thumb_media(self, image_data: bytes, filename: str = "thumb.jpg") -> str:
        """上传缩略图到永久素材"""
        token = self._get_access_token()
        url = f"{self.API_BASE}/material/add_material?access_token={token}&type=thumb"
        
        files = {"media": (filename, image_data, "image/jpeg")}
        response = requests.post(url, files=files, timeout=60)
        data = response.json()
        
        if "media_id" not in data:
            raise Exception(f"上传缩略图失败: {data}")
        
        return data["media_id"]
    
    def create_draft(self, title: str, content: str, author: str = "",
                    thumb_media_id: str = "", digest: str = "") -> str:
        """创建草稿"""
        token = self._get_access_token()
        url = f"{self.API_BASE}/draft/add?access_token={token}"
        
        articles = [{
            "title": title,
            "content": content,
            "author": author,
            "content_source_url": "",
            "need_open_comment": 0,
            "only_fans_can_comment": 0
        }]
        
        if thumb_media_id:
            articles[0]["thumb_media_id"] = thumb_media_id
        
        if digest:
            articles[0]["digest"] = digest
        
        payload = {"articles": articles}
        
        response = requests.post(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        data = response.json()
        
        if "media_id" not in data:
            raise Exception(f"创建草稿失败: {data}")
        
        return data["media_id"]
    
    def publish_article(self, media_id: str) -> str:
        """发布文章"""
        token = self._get_access_token()
        url = f"{self.API_BASE}/freepublish/submit?access_token={token}"
        
        payload = {"media_id": media_id}
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        data = response.json()
        
        if data.get("errcode") != 0:
            raise Exception(f"发布失败: {data}")
        
        return str(data.get("publish_id", ""))
    
    def get_publish_status(self, publish_id: str) -> Dict:
        """获取发布状态"""
        token = self._get_access_token()
        url = f"{self.API_BASE}/freepublish/get?access_token={token}"
        
        payload = {"publish_id": publish_id}
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        return response.json()
    
    def format_content(self, html_content: str) -> str:
        """格式化内容，适配微信"""
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 移除危险标签
        for tag in soup.find_all(["script", "style", "iframe"]):
            tag.decompose()
        
        # 处理图片
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                img.attrs = {"src": src, "data-src": src}
        
        # 处理标题样式
        for h in soup.find_all(["h1", "h2", "h3"]):
            h["style"] = "font-weight: bold; margin: 20px 0;"
        
        return str(soup)
    
    def render_with_template(self, title: str, content: str, 
                            template_name: str = "default",
                            author: str = "", cover_image: str = "",
                            full_html: bool = False,
                            **kwargs) -> str:
        """
        使用模板渲染文章
        
        Args:
            title: 文章标题
            content: 文章内容
            template_name: 模板名称
            author: 作者
            cover_image: 封面图片
            full_html: 是否输出完整 HTML 文档（默认 False，输出片段适合微信草稿）
            **kwargs: 其他参数
            
        Returns:
            渲染后的HTML
        """
        from app.templates import TemplateRegistry
        
        # 获取模板实例
        template = TemplateRegistry.create_instance(template_name)
        
        if not template:
            # 如果模板不存在，使用默认模板
            template = TemplateRegistry.create_instance("default")
        
        # 渲染内容
        if full_html:
            html = template.render(
                title=title,
                content=content,
                author=author,
                cover_image=cover_image,
                **kwargs
            )
        else:
            html = template.render_fragment(
                title=title,
                content=content,
                author=author,
                cover_image=cover_image,
                **kwargs
            )
        
        # 微信格式化处理
        html = self.format_content(html)
        
        return html
    
    def get_available_templates(self) -> Dict:
        """获取可用模板列表"""
        from app.templates import TemplateRegistry
        return TemplateRegistry.list_templates()
