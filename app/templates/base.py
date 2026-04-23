"""
模板基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class TemplateConfig:
    """模板配置"""
    name: str
    description: str
    author: str = ""
    version: str = "1.0.0"
    preview_image: str = ""
    supports_custom_css: bool = False


class BaseTemplate(ABC):
    """模板基类"""
    
    # 模板配置
    config = TemplateConfig(
        name="基础模板",
        description="基础排版模板"
    )
    
    def __init__(self, custom_css: Optional[str] = None, 
                 custom_config: Optional[Dict[str, Any]] = None):
        self.custom_css = custom_css or ""
        self.custom_config = custom_config or {}
    
    @abstractmethod
    def render(self, title: str, content: str, author: str = "",
               cover_image: str = "", **kwargs) -> str:
        """
        渲染文章
        
        Args:
            title: 文章标题
            content: 文章内容（HTML）
            author: 作者
            cover_image: 封面图片URL
            **kwargs: 其他参数
            
        Returns:
            完整的HTML字符串
        """
        pass
    
    def process_content(self, content: str) -> str:
        """
        处理内容
        子类可以重写此方法来自定义内容处理
        """
        return content
    
    def get_styles(self) -> str:
        """
        获取样式
        子类应该重写此方法提供模板样式
        """
        return """
        <style>
        .article-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.8;
            color: #333;
        }
        .article-title {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #222;
        }
        .article-meta {
            color: #999;
            font-size: 14px;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .article-content {
            font-size: 16px;
        }
        .article-content img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }
        .article-content h2 {
            font-size: 22px;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #222;
        }
        .article-content p {
            margin-bottom: 16px;
        }
        </style>
        """
    
    def render_fragment(self, title: str, content: str, author: str = "",
                        cover_image: str = "", **kwargs) -> str:
        """
        渲染文章片段（不含完整 HTML 文档结构，适合微信草稿等场景）
        子类应重写此方法返回 style + body 的内容片段
        """
        full_html = self.render(title, content, author, cover_image, **kwargs)
        # 从完整 HTML 中提取 body 内容
        import re
        match = re.search(r'<body>(.*?)</body>', full_html, re.DOTALL)
        if match:
            body = match.group(1).strip()
            # 同时保留 head 中的 style
            style_match = re.search(r'<style>.*?</style>', full_html, re.DOTALL)
            styles = style_match.group(0) if style_match else ""
            return f"{styles}\n{body}"
        return full_html

    def _wrap_html(self, body_content: str) -> str:
        """包装HTML"""
        styles = self.get_styles()
        custom_style = f"<style>{self.custom_css}</style>" if self.custom_css else ""
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {styles}
    {custom_style}
</head>
<body>
    {body_content}
</body>
</html>"""


class TemplateRegistry:
    """模板注册中心"""
    
    _templates: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, template_class: type):
        """注册模板"""
        if not issubclass(template_class, BaseTemplate):
            raise ValueError(f"模板类必须继承 BaseTemplate")
        cls._templates[name] = template_class
    
    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """获取模板类"""
        return cls._templates.get(name)
    
    @classmethod
    def list_templates(cls) -> Dict[str, TemplateConfig]:
        """列出所有模板"""
        return {
            name: template_class.config 
            for name, template_class in cls._templates.items()
        }
    
    @classmethod
    def create_instance(cls, name: str, **kwargs) -> Optional[BaseTemplate]:
        """创建模板实例"""
        template_class = cls.get(name)
        if template_class:
            return template_class(**kwargs)
        return None
