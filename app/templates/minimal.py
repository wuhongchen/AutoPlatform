"""
极简模板 - 干净简洁
"""

from .base import BaseTemplate, TemplateConfig


class MinimalTemplate(BaseTemplate):
    """
    极简模板
    干净简洁，去除多余装饰，专注内容本身
    """
    
    config = TemplateConfig(
        name="极简风格",
        description="去除多余装饰，干净简洁，专注内容本身",
        author="AutoPlatform",
        version="1.0.0",
        supports_custom_css=True
    )
    
    def get_styles(self) -> str:
        return self.build_style_block("""
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        .article-wrapper {
            max-width: 700px;
            margin: 28px auto;
            padding: 0 18px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .article-title {
            font-size: 32px;
            font-weight: 400;
            line-height: 1.3;
            color: #000;
            margin-bottom: 10px;
            letter-spacing: 0;
        }
        .article-author {
            font-size: 14px;
            color: #666;
            margin-bottom: 28px;
        }
        .article-cover {
            width: 100%;
            margin-bottom: 40px;
        }
        .article-body {
            font-size: 18px;
            line-height: 1.9;
            color: #222;
        }
        .article-body h2 {
            font-size: 24px;
            font-weight: 400;
            margin-top: 48px;
            margin-bottom: 20px;
            color: #000;
        }
        .article-body h3 {
            font-size: 20px;
            font-weight: 500;
            margin-top: 36px;
            margin-bottom: 16px;
        }
        .article-body p {
            margin-bottom: 24px;
        }
        .article-body img {
            max-width: 100%;
            height: auto;
            margin: 32px 0;
        }
        .article-body blockquote {
            margin: 32px 0;
            padding: 0 24px;
            border-left: 2px solid #000;
            color: #555;
        }
        .article-body ul, .article-body ol {
            margin: 24px 0;
            padding-left: 32px;
        }
        .article-body li {
            margin-bottom: 12px;
        }
        .article-body a {
            color: #000;
            text-decoration: underline;
            text-underline-offset: 3px;
        }
        .article-footer {
            margin-top: 80px;
            padding-top: 40px;
            border-top: 1px solid #eee;
            font-size: 13px;
            color: #999;
        }
        """)
    
    def render(self, title: str, content: str, author: str = "",
               cover_image: str = "", **kwargs) -> str:
        """渲染文章"""
        
        cover_html = f'<img src="{cover_image}" class="article-cover" alt="">' if cover_image else ""
        author_html = f'<div class="article-author">{author}</div>' if author else ""
        ad_header_html = self.render_ad_slot(
            kwargs.get("ad_header_html", ""),
            "article-ad-slot article-ad-slot--header"
        )
        ad_footer_html = self.render_ad_slot(
            kwargs.get("ad_footer_html", ""),
            "article-ad-slot article-ad-slot--footer"
        )
        
        body = f"""
        <article class="article-wrapper">
            <h1 class="article-title">{title}</h1>
            {author_html}
            {cover_html}
            {ad_header_html}
            <div class="article-body">
                {content}
            </div>
            {ad_footer_html}
        </article>
        """
        
        return self._wrap_html(body)
