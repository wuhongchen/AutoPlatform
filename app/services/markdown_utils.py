"""
Markdown 转换工具
提供 HTML↔Markdown 双向转换，用于全管道 Markdown 化。

转换点：
- 采集入库：HTML → Markdown (html_to_markdown)
- 发布/预览：Markdown → HTML (markdown_to_html)
"""

from __future__ import annotations

import re
from typing import Optional

from markdownify import markdownify as _markdownify
import markdown as _markdown


def html_to_markdown(html: str) -> str:
    """将 HTML 转换为 Markdown。

    专为微信公众号文章优化：
    - 保留图片、链接、表格
    - 去除行内样式、script/style 标签
    - 段落间用双换行分隔
    """
    if not html or not html.strip():
        return ""

    # markdownify 配置：只保留需要的标签进行转换，其余自动 strip
    md = _markdownify(
        html,
        heading_style="ATX",           # ## 标题格式
        bullets="-",                    # - 无序列表
        convert=[
            "h1", "h2", "h3", "h4", "h5", "h6",
            "p", "br",
            "strong", "b", "em", "i",
            "ul", "ol", "li",
            "a", "img",
            "table", "thead", "tbody", "tr", "th", "td",
            "blockquote", "pre", "code",
            "hr",
            "figure", "figcaption",
        ],
        escape_underscores=False,
        escape_asterisks=False,
    )

    # 清理多余空行
    md = re.sub(r"\n{4,}", "\n\n\n", md)
    return md.strip()


def markdown_to_html(md: str, theme: str = "default") -> str:
    """将 Markdown 转换为微信兼容的 HTML 片段。

    使用 Python markdown 库，启用：
    - fenced_code: 围栏代码块
    - tables: 表格
    - codehilite: 代码高亮（需要 highlight.js CSS）
    - nl2br: 单换行转 <br>

    Args:
        md: Markdown 文本
        theme: 主题名（default/grace/simple），影响 wrapper class

    Returns:
        带 CSS class 的 HTML 片段，可直接送入模板渲染
    """
    if not md or not md.strip():
        return ""

    extensions = [
        "fenced_code",
        "tables",
        "codehilite",
        "nl2br",
        "sane_lists",
    ]

    html = _markdown.markdown(md, extensions=extensions)

    # 包裹在 article-body 中，配合模板 CSS
    return f'<div class="article-body md-theme-{theme}">{html}</div>'


def normalize_to_markdown(content: str) -> str:
    """将任意内容归一化为 Markdown。

    - 如果看起来像 HTML → 转换为 Markdown
    - 如果已经是纯文本/Markdown → 直接返回

    用于后台手工创建文章时的内容归一化。
    """
    if not content or not content.strip():
        return ""

    raw = content.strip()

    # 检测是否为 HTML（包含 HTML 标签）
    looks_like_html = bool(re.search(r"</?[a-z][\s\S]*?>", raw, re.IGNORECASE))

    if looks_like_html:
        return html_to_markdown(raw)

    # 已经是纯文本或 Markdown，直接返回
    return raw


def extract_title_from_markdown(md: str) -> Optional[str]:
    """从 Markdown 文本中提取第一个一级标题作为文章标题。"""
    if not md:
        return None
    match = re.match(r"^#\s+(.+)$", md.strip(), re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def strip_markdown_wrapper(text: str) -> str:
    """去除 AI 输出中可能的 Markdown 代码围栏包裹。

    例如：
    ```markdown ... ```  →  内容本体
    ``` ... ```  →  内容本体
    """
    if not text:
        return ""

    text = text.strip()

    # 去除开头的 ```markdown 或 ```
    text = re.sub(r"^```(?:markdown|md)?\s*\n?", "", text, flags=re.IGNORECASE)

    # 去除末尾的 ```
    text = re.sub(r"\n?\s*```\s*$", "", text)

    return text.strip()
