from openai import OpenAI
from config import Config
import time
import re
import os

class DeepMPProcessor:
    """
    公众号深度增强处理器 (MP-Deep-Pro)
    目标：结构化、专业深度、完全原创长文
    """
    
    def __init__(self, api_key=None, base_url=None, feishu_client=None):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_ENDPOINT.replace("/chat/completions", "")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.feishu = feishu_client  # 用于下载飞书内部图片

    # --- 阶段一：逻辑结构分析 (Structure Analyzer) ---
    def _get_analysis_prompt(self, content):
        return f"""
你是一位深耕行业十年的顶级科技媒体主编。请对以下内容进行深度解构，为后续原创长文提供逻辑支架。

**待分析内容（节选）:**
{content}

**请严格输出 JSON 结构:**
{{
  "core_topic": "一句话概括文章核心议题",
  "technical_principles": "深入浅出解析其背后的核心技术或商业逻辑",
  "key_facts": ["核心事实1", "核心数据2"],
  "narrative_logic": ["逻辑起点", "冲突点", "深度挖掘", "行动建议"]
}}
"""

    # --- 阶段二：完全原创长文写作 (Original Deep Writer) ---
    def _get_generation_prompt(self, analysis, image_count):
        img_hint = "\n".join([f"  - [IMAGE_{i}]" for i in range(image_count)]) if image_count else "  - (本次抓取无原文配图)"
        return f"""
你是一位获过奖的深度特稿记者，擅长撰写逻辑严密、细节丰满的公众号原创长文。

**本文创作蓝图（来自主编分析）：**
{analysis}

**你可以使用的图片资源（请在正文中通过占位符调用）：**
{img_hint}

**【写作铁律：拒绝平庸，追求行业纵深】**
1. **内容饱满**：严禁简单的文字搬运。必须加入行业纵深对比、底层逻辑推演以及趋势预判。
2. **场景驱动**：用具体的“业务场景”带入，确保内容具有实战参考价值。
3. **【必须插图】**：请务必在正文的章节过渡处、核心观点解析后，插入图片占位符 `[IMAGE_N]`。至少插入 3-5 张图（如果资源充足的话）。
4. **字数与容量**：目标 1500-2500 字。内容必须扎实。
5. **去 AI 套语**：语言带有一个顶级记者的主观洞察力。不要说“总之”、“综上所述”等 AI 常用词。

**视觉排版规范（必须直接写在 HTML 标签的 style 属性中）：**
- **导读区**：使用 `<section style="background:#f8f9fa; border-radius:12px; padding:25px; margin:30px 0; border:1px solid #e9ecef;">`。
- **正文段落**：使用 `<p style="line-height:1.8; margin-bottom:20px; color:#333; text-align:justify;">`。
- **H2 章节**：使用 `<h2 style="font-size:1.4em; color:#1a1a1a; padding-bottom:10px; border-bottom:3px solid #007aff; margin-top:40px; margin-bottom:20px; display:inline-block;">`。
- **引用/点评**：使用 `<blockquote style="color:#555; background:#fffaf0; border-left:6px solid #f39c12; padding:20px; margin:30px 0; border-radius:4px;">`。
- **总结区**：使用 `<section style="background:linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color:#fff; padding:35px; border-radius:15px; margin-top:50px;">`。

**文章组织结构：**
[导读区] -> [引言] -> [H2 实战分析] -> (适当位置插入 [IMAGE_N]) -> [总结区]

**注意：**
- 标题请放在第一行，带上 `【标题：...】` 标记。
- 直接输出微信公众号 HTML 源码，不要 Markdown，不要解释文字。
"""

    def process(self, url, scraped_data, publisher=None):
        """
        publisher: 可选传入 WeChatPublisher 实例，用于将正文图片上传到微信素材库
        """
        image_urls = scraped_data.get('images', [])
        
        # ── 阶段一：结构分析 ──────────
        print(f"🔍 [MP-Deep] 阶段一：主编进行深度结构分析...")
        raw_excerpt = scraped_data['content_raw'][:2000]
        analysis_resp = self.client.chat.completions.create(
            model=Config.VOLC_ARK_MODEL_ID or "doubao-seed-2-0-pro-260215",
            messages=[{"role": "user", "content": self._get_analysis_prompt(raw_excerpt)}]
        )
        analysis_map = analysis_resp.choices[0].message.content
        
        # ── 阶段二：完全原创写作 ─────────
        print(f"🖋️ [MP-Deep] 阶段二：完全原创深度长文写作 (temperature=0.92)...")
        gen_resp = self.client.chat.completions.create(
            model=Config.VOLC_ARK_MODEL_ID or "doubao-seed-2-0-pro-260215",
            messages=[{"role": "user", "content": self._get_generation_prompt(analysis_map, len(image_urls))}],
            max_tokens=4000,
            temperature=0.92
        )
        
        content_raw_output = gen_resp.choices[0].message.content
        print(f"   📊 原始生成长度: {len(content_raw_output)} 字符")
        
        # 清理 Markdown 代码块标记
        content_cleaned = re.sub(r'```(?:html|markdown)?\n?', '', content_raw_output, flags=re.IGNORECASE)
        content_cleaned = content_cleaned.replace('```', '').strip()
        
        # ── 阶段三：图片处理 ───────
        image_mapping = self._upload_images_to_wechat(image_urls, publisher)
        
        # 替换占位符
        final_content = self._post_process_content(content_cleaned, image_mapping)
        print(f"   📊 后处理后长度: {len(final_content)} 字符")
        
        # 提取标题
        title = self._get_pure_title(content_cleaned)
        
        return {
            "full_content": final_content,
            "title": title,
            "analysis": analysis_map
        }

    def _upload_images_to_wechat(self, image_urls, publisher):
        """将原文图片下载后上传至微信素材库，返回 {index: wechat_url} 映射"""
        if not publisher or not image_urls:
            return {}
        
        import requests as req
        
        if not publisher.token:
            publisher._get_token()
        if not publisher.token:
            print("   ⚠️ 微信 token 获取失败，图片将使用原文外链")
            return {i: url for i, url in enumerate(image_urls)}
        
        wechat_mapping = {}
        MIN_IMG_SIZE    = 5 * 1024   # 小于 5KB 的装饰性小图直接跳过
        max_upload_count = 12
        uploaded = 0
        
        print(f"   📸 开始处理图片，共 {len(image_urls)} 张...")
        for i, src_url in enumerate(image_urls):
            if uploaded >= max_upload_count: break
            
            try:
                img_content = None
                if str(src_url).startswith("feishu://") and self.feishu:
                    img_content = self.feishu._download_image(src_url)
                else:
                    r = req.get(src_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                    if r.status_code == 200:
                        img_content = r.content
                
                if not img_content or len(img_content) < MIN_IMG_SIZE:
                    continue
                
                # 使用 WeChatPublisher 里的新方法
                wx_url = publisher.upload_article_image(img_content)
                if wx_url:
                    wechat_mapping[i] = wx_url
                    uploaded += 1
                    print(f"      [{i+1}] ✅ 上传成功 → 微信 CDN")
                
                time.sleep(0.2)
            except Exception as e:
                print(f"      [{i+1}] ⚠️ 异常: {e}")
        
        return wechat_mapping

    def _post_process_content(self, text, image_mapping):
        """根据映射替换 [IMAGE_N] 并清除冗余标题行"""
        processed = text
        
        # 1. 移除内容体中的标题标记行 (这些用于提取 title 字段，不应出现在最终正文内)
        processed = re.sub(r'^【标题：.*?】\s*\n?', '', processed, flags=re.MULTILINE)
        processed = re.sub(r'^(?:标题|Title)[:：].*?\n?', '', processed, flags=re.MULTILINE)
        processed = re.sub(r'^#[#\s]+.*?\n?', '', processed, flags=re.MULTILINE) # 移除可能的 Markdown H1/H2 标题行
        
        # 2. 移除 AI 可能产生的“导读”字样或空行开头
        processed = processed.lstrip()

        # 3. 替换占位符
        for i, url in image_mapping.items():
            placeholder = f"[IMAGE_{i}]"
            img_html = (
                f'<div style="text-align:center;margin:30px 0;">'
                f'<img src="{url}" style="max-width:100%;border-radius:8px;'
                f'box-shadow:0 4px 20px rgba(0,0,0,0.12);">'
                f'</div>'
            )
            processed = processed.replace(placeholder, img_html)
        
        # 4. 兜底：清除剩下的占位符
        processed = re.sub(r'\[IMAGE_\d+\]', '', processed)
        return processed.strip()

    def _get_pure_title(self, text):
        """提取纯净标题，强力清除 AI 痕迹"""
        try:
            # 基础清理
            text = re.sub(r'^【AI改后稿】\s*', '', text)
            text = re.sub(r'^(?:标题|Title)[:：]\s*', '', text)
            
            patterns = [
                r"【标题：(.*?)】",
                r"标题：(.*?)\n",
                r"标题:(.*?)\n",
                r"## (.*?)\n",
                r"<h1[^>]*>(.*?)</h1>",
                r"<h2[^>]*>(.*?)</h2>"
            ]
            for p in patterns:
                match = re.search(p, text, re.IGNORECASE)
                if match:
                    t = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    t = re.sub(r'^【AI改后稿】\s*', '', t)
                    if t and len(t) > 3:
                        return t
            
            # 如果没找到标记，取前几行非 HTML 的文字
            lines = text.split('\n')
            for line in lines[:10]:
                line = line.strip()
                if not line or line.startswith('<'): continue
                clean = re.sub(r'\[IMAGE_\d+\]', '', line).replace('#', '').strip()
                clean = re.sub(r'<[^>]+>', '', clean).strip()
                clean = re.sub(r'^【AI改后稿】\s*', '', clean)
                if clean and len(clean) > 5:
                    return clean
                    
            return "深度视角 | 行业精选"
        except Exception:
            return "深度视角 | 行业精选"

class WeChatFormatter:
    """公众号 HTML 美化器（移动优先）。

    能力增强：
    - DOM 级重排（替代简单正则替换，避免结构破坏）
    - Markdown 兜底渲染（markdown-it-py, GitHub: executablebooks/markdown-it-py）
    - 样式参考 doocs/md 主题体系，适配公众号窄屏阅读
    """

    _TAG_STYLE_MAP = {
        "p": "margin: 16px 0; font-size: 16px; line-height: 1.9; color: #1f2937; text-align: justify; text-indent: 2em; letter-spacing: 0.02em; word-break: break-word;",
        "h1": "margin: 28px 0 18px; padding-bottom: 10px; border-bottom: 2px solid #2563eb; font-size: 24px; line-height: 1.4; color: #0f172a; text-align: center; font-weight: 700;",
        "h2": "margin: 30px 0 14px; padding: 6px 10px 6px 12px; border-left: 4px solid #2563eb; background: #eef4ff; border-radius: 6px; font-size: 20px; line-height: 1.5; color: #0f172a; font-weight: 700;",
        "h3": "margin: 24px 0 12px; padding-left: 9px; border-left: 3px solid #93c5fd; font-size: 18px; line-height: 1.55; color: #1e3a8a; font-weight: 700;",
        "blockquote": "margin: 18px 0; padding: 12px 14px; border-left: 4px solid #60a5fa; background: #f8fbff; border-radius: 8px; color: #334155; font-size: 15px; line-height: 1.8;",
        "ul": "margin: 12px 0; padding-left: 1.2em; color: #1f2937;",
        "ol": "margin: 12px 0; padding-left: 1.2em; color: #1f2937;",
        "li": "margin: 8px 0; font-size: 16px; line-height: 1.8; color: #1f2937;",
        "pre": "margin: 14px 0; padding: 12px 14px; background: #0f172a; color: #e2e8f0; border-radius: 10px; overflow-x: auto; font-size: 13px; line-height: 1.7;",
        "code": "padding: 0.1em 0.35em; border-radius: 4px; background: #eef2ff; color: #3730a3; font-family: Menlo, Monaco, Consolas, monospace; font-size: 0.92em;",
        "table": "width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; line-height: 1.6;",
        "th": "padding: 8px 10px; border: 1px solid #e5e7eb; background: #f8fafc; color: #0f172a; font-weight: 600; text-align: left;",
        "td": "padding: 8px 10px; border: 1px solid #e5e7eb; color: #1f2937; vertical-align: top;",
        "a": "color: #2563eb; text-decoration: underline; text-underline-offset: 2px; word-break: break-all;",
        "strong": "font-weight: 700; color: #111827;",
        "b": "font-weight: 700; color: #111827;",
        "em": "font-style: italic; color: #374151;",
        "hr": "border: none; border-top: 1px solid #e5e7eb; margin: 18px 0;",
    }

    _WRAPPER_STYLE = (
        "font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', "
        "'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif; "
        "max-width: 677px; margin: 0 auto; padding: 12px 14px; background: #ffffff; "
        "color: #111827; box-sizing: border-box; overflow-wrap: break-word; word-break: break-word;"
    )

    @staticmethod
    def _append_style(tag, style_text):
        if not style_text:
            return
        existing = (tag.get("style") or "").strip().rstrip(";")
        merged = f"{existing}; {style_text}" if existing else style_text
        tag["style"] = merged.strip()

    @staticmethod
    def _strip_leading_title_lines(raw_text):
        lines = (raw_text or "").splitlines()
        out = []
        content_started = False
        title_pattern = re.compile(r'^(【.*?标题.*?】|(?:标题|Title|文章标题)[:：].*|#+\s+.*)$', re.IGNORECASE)
        for line in lines:
            s = line.strip()
            if not content_started:
                if not s:
                    continue
                if title_pattern.match(s):
                    continue
                # 纯 H1/H2 行也去掉
                if re.match(r'^<h[12][^>]*>.*?</h[12]>$', s, re.IGNORECASE):
                    continue
                content_started = True
            out.append(line)
        return "\n".join(out).strip()

    @staticmethod
    def _looks_like_markdown(text):
        if not text:
            return False
        if re.search(r'</?(p|h[1-6]|div|section|img|blockquote|ul|ol|li|table|pre|code)\b', text, re.IGNORECASE):
            return False
        indicators = [
            r'^\s{0,3}#{1,6}\s+',
            r'^\s*[-*+]\s+',
            r'^\s*\d+\.\s+',
            r'```',
            r'^\s*>\s+',
            r'!\[.*?\]\(.*?\)',
            r'\[.*?\]\(.*?\)'
        ]
        return any(re.search(p, text, re.MULTILINE) for p in indicators)

    @staticmethod
    def _maybe_markdown_to_html(raw_text):
        text = (raw_text or "").strip()
        if not text:
            return ""
        if not WeChatFormatter._looks_like_markdown(text):
            return text
        try:
            # GitHub: https://github.com/executablebooks/markdown-it-py
            from markdown_it import MarkdownIt
            md = MarkdownIt("commonmark", {"breaks": True, "linkify": True}).enable("table")
            return md.render(text)
        except Exception:
            return WeChatFormatter._simple_markdown_to_html(text)

    @staticmethod
    def _simple_markdown_to_html(text):
        """无 markdown-it-py 时的轻量兜底解析，保证可读性不塌陷。"""
        from html import escape

        def inline(md_line):
            escaped = escape(md_line)
            escaped = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img alt="\1" src="\2" />', escaped)
            escaped = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', escaped)
            escaped = re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)
            return escaped

        lines = text.splitlines()
        html_parts = []
        in_ul = False
        in_ol = False

        def close_lists():
            nonlocal in_ul, in_ol
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False

        for raw in lines:
            line = raw.strip()
            if not line:
                close_lists()
                continue

            if line.startswith("### "):
                close_lists()
                html_parts.append(f"<h3>{inline(line[4:])}</h3>")
                continue
            if line.startswith("## "):
                close_lists()
                html_parts.append(f"<h2>{inline(line[3:])}</h2>")
                continue
            if line.startswith("# "):
                close_lists()
                html_parts.append(f"<h1>{inline(line[2:])}</h1>")
                continue
            if line.startswith("> "):
                close_lists()
                html_parts.append(f"<blockquote><p>{inline(line[2:])}</p></blockquote>")
                continue

            m_ol = re.match(r'^(\d+)\.\s+(.*)$', line)
            if m_ol:
                if in_ul:
                    html_parts.append("</ul>")
                    in_ul = False
                if not in_ol:
                    html_parts.append("<ol>")
                    in_ol = True
                html_parts.append(f"<li>{inline(m_ol.group(2))}</li>")
                continue

            if re.match(r'^[-*+]\s+.+$', line):
                if in_ol:
                    html_parts.append("</ol>")
                    in_ol = False
                if not in_ul:
                    html_parts.append("<ul>")
                    in_ul = True
                html_parts.append(f"<li>{inline(line[2:])}</li>")
                continue

            close_lists()
            html_parts.append(f"<p>{inline(line)}</p>")

        close_lists()
        return "\n".join(html_parts).strip()

    @staticmethod
    def _extract_core_points(text):
        compact = re.sub(r'\s+', ' ', (text or '')).strip()
        m = re.match(r'^(?:📌\s*)?本文核心看点[:：]\s*(.+)$', compact)
        if not m:
            return None
        rest = m.group(1).strip()
        raw_items = re.split(r'\s*(?=\d+[\.、]\s*)', rest)
        items = []
        for it in raw_items:
            s = re.sub(r'^\d+[\.、]\s*', '', it).strip(' ；;，,。')
            if s:
                items.append(s)
        return items if len(items) >= 2 else None

    @staticmethod
    def _split_long_paragraph(text, target=120):
        text = (text or "").strip()
        if len(text) < 180:
            return [text] if text else []
        parts = re.split(r'(?<=[。！？!?])\s*', text)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 3:
            return [text]

        segs = []
        buf = ""
        for sent in parts:
            if len(buf) + len(sent) <= target or len(buf) < int(target * 0.65):
                buf += sent
            else:
                segs.append(buf.strip())
                buf = sent
        if buf:
            segs.append(buf.strip())
        return segs if len(segs) >= 2 else [text]

    @staticmethod
    def _enhance_semantic_structure(soup, container):
        paragraphs = list(container.find_all("p"))
        for p in paragraphs:
            text = p.get_text(" ", strip=True)
            if not text:
                continue

            # 1) 核心看点段 → H2 + 有序列表
            core_items = WeChatFormatter._extract_core_points(text)
            if core_items:
                h2 = soup.new_tag("h2")
                h2.string = "本文核心看点"
                ol = soup.new_tag("ol")
                for item in core_items:
                    li = soup.new_tag("li")
                    li.string = item
                    ol.append(li)
                p.insert_before(h2)
                h2.insert_after(ol)
                p.decompose()
                continue

            # 2) 疑似小标题段落提升层级
            compact = re.sub(r'\s+', ' ', text).strip()
            is_heading_like = (
                (len(compact) <= 32 and compact.endswith(("：", ":")))
                or (len(compact) <= 26 and re.match(r'^(?:\d+[\.、]|[一二三四五六七八九十]+[、.．]|[(（]?[一二三四五六七八九十0-9]{1,2}[)）])', compact))
            )
            if is_heading_like and not re.search(r'[。！？!?]', compact):
                h3 = soup.new_tag("h3")
                h3.string = compact.rstrip("：:")
                p.insert_before(h3)
                p.decompose()
                continue

            # 3) 过长段落按句拆分，增强呼吸感
            segs = WeChatFormatter._split_long_paragraph(compact)
            if len(segs) >= 2:
                for seg in segs:
                    np = soup.new_tag("p")
                    np.string = seg
                    p.insert_before(np)
                p.decompose()

    @staticmethod
    def _inject_auto_subheads(soup, container):
        """当正文缺少标题层级时，自动插入小标题，增强段落感。"""
        has_heading = bool(container.find(["h2", "h3"]))
        if has_heading:
            return

        paragraphs = [
            p for p in container.find_all("p")
            if len(p.get_text(" ", strip=True)) >= 38
        ]
        if len(paragraphs) < 5:
            return

        plan = [
            (1, "问题背景"),
            (3, "实操路径"),
            (5, "关键结论"),
        ]
        for idx, title in reversed(plan):
            if idx < len(paragraphs):
                h3 = soup.new_tag("h3")
                h3.string = title
                paragraphs[idx].insert_before(h3)

    @staticmethod
    def _decorate_visual_blocks(soup, container):
        """增加导语卡片和看点卡片，让视觉层次更明显。"""
        # 1) 导语卡片：首个长段落转为浅底色卡片
        first_para = None
        for p in container.find_all("p"):
            txt = p.get_text(" ", strip=True)
            if len(txt) >= 50:
                first_para = p
                break
        if first_para:
            txt = first_para.get_text(" ", strip=True)
            if 50 <= len(txt) <= 260:
                card = soup.new_tag("section")
                card["style"] = (
                    "margin: 10px 0 20px; padding: 16px 14px; border-radius: 12px; "
                    "background: linear-gradient(135deg, #f4f8ff 0%, #eef3ff 100%); "
                    "border: 1px solid #dbe7ff;"
                )
                badge = soup.new_tag("div")
                badge["style"] = (
                    "display: inline-block; margin-bottom: 8px; padding: 2px 8px; "
                    "font-size: 12px; color: #1d4ed8; background: #dbeafe; border-radius: 999px;"
                )
                badge.string = "导语"
                body = soup.new_tag("div")
                body["style"] = (
                    "font-size: 16px; line-height: 1.9; color: #1e293b; text-align: justify; "
                    "word-break: break-word;"
                )
                body.string = txt
                card.append(badge)
                card.append(body)
                first_para.replace_with(card)

        # 2) 核心看点卡片：h2=本文核心看点 + 紧随列表打包
        for h2 in list(container.find_all("h2")):
            if h2.get_text(" ", strip=True) != "本文核心看点":
                continue
            nxt = h2.find_next_sibling()
            if not nxt or nxt.name not in ("ol", "ul"):
                continue
            card = soup.new_tag("section")
            card["style"] = (
                "margin: 14px 0 20px; padding: 12px 12px 6px; border-radius: 12px; "
                "background: #f8fbff; border: 1px solid #dbeafe;"
            )
            h2.insert_before(card)
            card.append(h2.extract())
            card.append(nxt.extract())

    @staticmethod
    def _is_enabled(raw_value):
        return str(raw_value or "").strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _build_ad_block(soup):
        """构建通用广告位区块（内容由环境变量配置）。"""
        if not WeChatFormatter._is_enabled(Config.WECHAT_AD_ENABLED):
            return None

        ad_text = (Config.WECHAT_AD_TEXT or "").strip()
        ad_img_path = (Config.WECHAT_AD_IMAGE_PATH or "").strip()
        ad_img_url = (Config.WECHAT_AD_IMAGE_URL or "").strip()
        if not ad_text:
            if not ad_img_path and not ad_img_url:
                return None

        ad_title = (Config.WECHAT_AD_TITLE or "推广信息").strip()
        ad_link_text = (Config.WECHAT_AD_LINK_TEXT or "").strip()
        ad_link_url = (Config.WECHAT_AD_LINK_URL or "").strip()
        ad_img_link = (Config.WECHAT_AD_IMAGE_LINK_URL or "").strip() or ad_link_url

        wrapper = soup.new_tag("section")
        wrapper["data-ad-block"] = "1"
        wrapper["style"] = (
            "margin: 16px 0 20px; padding: 12px 12px 10px; border-radius: 12px; "
            "background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%); border: 1px solid #fed7aa;"
        )

        badge = soup.new_tag("div")
        badge["style"] = (
            "display: inline-block; margin-bottom: 8px; padding: 2px 8px; font-size: 12px; "
            "color: #9a3412; background: #ffedd5; border-radius: 999px;"
        )
        badge.string = ad_title
        wrapper.append(badge)

        img_src = ""
        if ad_img_path and os.path.exists(ad_img_path):
            # 通过占位协议让发布环节上传到微信 CDN，再回填可用 URL
            img_src = "local://wechat_ad_image"
        elif ad_img_url:
            img_src = ad_img_url

        if img_src:
            img = soup.new_tag("img", src=img_src)
            img["alt"] = ad_title or "推广图片"
            img["style"] = (
                "display: block; width: 100%; max-width: 100%; height: auto; margin: 2px auto 8px; "
                "border-radius: 10px; border: 1px solid #fed7aa;"
            )
            if ad_img_link:
                link = soup.new_tag("a", href=ad_img_link)
                link["style"] = "display: block; text-decoration: none;"
                link.append(img)
                wrapper.append(link)
            else:
                wrapper.append(img)

        if ad_text:
            body = soup.new_tag("div")
            body["style"] = "font-size: 15px; line-height: 1.8; color: #7c2d12; text-align: justify; word-break: break-word;"
            body.string = ad_text
            wrapper.append(body)

        if ad_link_text and ad_link_url:
            cta = soup.new_tag("a", href=ad_link_url)
            cta["style"] = (
                "display: inline-block; margin-top: 10px; color: #9a3412; font-size: 14px; "
                "text-decoration: underline; text-underline-offset: 2px; word-break: break-all;"
            )
            cta.string = ad_link_text
            wrapper.append(cta)

        return wrapper

    @staticmethod
    def _inject_ad_block(soup, container):
        block = WeChatFormatter._build_ad_block(soup)
        if not block:
            return

        position = str(Config.WECHAT_AD_POSITION or "bottom").strip().lower()
        if position not in {"top", "bottom", "both"}:
            position = "bottom"

        if position in {"top", "both"}:
            container.insert(0, block)

        if position in {"bottom", "both"}:
            bottom_block = block if position == "bottom" else WeChatFormatter._build_ad_block(soup)
            if bottom_block:
                container.append(bottom_block)

    @staticmethod
    def _is_inside_ad_block(tag):
        current = tag
        while current is not None:
            if getattr(current, "attrs", None) and current.attrs.get("data-ad-block") == "1":
                return True
            current = getattr(current, "parent", None)
        return False

    @staticmethod
    def deep_optimize_format(html_content):
        from bs4 import BeautifulSoup

        normalized = WeChatFormatter._strip_leading_title_lines(html_content or "")
        normalized = re.sub(r'```(?:html|markdown)?\n?', '', normalized, flags=re.IGNORECASE)
        normalized = normalized.replace('```', '').strip()
        normalized = WeChatFormatter._maybe_markdown_to_html(normalized)

        if not normalized:
            return f'<section style="{WeChatFormatter._WRAPPER_STYLE}"><p style="{WeChatFormatter._TAG_STYLE_MAP["p"]}">（内容为空）</p></section>'

        soup = BeautifulSoup(normalized, "html.parser")
        container = soup.body if soup.body else soup

        # 删除脚本类标签，避免样式污染
        for t in container.find_all(["script", "style", "iframe"]):
            t.decompose()

        # 清理前导标题节点，避免正文重复显示标题
        leading_pattern = re.compile(r'^(【.*?标题.*?】|(?:标题|Title|文章标题)[:：].*|#+\s+.*)$', re.IGNORECASE)
        for node in list(container.children):
            text = getattr(node, "get_text", lambda *args, **kwargs: str(node))(" ", strip=True) if hasattr(node, "get_text") else str(node).strip()
            if not text:
                if hasattr(node, "extract"):
                    node.extract()
                continue
            if leading_pattern.match(text):
                if hasattr(node, "decompose"):
                    node.decompose()
                else:
                    node.extract()
                continue
            break

        # 在样式注入前做一次语义增强，提升“标题感/段落感”
        WeChatFormatter._enhance_semantic_structure(soup, container)
        WeChatFormatter._inject_auto_subheads(soup, container)
        WeChatFormatter._decorate_visual_blocks(soup, container)
        WeChatFormatter._inject_ad_block(soup, container)

        for tag_name, style_text in WeChatFormatter._TAG_STYLE_MAP.items():
            for tag in container.find_all(tag_name):
                if WeChatFormatter._is_inside_ad_block(tag):
                    continue
                WeChatFormatter._append_style(tag, style_text)

        # 移动端图片体验：统一宽度、圆角、居中、自适应
        for img in container.find_all("img"):
            if WeChatFormatter._is_inside_ad_block(img):
                continue
            for attr in ["width", "height", "data-width", "data-height"]:
                if attr in img.attrs:
                    del img.attrs[attr]
            WeChatFormatter._append_style(
                img,
                "display: block; width: 100%; max-width: 100%; height: auto; margin: 12px auto; border-radius: 10px; object-fit: cover;"
            )

        # 表格增加横向滚动容器，避免手机端溢出
        for table in container.find_all("table"):
            parent = table.parent
            parent_style = (parent.get("style", "") if parent else "")
            if parent and parent.name in ["section", "div"] and "overflow-x" in parent_style:
                continue
            wrapper = soup.new_tag("section")
            wrapper["style"] = "width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 12px 0;"
            table.wrap(wrapper)

        # 避免无意义的空段落导致版面稀碎
        for p in container.find_all("p"):
            if not p.get_text(" ", strip=True) and not p.find("img"):
                p.decompose()

        body_html = "".join(str(x) for x in container.contents).strip()
        if not body_html:
            body_html = f'<p style="{WeChatFormatter._TAG_STYLE_MAP["p"]}">（内容为空）</p>'

        return f'<section style="{WeChatFormatter._WRAPPER_STYLE}">\n{body_html}\n</section>'

    @staticmethod
    def optimize_title(title):
        import re
        clean_title = re.sub(r'^【AI改后稿】\s*', '', title)
        clean_title = re.sub(r'^(?:标题|Title|文章标题)[:：]\s*', '', clean_title)
        clean_title = re.sub(r'^#+\s*', '', clean_title)
        clean_title = clean_title.strip()
        # 尽量缩短多余部分（按字节约束，避免微信侧硬截断）
        if len(clean_title.encode('utf-8')) > 64:
            for sep in ['：', ':', '|', '｜']:
                if sep in clean_title:
                    head = clean_title.split(sep)[0].strip()
                    if head and len(head.encode('utf-8')) <= 64:
                        clean_title = head
                        break
        return clean_title
