from openai import OpenAI
from config import Config
import time
import re

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
  "industry_context": "该事件相对于行业目前主流方案的竞争力/差异化分析",
  "key_facts": ["核心事实1", "核心数据2"],
  "impact_analysis": ["对开发者/用户的意涵", "对行业格局的影响"],
  "independent_angles": ["第一性原理剖析点", "反直觉逻辑延伸"],
  "narrative_logic": ["逻辑起点", "冲突点", "深度挖掘", "行动建议"],
  "layout_plan": "视觉排版节奏建议"
}}
"""

    # --- 阶段二：完全原创长文写作 (Original Deep Writer) ---
    def _get_generation_prompt(self, analysis, image_count):
        img_hint = "\n".join([f"- [IMAGE_{i}]" for i in range(image_count)]) if image_count else "- 暂无配图"
        return f"""
你是一位获过奖的深度特稿记者，擅长撰写逻辑严密、细节丰满的公众号原创长文。

**本文创作蓝图（来自主编分析）：**
{analysis}

**【写作铁律：拒绝平庸，追求行业纵深】**
1. **深度挖掘**：严禁简单的文字搬运。必须加入行业纵深对比（如：技术路径 A 对比 B 的本质区别）、底层逻辑推演以及未来 3-5 年的趋势预判。
2. **场景驱动**：用具体的“业务场景”或“开发者痛点”带入，确保内容具有实战参考价值。
3. **字数与容量**：目标 1800-2500 字。内容必须扎实，每个章节至少 400 字的逻辑展开，拒绝车轱辘话。
4. **去 AI 套语**：语言要带有个人的主观洞察力，禁用“首先、其次、综上所述”等公文套语。

**视觉排版建议 (借鉴 wenyan-cli 与极简美学)：**
- **导读区**：使用 `<section style="background:#f8f9fa; border-radius:12px; padding:25px; margin:30px 0; border:1px solid #e9ecef;">`，内部文字使用稍微偏灰的颜色。
- **H2 章节**：使用 `<h2 style="font-size:1.4em; color:#1a1a1a; padding-bottom:10px; border-bottom:3px solid #007aff; margin-top:50px; margin-bottom:20px; display:inline-block;">`。
- **引用/点评**：使用 `<blockquote style="color:#555; background:#fffaf0; border-left:6px solid #f39c12; padding:20px; margin:30px 0; border-radius:4px;">`。
- **分割线**：使用 `<hr style="border:0; height:1px; background-image:linear-gradient(to right, rgba(0,0,0,0), rgba(0,0,0,0.2), rgba(0,0,0,0)); margin:50px 0;">`。
- **关键概念**：使用 `<span style="background:linear-gradient(to bottom, transparent 60%%, #ffeb3b 0); font-weight:bold;">` 进行重点标注。
- **总结区**：使用 `<section style="background:linear-gradient(135deg, #2c3e50 0%%, #34495e 100%%); color:#fff; padding:35px; border-radius:15px; margin-top:60px; box-shadow:0 10px 30px rgba(0,0,0,0.15);">`。

**文章组织结构：**
[导读区] -> [引言] -> [H2 实战分析 × 3-4 个] -> [IMAGE_N] -> [精致分割线] -> [总结区]

直接输出微信公众号 HTML，不要 markdown 代码围栏，不要任何解释文字。
"""

    def process(self, url, scraped_data, publisher=None):
        """
        publisher: 可选传入 WeChatPublisher 实例，用于将正文图片上传到微信素材库
        """
        image_urls = scraped_data.get('images', [])
        
        # ── 阶段一：结构分析（只取原文前3000字，避免模型直接复述）──────────
        print(f"🔍 [MP-Deep] 阶段一：主编进行深度结构分析...")
        raw_excerpt = scraped_data['content_raw'][:3000]
        analysis_resp = self.client.chat.completions.create(
            model=Config.VOLC_ARK_MODEL_ID or "doubao-seed-2-0-pro-260215",
            messages=[{"role": "user", "content": self._get_analysis_prompt(raw_excerpt)}]
        )
        analysis_map = analysis_resp.choices[0].message.content
        
        # ── 阶段二：完全原创写作（高 temperature 增加创意，不传原文）─────────
        print(f"🖋️ [MP-Deep] 阶段二：完全原创深度长文写作 (temperature=0.92)...")
        gen_resp = self.client.chat.completions.create(
            model=Config.VOLC_ARK_MODEL_ID or "doubao-seed-2-0-pro-260215",
            messages=[{"role": "user", "content": self._get_generation_prompt(analysis_map, len(image_urls))}],
            max_tokens=4000,
            temperature=0.92     # 高创意度，降低原文复述
        )
        
        content_raw_output = gen_resp.choices[0].message.content
        print(f"   📊 原始生成长度: {len(content_raw_output)} 字符")
        
        # 清理 Markdown 代码块标记
        content_cleaned = re.sub(r'```(?:html)?\n?', '', content_raw_output).replace('```', '').strip()
        
        # ── 阶段三：图片处理（上传至微信素材库，获取合法微信 CDN 链接）───────
        wechat_image_urls = self._upload_images_to_wechat(image_urls, publisher)
        final_image_urls = wechat_image_urls if wechat_image_urls else image_urls
        
        # 替换占位符
        final_content = self._post_process_content(content_cleaned, final_image_urls)
        print(f"   📊 后处理后长度: {len(final_content)} 字符")
        
        title = self._get_pure_title(content_cleaned)
        
        return {
            "full_content": final_content,
            "title": title,
            "analysis": analysis_map
        }

    def _upload_images_to_wechat(self, image_urls, publisher):
        """将原文图片下载后上传至微信素材库，返回微信 CDN URL 列表（合法内链）
        
        过滤规则：
        - 跳过第一张（几乎 100% 是公众号 Logo/Banner）
        - 跳过文件 < 5KB 的小图（章节序号图、分隔符等装饰性图片）
        """
        if not publisher or not image_urls:
            return []
        
        import requests as req
        
        # 确保有 token
        if not publisher.token:
            publisher._get_token()
        if not publisher.token:
            print("   ⚠️ 微信 token 获取失败，图片将使用原文外链")
            return []
        
        upload_api = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={publisher.token}"
        wechat_urls = []
        
        # ── 过滤：跳过第一张 Logo，保留剩余图片（最多取8张）──────────────────
        SKIP_LOGO_COUNT = 1          # 跳过开头的品牌 Logo 数量
        MIN_IMG_SIZE    = 5 * 1024   # 小于 5KB 的装饰性小图直接跳过
        
        candidates = image_urls[SKIP_LOGO_COUNT:]   # 去掉第一张 Logo
        max_imgs = min(len(candidates), 8)
        
        print(f"   📸 过滤后图片 {max_imgs} 张（已跳过首张 Logo），开始上传...")
        uploaded = 0
        for i, src_url in enumerate(candidates[:max_imgs]):
            try:
                # 策略：如果以 feishu:// 开头，使用 feishu_client 下载
                img_content = None
                if str(src_url).startswith("feishu://") and self.feishu:
                    print(f"      [{i+1}] 📥 正在从飞书下载素材...")
                    img_content = self.feishu._download_image(src_url)
                else:
                    r = req.get(src_url, timeout=15, headers={
                        'Referer': 'https://mp.weixin.qq.com',
                        'User-Agent': 'Mozilla/5.0'
                    })
                    if r.status_code == 200:
                        img_content = r.content
                
                if not img_content:
                    print(f"      [{i+1}] ⚠️ 下载失败 (url: {src_url[:30]}...)")
                    continue
                
                # 跳过太小的装饰性图片（序号图、分隔线）
                if len(img_content) < MIN_IMG_SIZE:
                    print(f"      [{i+1}] ⏭  跳过小图 ({len(img_content)//1024}KB < 5KB，装饰性图片)")
                    continue
                
                # 上传到微信素材库
                resp = req.post(
                    upload_api,
                    files={'media': (f'img{i}.jpg', img_content, 'image/jpeg')},
                    timeout=30
                ).json()
                
                if 'url' in resp:
                    wechat_urls.append(resp['url'])
                    uploaded += 1
                    print(f"      [{i+1}] ✅ 上传成功 ({len(r.content)//1024}KB) → 微信 CDN")
                else:
                    errmsg = resp.get('errmsg', str(resp))
                    print(f"      [{i+1}] ⚠️ 上传失败: {errmsg}")
                time.sleep(0.5)
            except Exception as e:
                print(f"      [{i+1}] ⚠️ 异常: {e}")
        
        print(f"   📸 图片处理完成: {uploaded} 张内容图上传至微信 CDN")
        return wechat_urls

    def _post_process_content(self, text, image_urls):
        """将 [IMAGE_N] 替换为 <img> 标签（使用微信 CDN 链接）"""
        processed = text
        
        for i, url in enumerate(image_urls):
            placeholder = f"[IMAGE_{i}]"
            img_html = (
                f'<div style="text-align:center;margin:30px 0;">'
                f'<img src="{url}" style="max-width:100%;border-radius:8px;'
                f'box-shadow:0 4px 20px rgba(0,0,0,0.12);">'
                f'</div>'
            )
            processed = processed.replace(placeholder, img_html)
        
        # 清除所有未被替换的占位符（配图数少于占位符时）
        processed = re.sub(r'\[IMAGE_\d+\]', '', processed)
        return processed

    def _get_pure_title(self, text):
        """提取纯净标题"""
        try:
            patterns = [
                r"【标题：(.*?)】",
                r"标题：(.*?)\n",
                r"标题:(.*?)\n",
                r"## (.*?)\n",
                r"<h1[^>]*>(.*?)</h1>",
                r"<h2[^>]*>(.*?)</h2>"
            ]
            for p in patterns:
                match = re.search(p, text)
                if match:
                    t = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    if t and len(t) > 3:
                        return t
            
            lines = text.split('\n')
            for line in lines[:10]:
                line = line.strip()
                clean = re.sub(r'\[IMAGE_\d+\]', '', line).replace('#', '').strip()
                clean = re.sub(r'<[^>]+>', '', clean).strip()
                if clean and not line.startswith('<') and len(clean) > 5:
                    return clean
                    
            return "深度视角 | 行业精选"
        except Exception:
            return "深度视角 | 行业精选"

    def _extract_title(self, text):
        return self._get_pure_title(text)
