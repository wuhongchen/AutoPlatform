"""
贴图模板 — 图片消息专用排版
"""

from .base import BaseTemplate, TemplateConfig


class StickerTemplate(BaseTemplate):
    config = TemplateConfig(
        name="贴图",
        description="图片画廊风格，适合多图展示，大图全宽，标题突出",
        version="1.0.0",
    )

    def render(self, title: str = "", content: str = "", author: str = "", **kwargs) -> str:
        images = kwargs.get("images", [])
        description = kwargs.get("description", "")
        source_url = kwargs.get("source_url", "")
        tags = kwargs.get("tags", [])

        image_html = ""
        for img in images:
            url = img if isinstance(img, str) else img.get("url", "")
            alt = img.get("alt", "") if isinstance(img, dict) else ""
            image_html += f'<figure class="sticker-image"><img src="{url}" alt="{alt}"/></figure>\n'

        description_html = ""
        if description:
            description_html = f'<section class="sticker-desc"><p>{description}</p></section>'

        tags_html = ""
        if tags:
            tag_spans = " ".join(f'<span class="sticker-tag">#{t}</span>' for t in tags)
            tags_html = f'<section class="sticker-tags">{tag_spans}</section>'

        source_html = ""
        if source_url:
            source_html = f'<section class="sticker-source"><a href="{source_url}">阅读原文</a></section>'

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title or '贴图'}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#fff;color:#1a1a1a;line-height:1.6}}
  .sticker-container{{max-width:600px;margin:0 auto;padding:0}}
  .sticker-header{{padding:28px 20px 10px;text-align:center}}
  .sticker-header h1{{font-size:22px;font-weight:700;color:#111;margin-bottom:4px}}
  .sticker-header .author{{font-size:14px;color:#999}}
  .sticker-desc{{padding:8px 20px 20px;font-size:15px;color:#555;text-align:center;line-height:1.8}}
  .sticker-image{{margin:0;padding:0}}
  .sticker-image img{{display:block;width:100%;height:auto}}
  .sticker-image+.sticker-image{{margin-top:0}}
  .sticker-tags{{padding:12px 20px 4px;text-align:center}}.sticker-tag{{display:inline-block;margin:0 6px 8px;font-size:13px;color:#576b95;background:#f0f4ff;padding:2px 10px;border-radius:12px}}.sticker-source{{padding:4px 20px 20px;text-align:center}}.sticker-source a{{color:#576b95;font-size:14px;text-decoration:none}}.sticker-footer{{padding:20px;text-align:center;font-size:12px;color:#bbb}}
</style>
</head>
<body>
<div class="sticker-container">
  {image_html}
  <header class="sticker-header">
    <h1>{title or '贴图'}</h1>
    {f'<div class="author">{author}</div>' if author else ''}
  </header>
  {description_html}
  {tags_html}
  {source_html}
  <footer class="sticker-footer">Powered by AutoPlatform</footer>
</div>
</body>
</html>"""
