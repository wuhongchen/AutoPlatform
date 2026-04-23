"""
AI服务
提供AI改写、评分等功能
"""

import json
import time
from typing import Dict, List, Optional
import openai
from app.config import get_settings
from app.core.logger import get_logger
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
        self.logger = get_logger("ai")

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        task_name: str = "llm_call"
    ) -> str:
        """
        统一的 LLM 调用入口
        """
        start_time = time.time()
        self.logger.info(
            f"[{task_name}] LLM request | model={self.config.model} "
            f"temp={temperature} max_tokens={max_tokens} "
            f"sys_len={len(system_prompt)} usr_len={len(user_prompt)}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content
            duration_ms = int((time.time() - start_time) * 1000)

            usage = response.usage
            if usage:
                self.logger.info(
                    f"[{task_name}] LLM success | duration={duration_ms}ms "
                    f"prompt_tokens={usage.prompt_tokens} "
                    f"completion_tokens={usage.completion_tokens} "
                    f"total_tokens={usage.total_tokens}"
                )
            else:
                self.logger.info(
                    f"[{task_name}] LLM success | duration={duration_ms}ms (no usage data)"
                )

            return content

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.error(
                f"[{task_name}] LLM failed | duration={duration_ms}ms "
                f"error={type(e).__name__}: {e}"
            )
            raise

    async def rewrite_article(
        self,
        content: str,
        style_preset: str = "tech_expert",
        reference_articles: Optional[List[Dict]] = None,
        custom_instructions: Optional[str] = None,
        title: Optional[str] = None
    ) -> str:
        """改写文章"""
        preset = StylePresetManager.get_preset(style_preset)
        if not preset:
            self.logger.warning(
                f"[rewrite] Preset '{style_preset}' not found, fallback to tech_expert"
            )
            preset = StylePresetManager.get_preset("tech_expert")

        system_prompt = preset.system_prompt
        if custom_instructions:
            system_prompt += f"\n\n额外要求：\n{custom_instructions}"

        user_prompt = self._build_rewrite_prompt(
            content=content,
            title=title,
            reference_articles=reference_articles,
            style_params=preset.params
        )

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=preset.temperature,
            max_tokens=preset.max_tokens,
            task_name="rewrite"
        )

    def _build_rewrite_prompt(
        self,
        content: str,
        title: Optional[str] = None,
        reference_articles: Optional[List[Dict]] = None,
        style_params: Optional[Dict] = None
    ) -> str:
        """构建改写提示"""
        prompt_parts = []

        if title:
            prompt_parts.append(f"原标题：{title}\n")

        if reference_articles:
            prompt_parts.append("参考文章：")
            for i, ref in enumerate(reference_articles[:3], 1):
                ref_title = ref.get("title", "")
                ref_content = ref.get("content", "")[:500]
                prompt_parts.append(f"\n参考{i}：《{ref_title}》")
                prompt_parts.append(f"内容摘要：{ref_content}...")
            prompt_parts.append("\n请借鉴以上参考文章的写作风格和角度，但保持原创性。\n")

        if style_params:
            if "focus" in style_params:
                prompt_parts.append(f"重点关注：{style_params['focus']}\n")
            if "avoid" in style_params:
                prompt_parts.append(f"避免：{style_params['avoid']}\n")
            if "structure" in style_params:
                prompt_parts.append(f"文章结构：{style_params['structure']}\n")

        prompt_parts.append(f"原文内容：\n\n{content}\n")
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
        similarity_threshold: float = 0.7,
        custom_instructions: Optional[str] = None
    ) -> Dict:
        """带上下文的智能改写"""
        reference_articles = None
        used_references = []

        if inspiration_records:
            reference_articles = []
            for record in inspiration_records:
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

            reference_articles.sort(key=lambda x: x["similarity"], reverse=True)
            reference_articles = reference_articles[:3]

        rewritten = await self.rewrite_article(
            content=content,
            style_preset=style_preset,
            reference_articles=reference_articles,
            custom_instructions=custom_instructions
        )

        return {
            "content": rewritten,
            "style_preset": style_preset,
            "used_references": used_references,
            "reference_count": len(reference_articles) if reference_articles else 0
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """基于关键词重叠的 Jaccard 相似度"""
        import re

        def extract_keywords(text: str) -> set:
            text = re.sub(r'<[^>]+>', '', text)
            words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', text.lower())
            return set(words)

        keywords1 = extract_keywords(text1)
        keywords2 = extract_keywords(text2)

        if not keywords1 or not keywords2:
            return 0.0

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
        system_prompt = "你是一位资深内容编辑，擅长评估文章质量。"
        user_prompt = f"""请对以下文章进行评分和分析：

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

        raw_response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=1000,
            task_name="score"
        )

        try:
            result = json.loads(raw_response)
            return {
                "score": result.get("score", 0),
                "breakdown": result.get("breakdown", {}),
                "reason": result.get("reason", ""),
                "direction": result.get("direction", ""),
                "insight": result.get("insight", ""),
                "suggested_style": result.get("suggested_style", "tech_expert")
            }
        except json.JSONDecodeError:
            self.logger.warning(
                f"[score] JSON parse failed, raw response (first 200 chars): {raw_response[:200]}"
            )
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

        system_prompt = "你是一位标题党大师。"
        user_prompt = f"""请为以下文章生成{count}个吸引人的标题：

{content[:1000]}...

{style_hint}
要求：
1. 标题要有吸引力，能引发好奇
2. 简洁有力，适合公众号
3. 每个标题用数字编号
4. 直接输出标题列表"""

        raw_response = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=500,
            task_name="generate_title"
        )

        titles = raw_response.strip().split("\n")
        return [t.strip().strip("0123456789.- ") for t in titles if t.strip()][:count]

    async def generate_summary(self, content: str, max_length: int = 200) -> str:
        """生成摘要"""
        system_prompt = "你是一位摘要专家。"
        user_prompt = f"""请为以下文章生成一段摘要（{max_length}字以内）：

{content[:2000]}...

要求：
1. 概括核心内容
2. 突出亮点
3. 引发阅读兴趣"""

        return await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=300,
            task_name="generate_summary"
        )

    def list_style_presets(self) -> List[Dict]:
        """列出所有风格预设"""
        return StylePresetManager.list_presets()
