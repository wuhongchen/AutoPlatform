"""
AI服务
提供AI改写、评分等功能
"""

import json
import os
from typing import Dict, List, Optional, AsyncGenerator
import openai
from app.config import get_settings
from app.services.style_presets import StylePresetManager, StylePreset


class AIService:
    """AI服务"""
    
    def __init__(self):
        settings = get_settings()
        self.config = settings.ai
        self.client = openai.AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.endpoint,
            timeout=self.config.timeout
        )
    
    async def rewrite_article(
        self,
        content: str,
        style_preset: str = "tech_expert",
        reference_articles: Optional[List[Dict]] = None,
        custom_instructions: Optional[str] = None,
        title: Optional[str] = None
    ) -> str:
        """
        改写文章
        
        Args:
            content: 原始内容
            style_preset: 风格预设ID
            reference_articles: 参考文章列表，每篇包含title和content
            custom_instructions: 额外定制指令
            title: 原标题（用于保持主题一致）
        """
        # 获取风格预设
        preset = StylePresetManager.get_preset(style_preset)
        if not preset:
            preset = StylePresetManager.get_preset("tech_expert")
        
        # 构建系统提示
        system_prompt = preset.system_prompt
        
        # 添加定制指令
        if custom_instructions:
            system_prompt += f"\n\n额外要求：\n{custom_instructions}"
        
        # 构建用户提示
        user_prompt = self._build_rewrite_prompt(
            content=content,
            title=title,
            reference_articles=reference_articles,
            style_params=preset.params
        )
        
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=preset.temperature,
            max_tokens=preset.max_tokens
        )
        
        return response.choices[0].message.content
    
    def _build_rewrite_prompt(
        self,
        content: str,
        title: Optional[str] = None,
        reference_articles: Optional[List[Dict]] = None,
        style_params: Optional[Dict] = None
    ) -> str:
        """构建改写提示"""
        prompt_parts = []
        
        # 原标题
        if title:
            prompt_parts.append(f"原标题：{title}\n")
        
        # 参考资料
        if reference_articles:
            prompt_parts.append("参考文章：")
            for i, ref in enumerate(reference_articles[:3], 1):  # 最多3篇参考
                ref_title = ref.get("title", "")
                ref_content = ref.get("content", "")[:500]  # 截取前500字
                prompt_parts.append(f"\n参考{i}：《{ref_title}》")
                prompt_parts.append(f"内容摘要：{ref_content}...")
            prompt_parts.append("\n请借鉴以上参考文章的写作风格和角度，但保持原创性。\n")
        
        # 风格参数
        if style_params:
            if "focus" in style_params:
                prompt_parts.append(f"重点关注：{style_params['focus']}\n")
            if "avoid" in style_params:
                prompt_parts.append(f"避免：{style_params['avoid']}\n")
            if "structure" in style_params:
                prompt_parts.append(f"文章结构：{style_params['structure']}\n")
        
        # 原文
        prompt_parts.append(f"原文内容：\n\n{content}\n")
        
        # 输出要求
        prompt_parts.append("""
改写要求：
1. 不要直接复制原文，用自己的语言重新表达
2. 可以补充背景知识和解释
3. 保持核心信息准确
4. 输出HTML格式，使用h2/h3标签作为标题
5. 段落不要太长，适合手机阅读
6. 适当使用加粗、列表等排版元素
""")
        
        return "\n".join(prompt_parts)
    
    async def rewrite_with_context(
        self,
        content: str,
        style_preset: str = "tech_expert",
        inspiration_records: Optional[List[Dict]] = None,
        similarity_threshold: float = 0.7
    ) -> Dict:
        """
        带上下文的智能改写
        
        Args:
            content: 原始内容
            style_preset: 风格预设
            inspiration_records: 灵感库记录，用于寻找相关参考
            similarity_threshold: 相似度阈值，只参考相似度高于此值的文章
            
        Returns:
            包含改写结果和参考信息
        """
        reference_articles = None
        used_references = []
        
        # 如果有灵感库记录，筛选相关的作为参考
        if inspiration_records:
            reference_articles = []
            for record in inspiration_records:
                # 这里可以添加更复杂的相似度计算
                # 简单实现：基于标题和内容的文本匹配
                similarity = self._calculate_similarity(
                    content, 
                    record.get("content", "")
                )
                if similarity >= similarity_threshold:
                    reference_articles.append({
                        "title": record.get("title", ""),
                        "content": record.get("content", "")[:1000],
                        "similarity": similarity
                    })
                    used_references.append(record.get("title", ""))
            
            # 按相似度排序，取前3
            reference_articles.sort(key=lambda x: x["similarity"], reverse=True)
            reference_articles = reference_articles[:3]
        
        # 执行改写
        rewritten = await self.rewrite_article(
            content=content,
            style_preset=style_preset,
            reference_articles=reference_articles
        )
        
        return {
            "content": rewritten,
            "style_preset": style_preset,
            "used_references": used_references,
            "reference_count": len(reference_articles) if reference_articles else 0
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度
        简单实现：基于关键词重叠
        """
        # 提取关键词（简单实现：取长度大于2的词）
        import re
        
        def extract_keywords(text: str) -> set:
            # 移除HTML标签
            text = re.sub(r'<[^>]+>', '', text)
            # 提取中文字符和英文单词
            words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', text.lower())
            return set(words)
        
        keywords1 = extract_keywords(text1)
        keywords2 = extract_keywords(text2)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # 计算Jaccard相似度
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        
        return intersection / union if union > 0 else 0.0
    
    async def score_article(
        self,
        title: str,
        content: str,
        direction: str = ""
    ) -> Dict:
        """AI评分"""
        prompt = f"""请对以下文章进行评分和分析：

标题：{title}
内容：{content[:2000]}...

{f'内容方向：{direction}' if direction else ''}

请从以下维度评分（0-100分）：
1. 爆款潜力 - 成为爆文的可能性
2. 内容质量 - 信息价值和准确性
3. 传播价值 - 值得分享的程度

请以JSON格式返回：
{{
    "score": 总分,
    "breakdown": {{
        "potential": 爆款潜力分数,
        "quality": 内容质量分数,
        "shareability": 传播价值分数
    }},
    "reason": "推荐理由，50字以内",
    "direction": "建议改写方向",
    "insight": "核心洞察",
    "suggested_style": "建议的改写风格"
}}"""
        
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "你是一位资深内容编辑，擅长评估文章质量。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # 解析JSON响应
        try:
            result = json.loads(response.choices[0].message.content)
            return {
                "score": result.get("score", 0),
                "breakdown": result.get("breakdown", {}),
                "reason": result.get("reason", ""),
                "direction": result.get("direction", ""),
                "insight": result.get("insight", ""),
                "suggested_style": result.get("suggested_style", "tech_expert")
            }
        except json.JSONDecodeError:
            return {
                "score": 70,
                "breakdown": {},
                "reason": "内容有价值",
                "direction": "保持原风格",
                "insight": "值得改写",
                "suggested_style": "tech_expert"
            }
    
    async def generate_title(self, content: str, count: int = 3, style: str = "") -> List[str]:
        """生成标题"""
        style_hint = f"风格要求：{style}\n" if style else ""
        
        prompt = f"""请为以下文章生成{count}个吸引人的标题：

{content[:1000]}...

{style_hint}
要求：
1. 标题要有吸引力，能引发好奇
2. 简洁有力，适合公众号
3. 每个标题用数字编号
4. 直接输出标题列表"""
        
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "你是一位标题党大师。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )
        
        titles = response.choices[0].message.content.strip().split("\n")
        return [t.strip().strip("0123456789.- ") for t in titles if t.strip()][:count]
    
    async def generate_summary(self, content: str, max_length: int = 200) -> str:
        """生成摘要"""
        prompt = f"""请为以下文章生成一段摘要（{max_length}字以内）：

{content[:2000]}...

要求：
1. 概括核心内容
2. 突出亮点
3. 引发阅读兴趣"""
        
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "你是一位摘要专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
    
    def list_style_presets(self) -> List[Dict]:
        """列出所有风格预设"""
        return StylePresetManager.list_presets()
