"""
商务模板 - 专业商务风格
"""

from .base import BaseTemplate, TemplateConfig


class BusinessTemplate(BaseTemplate):
    """
    商务模板
    专业商务风格，稳重正式，适合商业分析类内容
    """
    
    config = TemplateConfig(
        name="商务风格",
        description="专业商务风格，稳重正式，适合商业分析和行业报告",
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
            padding: 40px 30px;
            background: #fff;
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            color: #2c3e50;
        }
        .article-header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            margin: -40px -30px 40px -30px;
            padding: 50px 30px;
            color: #fff;
        }
        .article-title {
            font-size: 30px;
            font-weight: 300;
            line-height: 1.3;
            margin-bottom: 16px;
            letter-spacing: -0.5px;
        }
        .article-meta {
            font-size: 13px;
            opacity: 0.8;
        }
        .article-author {
            font-weight: 500;
        }
        .article-cover {
            width: 100%;
            max-height: 350px;
            object-fit: cover;
            border-radius: 6px;
            margin-bottom: 40px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .article-body {
            font-size: 16px;
            line-height: 1.8;
            color: #34495e;
        }
        .article-body h2 {
            font-size: 22px;
            font-weight: 600;
            color: #2c3e50;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 3px solid #3498db;
        }
        .article-body h3 {
            font-size: 18px;
            font-weight: 600;
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        .article-body p {
            margin-bottom: 20px;
            text-align: justify;
        }
        .article-body img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            margin: 24px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .article-body blockquote {
            margin: 28px 0;
            padding: 20px 24px;
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            color: #5a6c7d;
            font-style: normal;
        }
        .article-body blockquote cite {
            display: block;
            margin-top: 12px;
            font-size: 14px;
            color: #7f8c8d;
            font-style: italic;
        }
        .article-body ul, .article-body ol {
            margin: 20px 0;
            padding-left: 28px;
        }
        .article-body li {
            margin-bottom: 10px;
        }
        .article-body a {
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
        }
        .article-body a:hover {
            color: #2980b9;
            text-decoration: underline;
        }
        .article-body strong {
            color: #2c3e50;
            font-weight: 600;
        }
        .article-body table {
            width: 100%;
            border-collapse: collapse;
            margin: 24px 0;
            font-size: 14px;
        }
        .article-body th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
        }
        .article-body td {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }
        .article-footer {
            margin-top: 60px;
            padding-top: 30px;
            border-top: 1px solid #e9ecef;
            color: #6c757d;
            font-size: 13px;
            text-align: center;
        }
        .key-point {
            background: #e8f4f8;
            padding: 20px;
            border-radius: 6px;
            margin: 24px 0;
            border-left: 4px solid #3498db;
        }
        .key-point-title {
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        </style>
        """
    
    def render(self, title: str, content: str, author: str = "",
               cover_image: str = "", **kwargs) -> str:
        """渲染文章"""
        
        cover_html = f'<img src="{cover_image}" class="article-cover" alt="封面">' if cover_image else ""
        author_html = f'<span class="article-author">{author}</span>' if author else ""
        
        body = f"""
        <div class="article-wrapper">
            <header class="article-header">
                <h1 class="article-title">{title}</h1>
                <div class="article-meta">
                    {author_html}
                </div>
            </header>
            
            {cover_html}
            
            <div class="article-body">
                {content}
            </div>
            
            <footer class="article-footer">
                <p>本内容仅供参考，转载请注明出处</p>
            </footer>
        </div>
        """
        
        return self._wrap_html(body)
