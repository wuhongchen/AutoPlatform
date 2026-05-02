"""
AI服务
提供AI改写、评分等功能
"""

import json
import re
import time
from typing import Dict, List, Optional
import openai
import httpx
from app.config import get_settings
from app.core.logger import get_logger
from app.services.style_presets import StylePresetManager, StylePreset


class AIService:
    """AI服务"""

    LONG_CONTENT_THRESHOLD = 3200
    CHUNK_TARGET_SIZE = 1800
    MAX_REFERENCE_COUNT = 2
    MAX_REFERENCE_CHARS = 240
    MAX_IMAGE_CONTEXTS = 4
    OVERLAP_MIN_CHARS = 400
    OVERLAP_THRESHOLD = 0.22

    def __init__(self):
        settings = get_settings()
        self.config = settings.ai
        timeout = httpx.Timeout(
            connect=min(30, self.config.timeout),
            read=self.config.timeout,
            write=self.config.timeout,
            pool=self.config.timeout,
        )
        self.client = openai.AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.endpoint,
            timeout=timeout
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
        title: Optional[str] = None,
        image_contexts: Optional[List[Dict]] = None,
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

        effective_references = self._compress_references(reference_articles)
        user_prompt = self._build_rewrite_prompt(
            content=content,
            title=title,
            reference_articles=effective_references,
            style_params=preset.params,
            image_contexts=image_contexts,
        )
        max_tokens = self._resolve_max_tokens(
            content=content,
            preset_max_tokens=preset.max_tokens,
            reference_count=len(effective_references),
        )

        rewritten = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=preset.temperature,
            max_tokens=max_tokens,
            task_name="rewrite"
        )

        if self._needs_deeper_rewrite(content, rewritten):
            self.logger.warning(
                f"[rewrite] overlap high -> intensify rewrite | title={title or '-'}"
            )
            intensified = await self._rewrite_to_reduce_overlap(
                original_content=content,
                first_pass_html=rewritten,
                preset=preset,
                title=title,
                custom_instructions=custom_instructions,
                image_contexts=image_contexts,
            )
            if intensified:
                rewritten = intensified

        return rewritten

    def _compress_references(self, reference_articles: Optional[List[Dict]]) -> List[Dict]:
        """压缩参考文章，避免提示词过长导致改写请求过慢。"""
        if not reference_articles:
            return []

        reduced = []
        for ref in reference_articles[:self.MAX_REFERENCE_COUNT]:
            reduced.append({
                "title": ref.get("title", ""),
                "content": (ref.get("content", "") or "")[:self.MAX_REFERENCE_CHARS],
                "similarity": ref.get("similarity"),
            })
        return reduced

    def _resolve_max_tokens(self, content: str, preset_max_tokens: int, reference_count: int = 0) -> int:
        """根据正文长度动态限制输出规模，降低长文超时概率。"""
        max_tokens = preset_max_tokens
        content_len = len(content or "")

        if content_len >= 4500:
            max_tokens = min(max_tokens, 1800)
        elif content_len >= self.LONG_CONTENT_THRESHOLD:
            max_tokens = min(max_tokens, 2200)
        elif content_len >= 1800:
            max_tokens = min(max_tokens, 2600)

        if reference_count:
            max_tokens = min(max_tokens, 2200)

        return max(900, max_tokens)

    def _split_content_chunks(self, content: str, chunk_size: int = None) -> List[str]:
        """按段落/句子拆分长文，便于分段改写。"""
        chunk_size = chunk_size or self.CHUNK_TARGET_SIZE
        cleaned = (content or "").strip()
        if not cleaned:
            return []

        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
        if not paragraphs:
            paragraphs = [cleaned]

        segments: List[str] = []
        for paragraph in paragraphs:
            if len(paragraph) <= chunk_size:
                segments.append(paragraph)
                continue

            sentences = [
                piece.strip()
                for piece in re.split(r"(?<=[。！？!?；;])", paragraph)
                if piece.strip()
            ]
            if not sentences:
                sentences = [paragraph]

            buffer = ""
            for sentence in sentences:
                if buffer and len(buffer) + len(sentence) > chunk_size:
                    segments.append(buffer.strip())
                    buffer = sentence
                else:
                    buffer = f"{buffer}{sentence}"
            if buffer.strip():
                segments.append(buffer.strip())

        chunks: List[str] = []
        current = ""
        for segment in segments:
            candidate = f"{current}\n\n{segment}".strip() if current else segment
            if current and len(candidate) > chunk_size:
                chunks.append(current.strip())
                current = segment
            else:
                current = candidate
        if current.strip():
            chunks.append(current.strip())

        return chunks

    async def _rewrite_in_chunks(
        self,
        content: str,
        style_preset: str,
        reference_articles: Optional[List[Dict]] = None,
        custom_instructions: Optional[str] = None,
        title: Optional[str] = None,
        image_contexts: Optional[List[Dict]] = None,
    ) -> str:
        """长文分段改写，避免单次请求超时。"""
        chunks = self._split_content_chunks(content)
        if len(chunks) <= 1:
            raise openai.APITimeoutError(request=httpx.Request("POST", self.config.endpoint))

        self.logger.warning(
            f"[rewrite] timeout fallback -> chunked rewrite | chunks={len(chunks)} title={title or '-'}"
        )

        chunk_outputs: List[str] = []
        compressed_refs = self._compress_references(reference_articles)
        for index, chunk in enumerate(chunks, 1):
            chunk_instructions = [
                custom_instructions.strip() if custom_instructions else "",
                f"当前为长文分段改写，第{index}/{len(chunks)}部分。",
                "只改写这一部分内容，不要重复整篇文章的开场或总结。",
                "不要输出“第X部分”字样，直接给自然正文。",
            ]
            chunk_output = await self.rewrite_article(
                content=chunk,
                style_preset=style_preset,
                reference_articles=compressed_refs if index == 1 else None,
                custom_instructions="\n".join(item for item in chunk_instructions if item),
                title=title if index == 1 else None,
                image_contexts=image_contexts if index == 1 else None,
            )
            chunk_outputs.append(chunk_output.strip())

        return "\n".join(item for item in chunk_outputs if item)

    def _build_rewrite_prompt(
        self,
        content: str,
        title: Optional[str] = None,
        reference_articles: Optional[List[Dict]] = None,
        style_params: Optional[Dict] = None,
        image_contexts: Optional[List[Dict]] = None,
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

        if image_contexts:
            prompt_parts.append("图片线索（仅在相关时自然融入叙述，不要编造图片里没有的信息）：")
            for item in image_contexts[:self.MAX_IMAGE_CONTEXTS]:
                index = item.get("index", "")
                alt = (item.get("alt") or "").strip()
                context = (item.get("context") or "").strip()
                bits = [part for part in [f"图片{index}", alt, context] if part]
                if bits:
                    prompt_parts.append(f"- {' | '.join(bits)}")
            prompt_parts.append("")

        prompt_parts.append(f"原文内容：\n\n{content}\n")
        prompt_parts.append("""
改写要求：
1. 不要直接复制原文句子，要重构开头、段落顺序和句式
2. 可以补充背景知识和解释，但不要偏离原文主题
3. 保持核心事实、数据、时间线准确
4. 输出HTML格式，使用h2/h3标签作为标题
5. 段落不要太长，适合手机阅读
6. 适当使用加粗、列表等排版元素
7. 除专有名词、机构名、产品名外，避免连续复用原文措辞
8. 如果图片线索和正文相关，可以自然写出“图中场景反映了什么”，但不要凭空编造图片细节
""")

        return "\n".join(prompt_parts)

    async def rewrite_with_context(
        self,
        content: str,
        style_preset: str = "tech_expert",
        inspiration_records: Optional[List[Dict]] = None,
        similarity_threshold: float = 0.7,
        custom_instructions: Optional[str] = None,
        title: Optional[str] = None,
        image_contexts: Optional[List[Dict]] = None,
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

        try:
            rewritten = await self.rewrite_article(
                content=content,
                style_preset=style_preset,
                reference_articles=reference_articles,
                custom_instructions=custom_instructions,
                title=title,
                image_contexts=image_contexts,
            )
        except openai.APITimeoutError:
            content_len = len(content or "")
            if content_len >= self.LONG_CONTENT_THRESHOLD:
                rewritten = await self._rewrite_in_chunks(
                    content=content,
                    style_preset=style_preset,
                    reference_articles=reference_articles,
                    custom_instructions=custom_instructions,
                    title=title,
                    image_contexts=image_contexts,
                )
                if reference_articles:
                    used_references = [ref.get("title", "") for ref in reference_articles[:self.MAX_REFERENCE_COUNT]]
            elif reference_articles:
                self.logger.warning("[rewrite] timeout fallback -> retry without references")
                rewritten = await self.rewrite_article(
                    content=content,
                    style_preset=style_preset,
                    reference_articles=None,
                    custom_instructions=custom_instructions,
                    title=title,
                    image_contexts=image_contexts,
                )
                used_references = []
            else:
                raise

        return {
            "content": rewritten,
            "style_preset": style_preset,
            "used_references": used_references,
            "reference_count": len(reference_articles) if reference_articles else 0
        }

    def _normalize_overlap_text(self, text: str) -> str:
        plain = re.sub(r"<[^>]+>", " ", text or "")
        plain = re.sub(r"\s+", "", plain)
        return plain.lower()

    def _estimate_overlap_ratio(self, original: str, rewritten: str, shingle_size: int = 12) -> float:
        source = self._normalize_overlap_text(original)
        candidate = self._normalize_overlap_text(rewritten)

        if len(source) < max(self.OVERLAP_MIN_CHARS, shingle_size) or len(candidate) < max(self.OVERLAP_MIN_CHARS, shingle_size):
            return 0.0

        def shingles(text: str) -> set:
            return {
                text[index:index + shingle_size]
                for index in range(0, len(text) - shingle_size + 1)
            }

        source_shingles = shingles(source)
        candidate_shingles = shingles(candidate)
        if not source_shingles or not candidate_shingles:
            return 0.0

        overlap = len(source_shingles & candidate_shingles)
        return overlap / max(1, len(candidate_shingles))

    def _needs_deeper_rewrite(self, original: str, rewritten: str) -> bool:
        ratio = self._estimate_overlap_ratio(original, rewritten)
        if ratio >= self.OVERLAP_THRESHOLD:
            self.logger.warning(f"[rewrite] overlap ratio high: {ratio:.3f}")
            return True
        return False

    async def _rewrite_to_reduce_overlap(
        self,
        original_content: str,
        first_pass_html: str,
        preset: StylePreset,
        title: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        image_contexts: Optional[List[Dict]] = None,
    ) -> str:
        system_prompt = (
            f"{preset.system_prompt}\n\n"
            "你正在执行二次深改。目标不是润色初稿，而是在不改变核心事实的前提下，"
            "彻底重构表达方式、段落组织和叙述节奏，显著降低与原文的字面重合。"
        )
        if custom_instructions:
            system_prompt += f"\n\n额外要求：\n{custom_instructions}"

        prompt_parts = []
        if title:
            prompt_parts.append(f"原标题：{title}")
        if image_contexts:
            prompt_parts.append("图片线索：")
            for item in image_contexts[:self.MAX_IMAGE_CONTEXTS]:
                bits = [part for part in [f"图片{item.get('index', '')}", item.get("alt", ""), item.get("context", "")] if part]
                if bits:
                    prompt_parts.append(f"- {' | '.join(bits)}")
        prompt_parts.append("原文：")
        prompt_parts.append(original_content)
        prompt_parts.append("\n初稿：")
        prompt_parts.append(first_pass_html)
        prompt_parts.append("""
请重新输出一版 HTML 成稿，并严格遵守：
1. 保留事实、数据、时间线和论点，不要遗漏关键信息
2. 改写开头，不要沿用原文或初稿的起手方式
3. 重新组织段落顺序与句式，避免连续复用原文措辞
4. 除专有名词外，尽量不用和原文相同的长短语
5. 图片线索仅作为辅助理解，不要编造图片不存在的细节
6. 输出最终成稿，不要解释过程
""")
        try:
            return await self._call_llm(
                system_prompt=system_prompt,
                user_prompt="\n".join(prompt_parts),
                temperature=min(0.9, preset.temperature + 0.05),
                max_tokens=max(900, preset.max_tokens),
                task_name="rewrite_overlap_retry",
            )
        except Exception as exc:
            self.logger.warning(f"[rewrite] overlap retry failed, keep first pass: {exc}")
            return first_pass_html

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
