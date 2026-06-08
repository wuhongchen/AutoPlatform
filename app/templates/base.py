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
        return self.build_style_block("")

    def get_shared_css(self) -> str:
        """所有模板共享的阅读与广告位样式"""
        return """
        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            padding: 0;
            background: #ffffff;
        }
        .article-wrapper,
        .article-header,
        .article-body,
        .article-footer,
        .article-meta {
            width: 100%;
        }
        .article-body,
        .article-content {
            word-break: break-word;
            overflow-wrap: anywhere;
        }
        .article-body img,
        .article-content img,
        .article-cover {
            display: block;
            max-width: 100% !important;
            height: auto !important;
        }
        .article-body table,
        .article-content table {
            display: block;
            width: 100%;
            max-width: 100%;
            overflow-x: auto;
            border-collapse: collapse;
        }
        .article-ad-slot {
            margin: 24px 0;
            padding: 14px 16px;
            border-radius: 12px;
            background: #f8fafc;
            border: 1px solid rgba(148, 163, 184, 0.24);
        }
        .article-ad-slot > :first-child {
            margin-top: 0;
        }
        .article-ad-slot > :last-child {
            margin-bottom: 0;
        }
        @media (max-width: 640px) {
            .article-wrapper {
                max-width: 100% !important;
                margin: 0 auto !important;
                padding: 20px 16px !important;
            }
            .article-header {
                margin-bottom: 24px !important;
                padding-bottom: 16px !important;
            }
            .article-title {
                font-size: 24px !important;
                line-height: 1.45 !important;
                letter-spacing: 0 !important;
                margin-bottom: 12px !important;
            }
            .article-meta,
            .article-author {
                font-size: 13px !important;
                line-height: 1.6 !important;
            }
            .article-cover {
                margin-bottom: 24px !important;
                border-radius: 8px !important;
            }
            .article-body,
            .article-content {
                font-size: 16px !important;
                line-height: 1.85 !important;
            }
            .article-body h2,
            .article-content h2 {
                font-size: 20px !important;
                line-height: 1.5 !important;
                margin-top: 28px !important;
                margin-bottom: 14px !important;
            }
            .article-body h3,
            .article-content h3 {
                font-size: 18px !important;
                line-height: 1.5 !important;
                margin-top: 22px !important;
                margin-bottom: 12px !important;
            }
            .article-body p,
            .article-content p,
            .article-body li,
            .article-content li {
                margin-bottom: 16px !important;
            }
            .article-body blockquote,
            .article-content blockquote {
                margin: 20px 0 !important;
                padding: 14px 16px !important;
            }
            .article-body ul,
            .article-body ol,
            .article-content ul,
            .article-content ol {
                padding-left: 22px !important;
            }
            .article-footer {
                margin-top: 32px !important;
                padding-top: 16px !important;
            }
            .article-ad-slot {
                margin: 20px 0 !important;
                padding: 12px 14px !important;
                border-radius: 10px !important;
            }
        }
        """

    def build_style_block(self, css: str) -> str:
        """拼装 style 标签"""
        return f"<style>{self.get_shared_css()}{css}</style>"

    def render_ad_slot(self, slot_html: str, slot_class: str) -> str:
        """渲染广告位片段"""
        if not slot_html or not slot_html.strip():
            return ""
        return f'<section class="{slot_class}">{slot_html}</section>'
    
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
