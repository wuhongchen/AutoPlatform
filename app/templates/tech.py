"""
科技风模板 - 现代科技风格
"""

from .base import BaseTemplate, TemplateConfig


class TechTemplate(BaseTemplate):
    """
    科技模板
    现代科技风格，渐变色彩，适合科技类内容
    """
    
    config = TemplateConfig(
        name="科技风格",
        description="现代科技风格，深色主题，渐变色彩，适合科技类内容",
        author="AutoPlatform",
        version="1.0.0",
        supports_custom_css=True
    )
    
    def get_styles(self) -> str:
        return """
        <style>
        .article-wrapper {
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #eaeaea;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .article-header {
            text-align: center;
            margin-bottom: 50px;
            padding: 40px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .article-title {
            font-size: 32px;
            font-weight: 700;
            line-height: 1.3;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 16px;
        }
        .article-author {
            color: #8892b0;
            font-size: 14px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .article-cover {
            width: 100%;
            max-height: 450px;
            object-fit: cover;
            border-radius: 12px;
            margin-bottom: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .article-body {
            font-size: 17px;
            line-height: 1.9;
            color: #ccd6f6;
        }
        .article-body h2 {
            font-size: 24px;
            font-weight: 600;
            color: #64ffda;
            margin-top: 48px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid rgba(100, 255, 218, 0.3);
        }
        .article-body h3 {
            font-size: 20px;
            font-weight: 600;
            color: #8892b0;
            margin-top: 32px;
            margin-bottom: 16px;
        }
        .article-body p {
            margin-bottom: 20px;
        }
        .article-body img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 24px 0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .article-body blockquote {
            margin: 32px 0;
            padding: 24px;
            background: rgba(102, 126, 234, 0.1);
            border-left: 4px solid #667eea;
            border-radius: 0 8px 8px 0;
            color: #a8b2d1;
        }
        .article-body code {
            background: rgba(100, 255, 218, 0.1);
            color: #64ffda;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: "Fira Code", monospace;
            font-size: 0.9em;
        }
        .article-body pre {
            background: #0a192f;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 24px 0;
        }
        .article-body ul, .article-body ol {
            margin: 20px 0;
            padding-left: 32px;
        }
        .article-body li {
            margin-bottom: 12px;
        }
        .article-body li::marker {
            color: #64ffda;
        }
        .article-body a {
            color: #64ffda;
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.3s;
        }
        .article-body a:hover {
            border-bottom-color: #64ffda;
        }
        .article-footer {
            margin-top: 60px;
            padding-top: 30px;
            border-top: 1px solid rgba(255,255,255,0.1);
            text-align: center;
            color: #8892b0;
            font-size: 14px;
        }
        .highlight {
            background: linear-gradient(120deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
            padding: 2px 6px;
            border-radius: 4px;
        }
        </style>
        """
    
    def render(self, title: str, content: str, author: str = "",
               cover_image: str = "", **kwargs) -> str:
        """渲染文章"""
        
        cover_html = f'<img src="{cover_image}" class="article-cover" alt="封面">' if cover_image else ""
        author_html = f'<div class="article-author">{author}</div>' if author else ""
        
        body = f"""
        <div class="article-wrapper">
            <header class="article-header">
                <h1 class="article-title">{title}</h1>
                {author_html}
            </header>
            
            {cover_html}
            
            <div class="article-body">
                {content}
            </div>
            
            <footer class="article-footer">
                <p>Powered by AutoPlatform</p>
            </footer>
        </div>
        """
        
        return self._wrap_html(body)
