import json
import os
from openai import OpenAI
from config import Config

class MPContentProcessor:
    """
    微信公众号精品内容处理器
    基于 AI writer v2.2 核心逻辑重构的 Python 版本
    核心目标：高人感、去 AI 味、爆款模式拆解
    """
    
    # --- v3.0 公众号高级去 AI 词汇库 (Media-Expert Version) ---
    WORD_VARIATIONS = {
        "用": ["开始用", "去用", "试着用", "将其引入", "落到了...上"],
        "买": ["入手了", "拿下了", "重金砸向", "下单买了", "将其纳入囊中"],
        "做": ["去做", "着手实施", "开始倒腾", "开始做", "切入"],
        "发现": ["注意到", "意外发现", "后来才知道", "深究后发觉"],
        "感觉": ["觉得", "个人感受是", "体感上", "给我的感觉", "作为从业者的直观感受"],
        "因为": ["归根结底是因为", "主要是", "背后的推手是", "要说为啥"],
        "但是": ["话说回来", "可是", "只是", "但这并不代表", "倒是"],
        "通过": ["凭借", "依托", "靠着", "借助", "直接用"]
    }

    # 用于润色的过渡短语，打破 AI 的“首先、其次、综上所述”
    HUMAN_TRANSITIONS = ["其实说白了", "有一个很有意思的现象", "我们可以换个角度看", "这也解释了为什么", "一个扎心的事实是"]
    COLLOQUIAL_FILLERS = ["真的", "确实", "简直", "居然", "毫不夸张地说", "讲真", "不得不说"]

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_ENDPOINT.replace("/chat/completions", "")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    # --- 阶段一：分析专家 (Reverse Engineering) ---
    def _get_analysis_prompt(self, content):
        return f"""
你是一位顶尖的微信公众号内容策略分析师。请针对提供的爆款文章进行深度拆解，并输出《创作公式报告》。

**待分析内容:**
{content}

**请严格输出 JSON 结构:**
{{
  "core_insight": "一句话概括核心洞察（拒绝标题党，要硬核）",
  "technical_logic": "梳理其背后的第一性原理或商业运转逻辑",
  "industry_positioning": "该事件在行业坐标系中的真实地位分析",
  "narrative_arc": "建议的内容铺陈路径（起、承、转、合的具体建议）",
  "independent_angle": "原文未触及的批判性或前瞻性视角"
}}
"""

    # --- 阶段二：创作专家 (De-AI Writer) ---
    def _get_generation_prompt(self, formula, material):
        return f"""
你是一位深耕科技/商业领域的深度观察家，拥有极强的“文字生命力”和“去 AI 感”。

**创作蓝图 (基于深度解构分析):**
{formula}

**用户原始素材:**
{material}

**【护城河级去 AI 指令 v3.0 - 公众号深度版】**
1. **词汇降维与升华：** 动词要带有“汗水感”。禁止平铺直叙。
   - 替换示例：使用 {self.WORD_VARIATIONS.get('感觉')} 等带体感的短语。
2. **逻辑过渡模块：** 严禁用使用“首先/此外/综上所述”。
   - 必须在段落转折处自然嵌入：{self.HUMAN_TRANSITIONS} 等短语。
3. **结构化叙事：**
   - **导读区**：使用风格化的 `<div class="guide-box" style="background:#f4f4f4;border-left:4px solid #333;padding:20px;margin-bottom:30px;">`。
   - **H2 章节**：深度展开，每个章节不少于 500 字，禁止车轱辘话。
   - **总结区**：高度浓缩主观洞察力。
4. **WeChat-Format 排版注入：**
   - 强调句：`<span style="color:#e67e22;font-weight:bold;">`
   - 图片占位：在 H2 下方留出 [IMAGE_N] 位置。

**输出内容要求：**
- 1个极具张力的专业标题 (避免廉价的震惊体)
- 1800-2500 字的长文正文 (HTML 格式)
- 3:4 比例 AI 生图提示词 (放在末尾)
"""

    def process(self, url, scraped_data):
        print(f"🕵️ [MP-Pro] 阶段一：分析专家正在逆向解构爆款基因...")
        
        # 1. 分析模式 (Reverse Engineering)
        analysis_resp = self.client.chat.completions.create(
            model=Config.VOLC_ARK_MODEL_ID or "gpt-3.5-turbo",
            messages=[{"role": "user", "content": self._get_analysis_prompt(scraped_data['content_raw'])}]
        )
        formula = analysis_resp.choices[0].message.content
        
        print(f"🎨 [MP-Pro] 阶段二：创作专家正在应用 De-AI 策略生成...")
        
        # 2. 拟人化重写 (Dual System + De-AI)
        gen_resp = self.client.chat.completions.create(
            model=Config.VOLC_ARK_MODEL_ID or "gpt-3.5-turbo",
            messages=[{"role": "user", "content": self._get_generation_prompt(formula, scraped_data['content_raw'])}],
            temperature=0.9
        )
        
        content = gen_resp.choices[0].message.content
        return {
            "full_content": content,
            "title": self._extract_title(content),
            "analysis": formula
        }

    def _extract_title(self, text):
        try:
            # 尝试提取标题
            import re
            match = re.search(r'<(h1|h2)[^>]*>(.*?)</\1>', text)
            if match:
                return re.sub(r'<[^>]+>', '', match.group(2)).strip()
            
            lines = text.split('\n')
            for line in lines[:5]:
                clean = re.sub(r'<[^>]+>', '', line).strip()
                if clean and len(clean) > 5:
                    return clean
            return "深度观察 | 行业精选"
        except:
            return "深度观察 | 行业精选"
