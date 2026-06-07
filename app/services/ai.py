"""
AI服务
提供AI改写、评分等功能
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Optional
import openai
import httpx
from bs4 import BeautifulSoup
from volcenginesdkarkruntime import Ark
from app.config import get_settings
from app.core.logger import get_logger
from app.services.style_presets import StylePresetManager, StylePreset


class AIService:
    """AI服务"""

    LONG_CONTENT_THRESHOLD = 3200
    CHUNK_TARGET_SIZE = 1800
    MAX_REFERENCE_COUNT = 2
    MAX_REFERENCE_CHARS = 240
    MAX_REFERENCE_SIMILARITY = 0.88
    MAX_IMAGE_CONTEXTS = 4
    OVERLAP_MIN_CHARS = 400
    OVERLAP_THRESHOLD = 0.14

    PROMOTION_LINE_PATTERNS = (
        r"扫码|二维码|长按识别|加(我)?微信|添加微信|进群|读者群|交流群",
        r"关注.{0,12}公众号|公众号.{0,12}关注|点击.{0,8}(蓝字|关注|原文)|阅读原文",
        r"点个(赞|在看)|点赞|在看|转发|分享给|星标|置顶|设为星标",
        r"商务合作|广告合作|赞赏|打赏|福利|优惠|下单|购买|课程|训练营|私信|后台回复",
    )
    PROMOTION_IMAGE_PATTERNS = (
        r"qr|qrcode|二维码|扫码|关注|公众号|赞赏|打赏|广告|banner|ad_",
    )
    AI_STYLE_PHRASES = (
        "不是简单的", "而是一个", "本质上", "核心在于", "可以说",
        "值得注意的是", "从某种程度上", "我们可以看到", "不难发现",
        "赋能", "闭环", "抓手", "底层逻辑", "价值锚点", "生态化", "范式",
    )

    def __init__(self):
        settings = get_settings()
        self.config = settings.ai
        self.logger = get_logger("ai")
        self._model_config = self._load_model_config()
        self._rebuild_clients()

    def _load_model_config(self) -> Optional[Dict]:
        """从数据库加载当前默认模型配置，失败则回退 .env"""
        try:
            from app.services.storage import StorageService
            db_config = StorageService().get_default_ai_config()
            if db_config and db_config.get("api_key"):
                self.logger.info(
                    f"[ai] loaded model from db: {db_config['name']} ({db_config['model']})"
                )
                return db_config
        except Exception as e:
            self.logger.warning(f"[ai] failed to load db model config: {e}")
        return None

    def _rebuild_clients(self):
        """基于当前配置重建 API 客户端"""
        if self._model_config:
            api_key = self._model_config["api_key"]
            endpoint = self._model_config.get("endpoint", "")
            model = self._model_config.get("model", "")
            timeout_val = self._model_config.get("timeout", self.config.timeout)
        else:
            api_key = self.config.api_key
            endpoint = self.config.endpoint
            model = self.config.model
            timeout_val = self.config.timeout

        timeout = httpx.Timeout(
            connect=min(30, timeout_val),
            read=timeout_val,
            write=timeout_val,
            pool=timeout_val,
        )
        self._current_model = model
        self._use_ark_responses = self._should_use_ark_responses_db(endpoint)
        self.ark_client = None
        if self._use_ark_responses:
            self.ark_client = Ark(
                api_key=api_key,
                base_url=endpoint,
                timeout=timeout,
            )
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=endpoint,
            timeout=timeout
        )

    def _should_use_ark_responses_db(self, endpoint: str = "") -> bool:
        """判断是否使用 Ark Responses API"""
        ep = (endpoint or self.config.endpoint or "").strip().lower()
        return "volces.com/api/v3" in ep

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
            f"[{task_name}] LLM request | model={self._current_model} "
            f"temp={temperature} max_tokens={max_tokens} "
            f"sys_len={len(system_prompt)} usr_len={len(user_prompt)}"
        )

        try:
            if self._use_ark_responses:
                response = await asyncio.to_thread(
                    self.ark_client.responses.create,
                    model=self._current_model,
                    instructions=system_prompt,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": user_prompt,
                                }
                            ],
                        }
                    ],
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    thinking={"type": "disabled"},
                    store=False,
                )
                content = self._extract_ark_response_text(response)
            else:
                response = await self.client.chat.completions.create(
                    model=self._current_model,
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
                    f"prompt_tokens={self._get_usage_value(usage, 'prompt_tokens', 'input_tokens')} "
                    f"completion_tokens={self._get_usage_value(usage, 'completion_tokens', 'output_tokens')} "
                    f"total_tokens={self._get_usage_value(usage, 'total_tokens')}"
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
            friendly_error = self._normalize_provider_error(e)
            if friendly_error:
                raise RuntimeError(friendly_error) from e
            raise

    def _extract_ark_response_text(self, response) -> str:
        """从 Ark Responses API 响应中提取 assistant 输出文本。"""
        if getattr(response, "error", None):
            raise RuntimeError(str(response.error))

        text_parts: List[str] = []
        for item in getattr(response, "output", None) or []:
            contents = self._get_obj_value(item, "content") or []
            for content_item in contents:
                item_type = self._get_obj_value(content_item, "type")
                item_text = self._get_obj_value(content_item, "text")
                if item_type == "output_text" and item_text:
                    text_parts.append(item_text)

        content = "\n".join(part.strip() for part in text_parts if part and part.strip()).strip()
        if content:
            status = getattr(response, "status", "")
            if status and status != "completed":
                self.logger.warning(
                    f"[llm_call] Ark response status={status}, using partial text"
                )
            return content

        status = getattr(response, "status", "")
        incomplete = getattr(response, "incomplete_details", None)
        raise RuntimeError(f"Ark Responses API 未返回文本内容。status={status}, incomplete={incomplete}")

    def _get_obj_value(self, obj, key: str):
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    def _get_usage_value(self, usage, *keys: str) -> int:
        for key in keys:
            value = self._get_obj_value(usage, key)
            if value is not None:
                return value
        return 0

    def _normalize_provider_error(self, error: Exception) -> str:
        """将常见供应商鉴权/订阅错误转成可操作提示。"""
        message = str(error)
        lowered = message.lower()
        if "invalidsubscription" in lowered or "codingplan" in lowered:
            return (
                "AI 模型调用失败：当前火山 Ark CodingPlan 订阅无效或已过期。"
                "请在火山引擎控制台续费/开通 CodingPlan，或把 .env 中的 "
                "AI_ENDPOINT、AI_MODEL、AI_API_KEY 切换为有效的其他模型服务。"
            )
        if "invalid authentication" in lowered or "invalid_authentication_error" in lowered:
            return "AI 模型调用失败：API Key 无效或不属于当前模型服务，请检查 .env 中的 AI_API_KEY 和 AI_ENDPOINT。"
        if "only available for coding agents" in lowered or "access_terminated_error" in lowered:
            return (
                "AI 模型调用失败：当前 Kimi Key 只能用于 Kimi Coding Agent，"
                "不能用于 AutoPlatform 的通用内容改写接口。请换用 Kimi Open Platform / Moonshot 的通用 API Key。"
            )
        return ""

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
        preset = self._get_style_preset(style_preset)
        if not preset:
            self.logger.warning(
                f"[rewrite] Preset '{style_preset}' not found, fallback to tech_expert"
            )
            preset = self._get_style_preset("tech_expert")

        system_prompt = self._build_rewrite_system_prompt(preset)
        if custom_instructions:
            system_prompt += f"\n\n额外要求：\n{custom_instructions}"

        effective_references = self._compress_references(reference_articles)
        rewrite_source = self._prepare_source_for_rewrite(content)
        user_prompt = self._build_rewrite_prompt(
            content=rewrite_source,
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
        rewritten = self._sanitize_rewritten_output(rewritten)

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
                rewritten = self._sanitize_rewritten_output(intensified)

        return rewritten

    def _build_rewrite_system_prompt(self, preset: StylePreset) -> str:
        """叠加统一编辑约束，避免单个风格预设把改写做成轻润色。"""
        ai_phrases = "、".join(self.AI_STYLE_PHRASES)
        return f"""{preset.system_prompt}

统一编辑红线：
1. 你不是润色助手，而是公众号选题编辑。先抽取事实，再按新账号视角重写成一篇新稿。
2. 保留事实、数据、人物、产品名和时间线，但不要保留原文叙事身份、口头禅、段落顺序、营销话术。
3. 输出必须像真实中文编辑写的自然稿，不要有 AI 总结腔、模板腔、口号腔。
4. 严禁使用或高频堆叠这些 AI 味表达：{ai_phrases}。
5. 默认使用第三方编辑视角，不继承原作者第一人称。原文中的“我/我们/我的读者/之前推过/我自己用下来”等自述，要改为客观描述或直接删除。
6. 删除软推广和导流内容，包括关注公众号、扫码、加微信、进群、课程/优惠/福利、点赞在看、阅读原文、商务合作、赞赏二维码等。
7. 只输出可直接进入排版模板的 HTML 片段，不要输出 Markdown、代码围栏、解释说明或“以下是改写稿”。"""

    def _get_style_preset(self, preset_id: str) -> Optional[StylePreset]:
        """同时支持内置风格与后台创建的自定义风格。"""
        preset = StylePresetManager.get_preset(preset_id)
        if preset:
            return preset

        try:
            from app.services.storage import StorageService

            stored = StorageService().get_style_preset(preset_id)
            if not stored or not stored.is_active:
                return None
            tone = stored.tone.value if hasattr(stored.tone, "value") else stored.tone
            style = stored.style.value if hasattr(stored.style, "value") else stored.style
            return StylePreset(
                id=stored.id,
                name=stored.name,
                description=stored.description,
                system_prompt=stored.system_prompt,
                tone=tone,
                style=style,
                temperature=stored.temperature,
                max_tokens=stored.max_tokens,
                params=stored.params or {},
            )
        except Exception as exc:
            self.logger.warning(f"[rewrite] failed to load custom style '{preset_id}': {exc}")
            return None

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
            max_tokens = min(max_tokens, 3200)
        elif content_len >= self.LONG_CONTENT_THRESHOLD:
            max_tokens = min(max_tokens, 3000)
        elif content_len >= 1800:
            max_tokens = min(max_tokens, 2600)

        if reference_count:
            max_tokens = min(max_tokens, 2800)

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
            prompt_parts.append("参考素材（只借鉴选题角度和信息补充，不复用句子、段落结构或作者身份）：")
            for i, ref in enumerate(reference_articles[:3], 1):
                ref_title = ref.get("title", "")
                ref_content = ref.get("content", "")[:500]
                prompt_parts.append(f"\n参考{i}：《{ref_title}》")
                prompt_parts.append(f"内容摘要：{ref_content}...")
            prompt_parts.append("\n如果参考素材与原文高度相似，主动忽略它，不要让它增加原文重合度。\n")

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

        prompt_parts.append(f"待改写素材（已初步剔除推广噪声；只把它当事实材料，不要沿用原文表达）：\n\n{content}\n")
        prompt_parts.append("""
改写要求：
1. 先在心里完成“事实提取 -> 结构重组 -> 重新表达”，最终只输出成稿。
2. 开头必须重写，不得沿用原文第一段的切入方式、作者经历、周末/额度/之前推过等自述。
3. 至少重排 60% 的段落顺序；小标题必须重新命名，不能照搬原文标题。
4. 除专有名词、产品名、固定术语外，不要出现连续 10 个中文字符与原文完全相同。
5. 删除原文里的软推广、关注引导、二维码提示、课程/福利/购买导流、点赞在看、阅读原文、商务合作。
6. 使用中性或账号化编辑视角，不要出现“我”“我们这个号”“我的读者”“我之前写过”等源作者第一人称。
7. 可以补充必要背景和解释，但不要编造事实、数据、截图细节和不存在的结论。
8. 语言要像真实编辑自然写稿：具体、克制、有判断；不要使用 AI 腔套话、宏大空词和过度总结。
9. 输出 HTML 片段，只允许使用 h2、h3、p、strong、em、ul、ol、li、blockquote、figure、img、figcaption。
10. 不要使用 Markdown 符号，不要输出 ```，不要输出 html/body/style/script，不要把 ul/ol 嵌进 p 标签。
11. 如果图片线索和正文相关，可以自然说明图片承载的信息；不知道图片内容时只写“配图/截图位置”，不要编造视觉细节。
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
                if similarity >= self.MAX_REFERENCE_SIMILARITY:
                    self.logger.info(
                        f"[rewrite] skip near-duplicate reference: {record.get('title', '')} similarity={similarity:.3f}"
                    )
                    continue
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
            f"{self._build_rewrite_system_prompt(preset)}\n\n"
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
5. 删除第一人称自述、关注引导、扫码、软广、课程/福利/购买导流、点赞在看、阅读原文
6. 去掉 AI 腔套话，使用真实编辑口吻
7. 图片线索仅作为辅助理解，不要编造图片不存在的细节
8. 输出最终 HTML 片段，不要解释过程，不要 Markdown
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

    def _prepare_source_for_rewrite(self, content: str) -> str:
        """改写前剔除明显推广/导流噪声，降低模型复读这些内容的概率。"""
        raw = (content or "").strip()
        if not raw:
            return ""

        lines = [line.strip() for line in re.split(r"[\r\n]+", raw)]
        kept = [
            line
            for line in lines
            if line and not self._is_promotional_text(line)
        ]
        cleaned = "\n".join(kept).strip()
        if len(cleaned) < max(20, len(raw) * 0.2):
            return raw
        return cleaned

    def _sanitize_rewritten_output(self, html: str) -> str:
        """修复模型输出的常见格式问题，并移除残留推广块。"""
        cleaned = (html or "").strip()
        if not cleaned:
            return ""

        cleaned = re.sub(r"^```(?:html)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        soup = BeautifulSoup(cleaned, "html.parser")
        for tag in soup.find_all(["script", "style", "iframe"]):
            tag.decompose()
        for tag in soup.find_all(["html", "body"]):
            tag.unwrap()

        allowed_tags = {
            "h2", "h3", "p", "strong", "em", "ul", "ol", "li",
            "blockquote", "figure", "img", "figcaption", "br",
        }
        for tag in list(soup.find_all(True)):
            if tag.name not in allowed_tags:
                tag.unwrap()
                continue

            if tag.name == "img":
                src = tag.get("src") or tag.get("data-src") or ""
                alt = tag.get("alt") or ""
                if self._is_promotional_image(src, alt):
                    parent = tag.parent
                    tag.decompose()
                    if parent and parent.name == "figure" and not parent.get_text(strip=True) and not parent.find("img"):
                        parent.decompose()
                    continue
                tag.attrs = {
                    key: value
                    for key, value in tag.attrs.items()
                    if key in {"src", "data-src", "alt"}
                }
            else:
                tag.attrs = {}

        for tag in list(soup.find_all(["p", "li", "blockquote", "figcaption", "h2", "h3"])):
            text = tag.get_text(" ", strip=True)
            if not text:
                tag.decompose()
                continue
            if self._is_promotional_text(text):
                tag.decompose()

        return str(soup).strip()

    def _is_promotional_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "").lower()
        return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in self.PROMOTION_LINE_PATTERNS)

    def _is_promotional_image(self, src: str, alt: str = "") -> bool:
        normalized = f"{src or ''} {alt or ''}".lower()
        return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in self.PROMOTION_IMAGE_PATTERNS)

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
