"""
默认模板 - 经典公众号风格
"""

from .base import BaseTemplate, TemplateConfig


class DefaultTemplate(BaseTemplate):
    """
    默认模板
    经典公众号排版风格，清晰易读
    """
    
    config = TemplateConfig(
        name="经典默认",
        description="经典公众号排版风格，清晰易读，适合大多数场景",
        author="AutoPlatform",
        version="1.0.0",
        supports_custom_css=True
    )
    
    def get_styles(self) -> str:
        return self.build_style_block("""
        .article-wrapper {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px 15px;
            background: #fff;
        }
        .article-header {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }
        .article-title {
            font-size: 26px;
            font-weight: 700;
            line-height: 1.4;
            color: #1a1a1a;
            margin-bottom: 16px;
        }
        .article-meta {
            display: flex;
            align-items: center;
            color: #8c8c8c;
            font-size: 14px;
        }
        .article-author {
            margin-right: 15px;
            color: #576b95;
        }
        .article-cover {
            width: 100%;
            max-height: 400px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .article-body {
            font-size: 17px;
            line-height: 1.8;
            color: #333;
        }
        .article-body h2 {
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 32px;
            margin-bottom: 16px;
            padding-left: 12px;
            border-left: 4px solid #576b95;
        }
        .article-body h3 {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-top: 24px;
            margin-bottom: 12px;
        }
        .article-body p {
            margin-bottom: 20px;
            text-align: justify;
        }
        .article-body img {
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .article-body blockquote {
            margin: 20px 0;
            padding: 16px 20px;
            background: #f7f7f7;
            border-left: 4px solid #576b95;
            color: #666;
            font-style: italic;
        }
        .article-body ul, .article-body ol {
            margin: 16px 0;
            padding-left: 28px;
        }
        .article-body li {
            margin-bottom: 8px;
        }
        .article-body a {
            color: #576b95;
            text-decoration: none;
        }
        .article-body a:hover {
            text-decoration: underline;
        }
        .article-footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 14px;
            text-align: center;
        }
        """)
    
    def render(self, title: str, content: str, author: str = "",
               cover_image: str = "", **kwargs) -> str:
        """渲染文章"""
        
        # 处理封面
        cover_html = f'<img src="{cover_image}" class="article-cover" alt="封面">' if cover_image else ""
        
        # 处理作者信息
        author_html = f'<span class="article-author">{author}</span>' if author else ""
        ad_header_html = self.render_ad_slot(
            kwargs.get("ad_header_html", ""),
            "article-ad-slot article-ad-slot--header"
        )
        ad_footer_html = self.render_ad_slot(
            kwargs.get("ad_footer_html", ""),
            "article-ad-slot article-ad-slot--footer"
        )
        
        body = f"""
        <div class="article-wrapper">
            <header class="article-header">
                <h1 class="article-title">{title}</h1>
                <div class="article-meta">
                    {author_html}
                </div>
            </header>
            
            {cover_html}
            {ad_header_html}
            
            <div class="article-body">
                {content}
            </div>
            
            {ad_footer_html}
            
        </div>
        """
        
        return self._wrap_html(body)
