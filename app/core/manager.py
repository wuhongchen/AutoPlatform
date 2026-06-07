"""
应用主管理器
"""
import mimetypes
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from app.config import get_settings
from app.models import (
    FeedSource,
    Account, Article, ArticleStatus,
    InspirationRecord, InspirationStatus,
    StylePreset, Task, TaskStatus, TaskName,
    ImageAsset, ImageAssetSource,
)
from app.services import (
    StorageService,
    AIService,
    CollectorService,
    WechatService,
    WechatLoginStateService,
    ImageService,
)
from app.services.style_presets import STYLE_PRESETS
from app.core.logger import get_logger
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = get_logger("manager")

class AppManager:
    """应用主管理器"""
    
    def __init__(self):
        self.storage = StorageService()
        self.ai = AIService()
        self.collector = CollectorService()
        self.image = ImageService()
        self._init_builtin_presets()
        self._init_builtin_ai_configs()
        self._ensure_feed_sources_table()
        self._repair_collected_html()
        self._repair_task_account_bindings()
        self._init_executor()
    
    def _init_executor(self):
        """初始化任务执行器"""
        from app.core.executor import TaskExecutor
        executor = TaskExecutor()
        executor.set_manager(self)
        logger.info("[manager] task executor initialized")

    def _resolve_task_account_id(self, payload: Optional[Dict], account_id: str = "") -> str:
        """为任务补全账户归属，优先显式值，其次从文章反查。"""
        if account_id:
            return account_id

        payload = payload or {}
        payload_account_id = (payload.get("account_id") or "").strip()
        if payload_account_id:
            return payload_account_id

        article_id = payload.get("article_id")
        if article_id:
            article = self.storage.get_article(article_id)
            if article and article.account_id:
                return article.account_id

        return ""

    def _repair_task_account_bindings(self):
        """启动时修复历史上未绑定账户的任务，避免任务看板漏显示。"""
        repaired = 0
        for task in self.storage.list_tasks(limit=10000):
            if task.account_id:
                continue
            resolved_account_id = self._resolve_task_account_id(task.payload)
            if not resolved_account_id:
                continue
            if self.storage.update_task(task.id, {"account_id": resolved_account_id}):
                repaired += 1

        if repaired:
            logger.info(f"[manager] repaired task account bindings: {repaired}")

    def _repair_collected_html(self):
        """修复历史采集内容中的隐藏样式，避免详情和文章正文不可见。"""
        repaired_inspirations = 0
        for record in self.storage.list_inspirations(limit=10000):
            relinked_html = self.collector.relink_local_images(
                record.content_html or "",
                record.images or [],
            )
            sanitized_html = self.collector.sanitize_content_html(relinked_html)
            if sanitized_html == (record.content_html or ""):
                continue
            self.storage.update_inspiration(record.id, {"content_html": sanitized_html})
            repaired_inspirations += 1

        repaired_articles = 0
        for article in self.storage.list_articles(limit=10000):
            updates = {}
            original_html = article.original_html or ""
            rewritten_html = article.rewritten_html or ""
            sanitized_original_html = self.collector.sanitize_content_html(
                self.collector.relink_local_images(original_html, article.images or [])
            )
            sanitized_rewritten_html = self.collector.sanitize_content_html(
                self.collector.relink_local_images(rewritten_html, article.images or [])
            )
            merged_rewritten_html = sanitized_rewritten_html
            if sanitized_rewritten_html and "<img" not in sanitized_rewritten_html.lower():
                merged_rewritten_html = self._merge_rewritten_html_with_original_images(
                    article,
                    sanitized_rewritten_html,
                )
            if sanitized_original_html != original_html:
                updates["original_html"] = sanitized_original_html
            if merged_rewritten_html != rewritten_html:
                updates["rewritten_html"] = merged_rewritten_html
            if updates:
                self.storage.update_article(article.id, updates)
                repaired_articles += 1

        if repaired_inspirations or repaired_articles:
            logger.info(
                "[manager] repaired hidden collected html: "
                f"inspirations={repaired_inspirations} articles={repaired_articles}"
            )

    def create_task(self, name: str, payload: dict, account_id: str = "", target_id: str = "") -> Task:
        """创建并提交异步任务"""
        from app.core.executor import TaskExecutor

        resolved_account_id = self._resolve_task_account_id(payload, account_id)
        task = Task(
            id=str(uuid.uuid4()),
            name=TaskName(name),
            payload=payload,
            status=TaskStatus.PENDING,
            account_id=resolved_account_id,
            target_id=target_id or payload.get("article_id", ""),
        )
        self.storage.create_task(task)
        
        executor = TaskExecutor()
        executor.submit(task.id)
        
        logger.info(f"[manager] task created: {task.id} ({name})")
        return task
    
    def _init_builtin_presets(self):
        """初始化内置风格预设到数据库"""
        builtin_presets = [
            StylePreset(
                id=p.id,
                name=p.name,
                description=p.description,
                system_prompt=p.system_prompt,
                tone=p.tone,
                style=p.style,
                temperature=p.temperature,
                max_tokens=p.max_tokens,
                is_builtin=True,
                is_active=True,
                params=p.params
            )
            for p in STYLE_PRESETS.values()
        ]
        self.storage.init_builtin_presets(builtin_presets)
    
    def create_account(self, name: str, account_id: str, **kwargs) -> Account:
        account = Account(id=account_id, name=name, account_id=account_id, **kwargs)
        return self.storage.create_account(account)

    def merge_wechat_cached_articles_into_inspirations(self, account_id: str, limit: int = 200) -> Dict:
        """将公众号雷达已缓存的文章自动并入统一素材库。"""
        if not account_id:
            return {"ok": True, "inserted": 0, "skipped": 0, "records": []}

        service = self._get_wechat_login_service(account_id)
        target_mp_ids: list[str] = [""]
        article_count = 0
        if hasattr(service, "load_state"):
            state = service.load_state()
            article_count = sum(len(items or []) for items in (state.get("articles") or {}).values())
            target_mp_ids = [""]
        else:
            if hasattr(service, "list_mps"):
                mps = service.list_mps().get("items") or []
                target_mp_ids = [item.get("id", "") for item in mps if item.get("id")]
            try:
                listed = service.list_articles(limit=1, include_content=False)
            except TypeError:
                listed = service.list_articles(limit=1)
            article_count = int(listed.get("count") or 0)
            if target_mp_ids:
                article_count = 0
                for mp_id in target_mp_ids:
                    try:
                        listed_mp = service.list_articles(mp_id=mp_id, limit=1, include_content=False)
                    except TypeError:
                        listed_mp = service.list_articles(mp_id=mp_id, limit=1)
                    article_count += int(listed_mp.get("count") or 0)
        if article_count <= 0:
            return {"ok": True, "inserted": 0, "skipped": 0, "records": []}

        try:
            if target_mp_ids == [""]:
                try:
                    return service.sync_articles_to_inspirations(
                        storage=self.storage,
                        collector=self.collector,
                        limit=max(1, int(limit)),
                        skip_diagnostics=True,
                    )
                except TypeError:
                    return service.sync_articles_to_inspirations(
                        storage=self.storage,
                        collector=self.collector,
                        limit=max(1, int(limit)),
                    )

            merged = {"ok": True, "inserted": 0, "skipped": 0, "records": []}
            for mp_id in target_mp_ids:
                try:
                    result = service.sync_articles_to_inspirations(
                        storage=self.storage,
                        collector=self.collector,
                        mp_id=mp_id,
                        limit=max(1, int(limit)),
                        skip_diagnostics=True,
                    )
                except TypeError:
                    result = service.sync_articles_to_inspirations(
                        storage=self.storage,
                        collector=self.collector,
                        mp_id=mp_id,
                        limit=max(1, int(limit)),
                    )
                merged["inserted"] += int(result.get("inserted") or 0)
                merged["skipped"] += int(result.get("skipped") or 0)
                merged["records"].extend(result.get("records") or [])
            return merged
        except Exception as exc:
            logger.warning(f"[manager] failed to merge wechat cached articles for {account_id}: {exc}")
            return {"ok": False, "inserted": 0, "skipped": 0, "records": [], "error": str(exc)}

    def _normalize_article_content(self, content: str) -> tuple[str, str]:
        """将后台输入规范化为 HTML 与纯文本"""
        raw_content = (content or "").strip()
        if not raw_content:
            return "", ""

        looks_like_html = bool(re.search(r"</?[a-z][\s\S]*>", raw_content, re.IGNORECASE))
        if looks_like_html:
            html = raw_content
        else:
            paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n", raw_content) if segment.strip()]
            html = "".join(
                f"<p>{paragraph.replace(chr(10), '<br>')}</p>"
                for paragraph in paragraphs
            )

        text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
        return html, text

    def _extract_reusable_article_images(self, article: Article) -> List[Dict[str, str]]:
        """提取可在改写成稿中复用的正文图片及其上下文。"""
        original_html = article.original_html or ""
        if not original_html:
            return []

        explicit_images = [item.strip() for item in (article.images or []) if item and item.strip()]
        explicit_image_set = set(explicit_images)
        soup = BeautifulSoup(original_html, "html.parser")
        reusable: List[Dict[str, str]] = []
        seen: set[str] = set()
        blocks = soup.find_all(["p", "h2", "h3", "h4", "li", "figcaption", "blockquote"])

        def _context_for_image(target_img) -> str:
            for index, block in enumerate(blocks):
                if target_img in block.find_all("img"):
                    nearby = []
                    for candidate in blocks[max(0, index - 1): index + 2]:
                        text = candidate.get_text(" ", strip=True)
                        if text:
                            nearby.append(text)
                    return " ".join(nearby)[:180]

            previous_text = ""
            next_text = ""
            previous_tag = target_img.find_previous(["p", "h2", "h3", "h4", "li", "figcaption", "blockquote"])
            next_tag = target_img.find_next(["p", "h2", "h3", "h4", "li", "figcaption", "blockquote"])
            if previous_tag:
                previous_text = previous_tag.get_text(" ", strip=True)
            if next_tag:
                next_text = next_tag.get_text(" ", strip=True)
            return " ".join(part for part in [previous_text, next_text] if part)[:180]

        for img in soup.find_all("img"):
            src = (img.get("data-src") or img.get("src") or "").strip()
            if not src or src.startswith("data:") or src in seen:
                continue

            should_keep = src in explicit_image_set
            try:
                if self.collector._is_qr_or_ad(src, img):
                    should_keep = False
            except Exception:
                pass

            image_context = _context_for_image(img)
            direct_context = ""
            if img.parent and getattr(img.parent, "name", "") != "[document]":
                direct_context = img.parent.get_text(" ", strip=True)
            promo_context = re.sub(
                r"\s+",
                "",
                " ".join([src, img.get("alt") or "", direct_context]).lower(),
            )
            if re.search(r"扫码|二维码|关注公众号|公众号关注|长按识别|加微信|读者群|交流群|赞赏|商务合作|广告", promo_context):
                should_keep = False

            if not should_keep:
                continue

            seen.add(src)
            reusable.append({
                "src": src,
                "alt": (img.get("alt") or "").strip(),
                "context": image_context,
            })

        return reusable

    def _extract_article_image_contexts(self, article: Article) -> List[Dict[str, str]]:
        """提取供 AI 改写参考的图片上下文线索。"""
        image_contexts = []
        for index, item in enumerate(self._extract_reusable_article_images(article), 1):
            context = {
                "index": index,
                "alt": item.get("alt", ""),
                "context": item.get("context", ""),
            }
            if context["alt"] or context["context"]:
                image_contexts.append(context)
        return image_contexts

    def _select_image_anchor_index(self, anchor_texts: List[str], image_context: str, fallback_index: int) -> int:
        """按上下文匹配图片插入位置，匹配失败时使用均匀分布兜底。"""
        normalized_context = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", (image_context or "").lower()))
        if not normalized_context:
            return fallback_index

        best_index = fallback_index
        best_score = 0.0
        for index, text in enumerate(anchor_texts):
            normalized_text = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", (text or "").lower()))
            if not normalized_text:
                continue
            score = len(normalized_context & normalized_text) / max(1, len(normalized_context))
            if score > best_score:
                best_score = score
                best_index = index

        return best_index if best_score >= 0.18 else fallback_index

    def _merge_rewritten_html_with_original_images(self, article: Article, rewritten_html: str) -> str:
        """将原文中可复用的正文图片按节奏插回改写成稿。"""
        html = (rewritten_html or "").strip()
        if not html:
            return html

        reusable_images = self._extract_reusable_article_images(article)
        if not reusable_images:
            return html

        rewritten_soup = BeautifulSoup(html, "html.parser")
        existing_sources = {
            (img.get("data-src") or img.get("src") or "").strip()
            for img in rewritten_soup.find_all("img")
            if (img.get("data-src") or img.get("src") or "").strip()
        }
        remaining_images = [item for item in reusable_images if item["src"] not in existing_sources]
        if not remaining_images:
            return html

        anchors = rewritten_soup.find_all(["p", "h2", "h3", "h4", "ul", "ol", "blockquote"])
        if not anchors:
            container = rewritten_soup.body or rewritten_soup
            for item in remaining_images:
                figure = rewritten_soup.new_tag("figure")
                image_tag = rewritten_soup.new_tag("img", src=item["src"])
                image_tag["loading"] = "lazy"
                image_tag["referrerpolicy"] = "no-referrer"
                if item["alt"]:
                    image_tag["alt"] = item["alt"]
                figure.append(image_tag)
                container.append(figure)
            return self.collector.sanitize_content_html(str(rewritten_soup))

        last_inserted_after: Dict[int, object] = {}
        anchor_count = len(anchors)
        image_count = len(remaining_images)
        anchor_texts = [anchor.get_text(" ", strip=True) for anchor in anchors]
        for index, item in enumerate(remaining_images):
            fallback_anchor_index = min(
                anchor_count - 1,
                max(0, round(((index + 1) * anchor_count) / (image_count + 1)) - 1),
            )
            target_anchor_index = self._select_image_anchor_index(
                anchor_texts=anchor_texts,
                image_context=item.get("context", ""),
                fallback_index=fallback_anchor_index,
            )
            anchor = anchors[target_anchor_index]

            figure = rewritten_soup.new_tag("figure")
            image_tag = rewritten_soup.new_tag("img", src=item["src"])
            image_tag["loading"] = "lazy"
            image_tag["referrerpolicy"] = "no-referrer"
            if item["alt"]:
                image_tag["alt"] = item["alt"]
            figure.append(image_tag)

            anchor_key = id(anchor)
            previous = last_inserted_after.get(anchor_key)
            if previous is not None:
                previous.insert_after(figure)
            else:
                anchor.insert_after(figure)
            last_inserted_after[anchor_key] = figure

        merged_html = self.collector.sanitize_content_html(str(rewritten_soup))
        return self.collector.relink_local_images(merged_html, article.images or [])

    def _save_image_bytes(
        self,
        image_bytes: bytes,
        account_id: str,
        filename: str,
        mime_type: str = "",
    ) -> tuple[str, str, str]:
        """保存图片到本地并返回相对路径与访问地址"""
        settings = get_settings()
        image_root = settings.data_dir / "images" / "assets" / account_id
        image_root.mkdir(parents=True, exist_ok=True)

        safe_name = secure_filename(filename) or f"{uuid.uuid4().hex}.png"
        ext = Path(safe_name).suffix
        if not ext:
            guessed_ext = mimetypes.guess_extension(mime_type or "image/png") or ".png"
            ext = guessed_ext
        final_name = f"{uuid.uuid4().hex}{ext.lower()}"
        file_path = image_root / final_name
        file_path.write_bytes(image_bytes)

        relative_path = file_path.relative_to(settings.data_dir / "images").as_posix()
        image_url = f"/local_images/{relative_path}"
        final_mime_type = mime_type or mimetypes.guess_type(str(file_path))[0] or "image/png"
        return relative_path, image_url, final_mime_type

    def list_image_assets(self, account_id: Optional[str] = None) -> List[ImageAsset]:
        return self.storage.list_image_assets(account_id=account_id)

    def upload_image_asset(
        self,
        file: FileStorage,
        account_id: str,
        title: str = "",
    ) -> ImageAsset:
        if not file or not file.filename:
            raise Exception("请选择图片文件")
        if not account_id:
            raise Exception("账户不能为空")

        raw_bytes = file.read()
        if not raw_bytes:
            raise Exception("图片内容为空")

        relative_path, image_url, mime_type = self._save_image_bytes(
            raw_bytes,
            account_id=account_id,
            filename=file.filename,
            mime_type=file.mimetype or "",
        )
        asset = ImageAsset(
            id=str(uuid.uuid4()),
            title=(title or Path(file.filename).stem or "未命名图片").strip(),
            source_type=ImageAssetSource.UPLOAD,
            image_url=image_url,
            file_path=relative_path,
            mime_type=mime_type,
            account_id=account_id,
            metadata={"original_filename": file.filename},
        )
        return self.storage.create_image_asset(asset)

    def generate_image_asset(
        self,
        prompt: str,
        account_id: str,
        title: str = "",
        size: str = "",
    ) -> ImageAsset:
        if not prompt.strip():
            raise Exception("图片提示词不能为空")
        if not account_id:
            raise Exception("账户不能为空")

        result = self.image.generate(prompt=prompt, size=size)
        relative_path, image_url, mime_type = self._save_image_bytes(
            result["bytes"],
            account_id=account_id,
            filename=f"ai_{uuid.uuid4().hex}.png",
            mime_type=result.get("mime_type", "image/png"),
        )
        asset = ImageAsset(
            id=str(uuid.uuid4()),
            title=(title or prompt[:24] or "AI 配图").strip(),
            prompt=prompt.strip(),
            source_type=ImageAssetSource.AI,
            image_url=image_url,
            file_path=relative_path,
            mime_type=mime_type,
            account_id=account_id,
            metadata={
                "size": size,
                "revised_prompt": result.get("revised_prompt", ""),
            },
        )
        return self.storage.create_image_asset(asset)

    def delete_image_asset(self, asset_id: str) -> bool:
        asset = self.storage.get_image_asset(asset_id)
        if not asset:
            return False

        settings = get_settings()
        file_path = settings.data_dir / "images" / asset.file_path
        if file_path.exists() and file_path.is_file():
            os.remove(file_path)
        return self.storage.delete_image_asset(asset_id)
    
    def get_account(self, account_id: str) -> Optional[Account]:
        return self.storage.get_account(account_id)
    
    def list_accounts(self) -> List[Account]:
        return self.storage.list_accounts()

    def _get_wechat_login_service(self, account_id: str) -> WechatLoginStateService:
        target_account_id = (account_id or "").strip() or "default"
        account = self.storage.get_account(target_account_id)
        if not account:
            raise Exception("账户不存在")
        return WechatLoginStateService(account)

    def wechat_ingest_status(self, account_id: str) -> Dict:
        return self._get_wechat_login_service(account_id).status()

    def wechat_ingest_login(
        self,
        account_id: str,
        wait: bool = False,
        qr_display: str = "none",
        timeout: int = 60,
        token_wait_timeout: int = 20,
        thread_join_timeout: int = 8,
    ) -> Dict:
        return self._get_wechat_login_service(account_id).login(
            wait=wait,
            qr_display=qr_display,
            timeout=timeout,
            token_wait_timeout=token_wait_timeout,
            thread_join_timeout=thread_join_timeout,
        )

    def wechat_ingest_search_mp(self, account_id: str, keyword: str, limit: int = 10, offset: int = 0) -> Dict:
        return self._get_wechat_login_service(account_id).search_mp(keyword=keyword, limit=limit, offset=offset)

    def wechat_ingest_list_mps(self, account_id: str) -> Dict:
        return self._get_wechat_login_service(account_id).list_mps()

    def wechat_ingest_add_mp(
        self,
        account_id: str,
        keyword: str,
        pick: int = 1,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict:
        return self._get_wechat_login_service(account_id).add_mp(
            keyword=keyword,
            pick=pick,
            limit=limit,
            offset=offset,
        )

    def wechat_ingest_pull_articles(
        self,
        account_id: str,
        mp_id: str,
        pages: int = 1,
        mode: str = "api",
        with_content: bool = False,
    ) -> Dict:
        return self._get_wechat_login_service(account_id).pull_articles(
            mp_id=mp_id,
            pages=pages,
            mode=mode,
            with_content=with_content,
        )

    def wechat_ingest_list_articles(self, account_id: str, mp_id: str = "", limit: int = 50) -> Dict:
        return self._get_wechat_login_service(account_id).list_articles(mp_id=mp_id, limit=limit)

    def wechat_ingest_article_preview(self, account_id: str, mp_id: str, article_id: str) -> Dict:
        return self._get_wechat_login_service(account_id).get_article_preview(
            collector=self.collector,
            mp_id=mp_id,
            article_id=article_id,
        )

    def wechat_ingest_batch_fetch_content(
        self,
        account_id: str,
        mp_id: str = "",
        limit: int = 10,
        skip_existing: bool = True,
        continue_on_error: bool = True,
        sleep_sec: float = 0.8,
    ) -> Dict:
        return self._get_wechat_login_service(account_id).batch_fetch_content(
            mp_id=mp_id,
            limit=limit,
            skip_existing=skip_existing,
            continue_on_error=continue_on_error,
            sleep_sec=sleep_sec,
        )

    def wechat_ingest_sync_inspirations(self, account_id: str, mp_id: str = "", limit: int = 20) -> Dict:
        return self._get_wechat_login_service(account_id).sync_articles_to_inspirations(
            storage=self.storage,
            collector=self.collector,
            mp_id=mp_id,
            limit=limit,
        )

    def wechat_ingest_full_flow(
        self,
        account_id: str,
        mp_id: str = "",
        keyword: str = "",
        pick: int = 1,
        pages: int = 1,
        mode: str = "api",
        with_content: bool = False,
        content_limit: int = 10,
        sync_limit: int = 20,
    ) -> Dict:
        return self._get_wechat_login_service(account_id).full_flow(
            storage=self.storage,
            collector=self.collector,
            mp_id=mp_id,
            keyword=keyword,
            pick=pick,
            pages=pages,
            mode=mode,
            with_content=with_content,
            content_limit=content_limit,
            sync_limit=sync_limit,
        )

    def _build_account_rewrite_instructions(
        self,
        account: Optional[Account],
        custom_instructions: Optional[str] = None,
    ) -> str:
        """拼接账户级内容方向与本次补充要求。"""
        parts: List[str] = []
        if account:
            account_instruction_fields = [
                ("账号内容方向", account.content_direction),
                ("账号改写要求", account.prompt_direction),
                ("公众号成稿要求", account.wechat_prompt_direction),
            ]
            for label, value in account_instruction_fields:
                value = (value or "").strip()
                if value:
                    parts.append(f"{label}：{value}")

        custom_instructions = (custom_instructions or "").strip()
        if custom_instructions:
            parts.append(f"本次补充要求：{custom_instructions}")

        return "\n".join(parts)

    def render_article_for_wechat_copy(
        self,
        article_id: str,
        template: str = "default",
        full_html: bool = False,
    ) -> Dict[str, str]:
        """将已改写文章渲染为可复制到微信公众号编辑器的 HTML。"""
        article = self.storage.get_article(article_id)
        if not article:
            raise Exception("文章不存在")
        if not (article.rewritten_html or article.original_html):
            raise Exception("文章内容为空")

        account = self.storage.get_account(article.account_id)
        template_name = (template or "").strip() or "default"
        content_html = article.rewritten_html or article.original_html
        author = article.source_author or (account.wechat_author if account else "")
        cover_image = article.cover_image or (article.images[0] if article.images else "")
        wechat = WechatService(
            account.wechat_appid if account else "",
            account.wechat_secret if account else "",
        )
        html = wechat.render_with_template(
            title=article.source_title or "无标题",
            content=content_html,
            template_name=template_name,
            author=author,
            cover_image=cover_image,
            full_html=full_html,
            ad_header_html=account.ad_header_html if account else "",
            ad_footer_html=account.ad_footer_html if account else "",
        )
        text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
        return {
            "article_id": article.id,
            "account_id": article.account_id,
            "title": article.source_title,
            "template": template_name,
            "html": html,
            "text": text,
        }

    async def run_content_flow_from_url(
        self,
        url: str,
        account_id: str,
        style: Optional[str] = None,
        template: str = "default",
        use_references: bool = True,
        custom_instructions: Optional[str] = None,
        inspiration_ids: Optional[List[str]] = None,
        task_id: str = "",
    ) -> Dict:
        """从链接采集、生成文章、改写，并输出公众号可复制 HTML。"""
        url = (url or "").strip()
        if not url:
            raise Exception("链接不能为空")

        account_id = (account_id or "").strip() or "default"
        account = self.storage.get_account(account_id)
        if not account:
            raise Exception("账户不存在")

        template_name = (template or "").strip() or "default"
        selected_style = (style or account.pipeline_role or "tech_expert").strip()
        logger.info(
            f"[content_flow] start url={url} account={account_id} "
            f"style={selected_style} template={template_name}"
        )

        record = await self.collect_inspiration(url=url, account_id=account_id)
        record_metadata = dict(record.metadata or {})
        record_metadata["content_flow"] = {
            "task_id": task_id,
            "stage": "collected",
            "created_at": datetime.now().isoformat(),
        }
        self.storage.update_inspiration(record.id, {"metadata": record_metadata})

        article = self.create_article_from_inspiration(record.id)
        combined_instructions = self._build_account_rewrite_instructions(
            account,
            custom_instructions=custom_instructions,
        )
        rewritten_article = await self.rewrite_article(
            article_id=article.id,
            style=selected_style,
            use_references=use_references,
            custom_instructions=combined_instructions or None,
            inspiration_ids=inspiration_ids,
        )
        formatted = self.render_article_for_wechat_copy(
            rewritten_article.id,
            template=template_name,
        )

        article_metadata = dict(rewritten_article.metadata or {})
        article_metadata["content_flow"] = {
            "task_id": task_id,
            "inspiration_id": record.id,
            "template": template_name,
            "copy_ready": True,
            "completed_at": datetime.now().isoformat(),
        }
        self.storage.update_article(rewritten_article.id, {"metadata": article_metadata})
        self.storage.update_account(account_id, {
            "last_run_at": datetime.now().isoformat(),
            "run_count": (account.run_count or 0) + 1,
        })

        logger.info(
            f"[content_flow] completed url={url} article={rewritten_article.id} "
            f"inspiration={record.id}"
        )
        return {
            "ok": True,
            "task_id": task_id,
            "account_id": account_id,
            "url": url,
            "inspiration_id": record.id,
            "article_id": rewritten_article.id,
            "title": rewritten_article.source_title,
            "style": selected_style,
            "template": template_name,
            "article_status": rewritten_article.status.value,
            "copy_ready": True,
            "copy_text_length": len(formatted["text"]),
            "steps": [
                {
                    "name": "采集",
                    "module": "inspirations",
                    "status": "completed",
                    "id": record.id,
                },
                {
                    "name": "生成文章",
                    "module": "articles",
                    "status": "completed",
                    "id": article.id,
                },
                {
                    "name": "AI 改写",
                    "module": "articles",
                    "status": "completed",
                    "id": rewritten_article.id,
                },
                {
                    "name": "公众号格式",
                    "module": "templates",
                    "status": "completed",
                    "id": template_name,
                },
            ],
        }
    
    async def collect_inspiration(self, url: str, account_id: str) -> InspirationRecord:
        logger.info(f"[collect] url={url} account={account_id}")
        result = self.collector.fetch_url(url)
        if not result["success"]:
            logger.error(f"[collect] failed: {result.get('error')}")
            raise Exception(f"采集失败: {result.get('error')}")
        
        record_id = str(uuid.uuid4())
        
        # 下载图片到本地
        images = result["images"]
        content_html = self.collector.sanitize_content_html(result["content_html"])
        if images:
            from app.config import get_settings
            settings = get_settings()
            image_dir = str(settings.data_dir / "images")
            local_paths, url_map = self.collector.download_images(
                images, record_id, base_dir=image_dir
            )
            if url_map:
                content_html = self.collector.rewrite_image_urls(content_html, url_map)
                images = local_paths
                logger.info(f"[collect] downloaded {len(url_map)} images for {record_id}")
        
        record = InspirationRecord(
            id=record_id,
            source_url=url,
            title=result["title"],
            author=result["author"],
            content=result["content"],
            content_html=content_html,
            images=images,
            status=InspirationStatus.COLLECTED,
            account_id=account_id
        )
        self.storage.create_inspiration(record)
        return self.storage.get_inspiration(record.id)
    
    async def analyze_inspiration(self, record_id: str):
        """AI分析素材（不影响状态）"""
        record = self.storage.get_inspiration(record_id)
        if not record:
            logger.warning(f"[analyze] record not found: {record_id}")
            return

        try:
            logger.info(f"[analyze] scoring record={record_id} title={record.title[:30]}")
            score = await self.ai.score_article(record.title, record.content)
            self.storage.update_inspiration(record_id, {
                "ai_score": score["score"],
                "ai_reason": score["reason"],
                "ai_direction": score["direction"],
                "analyzed_at": datetime.now()
            })
            logger.info(f"[analyze] scored record={record_id} score={score['score']}")
        except Exception as e:
            logger.error(f"[analyze] failed record={record_id}: {e}")
            self.storage.update_inspiration(record_id, {
                "error_message": str(e)
            })
    
    def create_article_from_inspiration(self, record_id: str) -> Article:
        """从素材创建文章（素材库→我的文章）"""
        record = self.storage.get_inspiration(record_id)
        if not record:
            raise Exception("素材不存在")

        if record.article_id:
            existing_article = self.storage.get_article(record.article_id)
            if existing_article:
                return existing_article
        
        article = Article(
            id=str(uuid.uuid4()),
            source_url=record.source_url,
            source_title=record.title,
            source_author=record.author,
            original_content=record.content,
            original_html=self.collector.sanitize_content_html(record.content_html),
            images=record.images,
            status=ArticleStatus.PENDING,
            account_id=record.account_id
        )
        self.storage.create_article(article)
        self.storage.update_inspiration(record_id, {
            "article_id": article.id
        })
        return article

    def create_manual_article(self, data: Dict) -> Article:
        """后台手工创建文章"""
        title = (data.get("source_title") or data.get("title") or "").strip()
        if not title:
            raise Exception("文章标题不能为空")

        html_content, text_content = self._normalize_article_content(data.get("content", ""))
        if not html_content:
            raise Exception("文章内容不能为空")

        publish_ready = bool(data.get("publish_ready"))
        article_id = str(uuid.uuid4())
        account_id = data.get("account_id", "") or "default"
        account = self.storage.get_account(account_id)

        article = Article(
            id=article_id,
            source_url=(data.get("source_url") or f"manual://{article_id}").strip(),
            source_title=title,
            source_author=(data.get("source_author") or (account.wechat_author if account else "")).strip(),
            original_content=text_content,
            original_html=html_content,
            rewritten_content=text_content if publish_ready else "",
            rewritten_html=html_content if publish_ready else "",
            cover_image=(data.get("cover_image") or "").strip(),
            status=ArticleStatus.REWRITTEN if publish_ready else ArticleStatus.PENDING,
            account_id=account_id,
            metadata={
                "manual_created": True,
                "publish_ready": publish_ready,
                "last_edited_at": datetime.now().isoformat(),
            },
        )
        return self.storage.create_article(article)

    def update_article_content(self, article_id: str, data: Dict) -> Article:
        """后台编辑文章"""
        article = self.storage.get_article(article_id)
        if not article:
            raise Exception("文章不存在")
        if article.status == ArticleStatus.PUBLISHING:
            raise Exception("文章发布中，暂不允许编辑")

        title = (data.get("source_title") or data.get("title") or article.source_title or "").strip()
        if not title:
            raise Exception("文章标题不能为空")

        current_content = article.rewritten_html or article.original_html or article.original_content
        content_seed = data.get("content") if data.get("content") is not None else current_content
        html_content, text_content = self._normalize_article_content(content_seed)
        if not html_content:
            raise Exception("文章内容不能为空")

        publish_ready = bool(data.get("publish_ready"))
        editing_target = (data.get("editing_target") or ("rewritten" if article.rewritten_html else "original")).strip()
        metadata = dict(article.metadata or {})
        metadata.update({
            "manual_created": True,
            "publish_ready": publish_ready,
            "editing_target": editing_target,
            "last_edited_at": datetime.now().isoformat(),
        })

        self.storage.update_article(article_id, {
            "source_title": title,
            "source_author": (data.get("source_author") or article.source_author or "").strip(),
            "source_url": (data.get("source_url") or article.source_url or f"manual://{article_id}").strip(),
            "cover_image": (data.get("cover_image") or "").strip(),
            "original_content": text_content,
            "original_html": html_content,
            "rewritten_content": text_content if publish_ready else "",
            "rewritten_html": html_content if publish_ready else "",
            "status": ArticleStatus.REWRITTEN if publish_ready else ArticleStatus.PENDING,
            "metadata": metadata,
            "error_message": "",
        })
        return self.storage.get_article(article_id)
    
    async def rewrite_article(
        self,
        article_id: str,
        style: Optional[str] = None,
        use_references: bool = True,
        custom_instructions: Optional[str] = None,
        inspiration_ids: Optional[List[str]] = None
    ) -> Article:
        """改写文章"""
        article = self.storage.get_article(article_id)
        if not article:
            raise Exception("文章不存在")

        account = self.storage.get_account(article.account_id)

        if not style:
            style = article.rewrite_style or (account.pipeline_role if account else "tech_expert")

        logger.info(
            f"[rewrite] article={article_id} style={style} "
            f"refs={use_references} instructions={'yes' if custom_instructions else 'no'}"
        )

        reference_records = None
        if use_references:
            if inspiration_ids:
                reference_records = []
                for insp_id in inspiration_ids[:5]:
                    insp = self.storage.get_inspiration(insp_id)
                    if insp:
                        reference_records.append({
                            "id": insp.id,
                            "title": insp.title,
                            "content": insp.content,
                            "source_url": insp.source_url
                        })
            else:
                inspirations = self.storage.list_inspirations(
                    account_id=article.account_id,
                    limit=10
                )
                reference_records = [
                    {"title": i.title, "content": i.content}
                    for i in inspirations
                    if i.article_id != article.id and i.source_url != article.source_url
                ]

        self.storage.update_article(article_id, {"status": ArticleStatus.REWRITING})

        try:
            result = await self.ai.rewrite_with_context(
                content=article.original_content,
                style_preset=style,
                inspiration_records=reference_records if use_references else None,
                custom_instructions=custom_instructions,
                title=article.source_title,
                image_contexts=self._extract_article_image_contexts(article),
            )

            rewritten = self._merge_rewritten_html_with_original_images(
                article,
                result["content"],
            )
            used_refs = result.get("used_references", [])

            # 回写风格使用次数
            self.storage.increment_preset_usage(style)

            rewrite_mode = "manual" if inspiration_ids else ("auto" if use_references else "none")
            metadata = dict(article.metadata or {})
            metadata.update({
                "used_inspiration_ids": inspiration_ids or [],
                "reference_count": result.get("reference_count", 0),
                "rewrite_mode": rewrite_mode,
            })
            self.storage.update_article(article_id, {
                "rewritten_html": rewritten,
                "status": ArticleStatus.REWRITTEN,
                "rewrite_style": style,
                "rewrite_references": used_refs,
                "custom_instructions": custom_instructions or "",
                "metadata": metadata
            })
            logger.info(f"[rewrite] success article={article_id} style={style} mode={rewrite_mode}")
        except Exception as e:
            logger.error(f"[rewrite] failed article={article_id}: {e}")
            self.storage.update_article(article_id, {
                "status": ArticleStatus.FAILED,
                "error_message": str(e)
            })
            raise

        return self.storage.get_article(article_id)
    
    def get_style_presets(self) -> List[Dict]:
        """获取所有改写风格预设（从数据库）"""
        presets = self.storage.list_style_presets()
        return [p.model_dump() for p in presets]
    
    def get_style_preset(self, preset_id: str) -> Optional[StylePreset]:
        """获取单个风格预设"""
        return self.storage.get_style_preset(preset_id)
    
    def create_style_preset(self, preset_data: Dict) -> StylePreset:
        """创建自定义风格预设"""
        preset_id = (preset_data.get("id") or "").strip() or str(uuid.uuid4())
        preset = StylePreset(
            id=preset_id,
            name=preset_data["name"],
            description=preset_data.get("description", ""),
            system_prompt=preset_data["system_prompt"],
            tone=preset_data.get("tone", "professional"),
            style=preset_data.get("style", "analytical"),
            temperature=preset_data.get("temperature", 0.7),
            max_tokens=preset_data.get("max_tokens", 4000),
            is_builtin=False,
            is_active=True,
            params=preset_data.get("params", {})
        )
        return self.storage.create_style_preset(preset)
    
    def update_style_preset(self, preset_id: str, data: Dict) -> bool:
        """更新风格预设（只能更新非内置）"""
        return self.storage.update_style_preset(preset_id, data)
    
    def delete_style_preset(self, preset_id: str) -> bool:
        """删除风格预设（只能删除非内置）"""
        return self.storage.delete_style_preset(preset_id)
    
    def toggle_style_preset(self, preset_id: str) -> bool:
        """启用/禁用风格预设"""
        preset = self.storage.get_style_preset(preset_id)
        if not preset:
            return False
        return self.storage.update_style_preset(preset_id, {"is_active": not preset.is_active})
    
    async def publish_article(self, article_id: str,
                             template: str = "default") -> Article:
        """发布文章"""
        article = self.storage.get_article(article_id)
        if not article:
            raise Exception("文章不存在")

        account = self.storage.get_account(article.account_id)
        if not account or not account.wechat_appid:
            raise Exception("微信配置不完整")

        logger.info(f"[publish] article={article_id} template={template}")

        wechat = WechatService(account.wechat_appid, account.wechat_secret)
        self.storage.update_article(article_id, {"status": ArticleStatus.PUBLISHING})

        try:
            author = article.source_author or account.wechat_author
            content = wechat.render_with_template(
                title=article.source_title,
                content=article.rewritten_html or article.original_html,
                template_name=template,
                author=author,
                cover_image=article.cover_image,
                ad_header_html=account.ad_header_html,
                ad_footer_html=account.ad_footer_html,
            )

            draft_id = wechat.create_draft(
                title=article.source_title,
                content=content,
                author=author
            )

            metadata = dict(article.metadata or {})
            metadata.update({
                "template": template,
                "ad_header_enabled": bool((account.ad_header_html or "").strip()),
                "ad_footer_enabled": bool((account.ad_footer_html or "").strip()),
            })
            self.storage.update_article(article_id, {
                "wechat_draft_id": draft_id,
                "status": ArticleStatus.PUBLISHED,
                "published_at": datetime.now(),
                "metadata": metadata
            })
            logger.info(f"[publish] success article={article_id} draft_id={draft_id}")
        except Exception as e:
            logger.error(f"[publish] failed article={article_id}: {e}")
            self.storage.update_article(article_id, {
                "status": ArticleStatus.FAILED,
                "error_message": str(e)
            })
            raise

        return self.storage.get_article(article_id)
    
    def get_templates(self) -> Dict:
        """获取可用模板列表"""
        from app.templates import TemplateRegistry
        return TemplateRegistry.list_templates()
    
    async def process_pipeline(self, account_id: str, batch_size: int = 3,
                                style: Optional[str] = None,
                                template: str = "default") -> Task:
        """批量处理任务（已转为异步任务模式）"""
        return self.create_task(
            name="batch",
            payload={
                "batch_size": batch_size,
                "style": style,
                "template": template,
            },
            account_id=account_id,
        )
    
    def _ensure_feed_sources_table(self):
        """确保 feed_sources 表存在（兼容旧数据库）"""
        pass  # storage._init_tables 已处理

    # ─── RSS 信息源管理 ───────────────────────────────────────────

    def list_feed_sources(self, account_id: Optional[str] = None) -> List[Dict]:
        return self.storage.list_feed_sources(account_id=account_id)

    def get_feed_source(self, feed_id: str) -> Optional[Dict]:
        return self.storage.get_feed_source(feed_id)

    def create_feed_source(self, data: Dict) -> Dict:
        import uuid
        data["id"] = data.get("id") or f"feed_{uuid.uuid4().hex[:8]}"
        return self.storage.create_feed_source(data)

    def update_feed_source(self, feed_id: str, data: Dict) -> bool:
        return self.storage.update_feed_source(feed_id, data)

    def delete_feed_source(self, feed_id: str) -> bool:
        return self.storage.delete_feed_source(feed_id)

    def toggle_feed_source(self, feed_id: str) -> bool:
        return self.storage.toggle_feed_source(feed_id)

    def fetch_feed(self, feed_id: str) -> Dict:
        """抓取 RSS 源，将新条目写入灵感库"""
        import uuid, re
        import xml.etree.ElementTree as ET
        import requests
        from datetime import datetime

        feed = self.storage.get_feed_source(feed_id)
        if not feed:
            raise Exception("信息源不存在")

        try:
            resp = requests.get(feed["url"], timeout=30, headers={
                "User-Agent": "Mozilla/5.0 AutoPlatform/2.0 RSS Reader"
            })
            resp.encoding = resp.apparent_encoding or "utf-8"
            root = ET.fromstring(resp.text)
        except Exception as e:
            raise Exception(f"RSS 抓取失败: {e}")

        items = []
        # RSS 2.0
        for item in root.iter("item"):
            items.append({
                "title": self._rss_text(item, "title"),
                "link": self._rss_text(item, "link"),
                "description": self._rss_text(item, "description"),
                "author": self._rss_text(item, "author") or self._rss_text(item, "dc:creator"),
                "pub_date": self._rss_text(item, "pubDate"),
            })
        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//atom:entry", ns) or root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            link_el = entry.find("atom:link", ns) or entry.find("{http://www.w3.org/2005/Atom}link")
            items.append({
                "title": self._rss_text(entry, "title", ns),
                "link": link_el.get("href", "") if link_el is not None else "",
                "description": self._rss_text(entry, "summary", ns) or self._rss_text(entry, "content", ns),
                "author": self._rss_text(entry, "author/name", ns),
                "pub_date": self._rss_text(entry, "published", ns) or self._rss_text(entry, "updated", ns),
            })

        new_count = 0
        skipped = 0
        for item in items:
            url = (item.get("link") or "").strip()
            if not url:
                skipped += 1
                continue
            # 去重
            existing = self.storage.find_inspiration_by_url(url)
            if existing:
                skipped += 1
                continue
            # 清洗 HTML
            desc = item.get("description", "") or ""
            content_html = desc if desc.startswith("<") else f"<p>{desc}</p>"
            content_text = re.sub(r"<[^>]+>", "", desc).strip() if desc else ""
            # 写入灵感库
            record = InspirationRecord(
                id=f"insp_{uuid.uuid4().hex[:12]}",
                source_url=url,
                source_type="rss",
                source_account=feed.get("name", ""),
                title=item.get("title", "") or "无标题",
                author=item.get("author", ""),
                content=content_text,
                content_html=content_html,
                status=InspirationStatus.COLLECTED,
                account_id=feed.get("account_id", "default"),
            )
            self.storage.create_inspiration(record)
            new_count += 1

        # 更新 feed 状态
        self.storage.update_feed_source(feed_id, {
            "last_fetched_at": datetime.now().isoformat(),
            "item_count": feed.get("item_count", 0) + new_count,
        })

        return {
            "feed_id": feed_id,
            "new_items": new_count,
            "skipped": skipped,
            "total": len(items),
        }

    def _rss_text(self, element, tag: str, ns: dict = None) -> str:
        """安全提取 RSS 元素文本"""
        import xml.etree.ElementTree as ET
        try:
            if ns:
                el = element.find(tag, ns)
            else:
                el = element.find(tag)
            if el is None:
                # 尝试 namespace 形式 {ns}tag
                for child in element:
                    if child.tag.endswith("}" + tag) or child.tag == tag:
                        return (child.text or "").strip()
                return ""
            return (el.text or "").strip()
        except Exception:
            return ""

    def sync_published_articles(self, account_id: str) -> Dict:
        """从微信同步已发布文章到数据库"""
        account = self.storage.get_account(account_id)
        if not account or not account.wechat_appid:
            raise Exception("账户未配置微信凭证")

        from app.services.wechat import WechatService
        wechat = WechatService(account.wechat_appid, account.wechat_secret)
        result = wechat.get_published_list(count=20)
        synced = 0
        for item in result.get("items", []):
            url = item.get("url", "")
            if not url:
                continue
            existing = self.storage.find_inspiration_by_url(url)
            if existing:
                continue
            import uuid
            record = InspirationRecord(
                id=f"pub_{uuid.uuid4().hex[:12]}",
                source_url=url,
                source_type="wechat_published",
                source_account=account.name or account_id,
                title=item.get("title", "") or "无标题",
                author=item.get("author", ""),
                content="",
                content_html="",
                status=InspirationStatus.COLLECTED,
                account_id=account_id,
            )
            self.storage.create_inspiration(record)
            synced += 1
        return {"synced": synced, "total": result.get("total", 0)}

    def get_stats(self, account_id: Optional[str] = None) -> Dict:
        return self.storage.get_stats(account_id)

    # ─── AI 模型配置管理 ───────────────────────────────────────────

    def _init_builtin_ai_configs(self):
        """初始化内置 AI 配置预设"""
        try:
            settings = get_settings()
            api_key = settings.ai.api_key or ""
            self.storage.init_builtin_ai_configs(api_key)
        except Exception as e:
            logger.warning(f"[ai_config] init builtin configs warning: {e}")

    def list_ai_configs(self) -> List[Dict]:
        return self.storage.list_ai_configs()

    def get_ai_config(self, config_id: str) -> Optional[Dict]:
        return self.storage.get_ai_config(config_id)

    def create_ai_config(self, data: Dict) -> Dict:
        return self.storage.create_ai_config(data)

    def update_ai_config(self, config_id: str, data: Dict) -> bool:
        return self.storage.update_ai_config(config_id, data)

    def delete_ai_config(self, config_id: str) -> bool:
        return self.storage.delete_ai_config(config_id)

    def set_default_ai_config(self, config_id: str) -> bool:
        return self.storage.set_default_ai_config(config_id)

    async def test_ai_config(self, config_id: str) -> Dict:
        """测试 AI 配置连接"""
        import time
        config = self.storage.get_ai_config(config_id)
        if not config:
            raise Exception("配置不存在")
        if not config.get("api_key"):
            raise Exception("API Key 未配置")

        import openai
        client = openai.AsyncOpenAI(
            api_key=config["api_key"],
            base_url=config.get("endpoint", "https://api.deepseek.com/v1"),
            timeout=20,
        )
        start = time.time()
        try:
            response = await client.chat.completions.create(
                model=config["model"],
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
            )
            elapsed = round((time.time() - start) * 1000)
            return {
                "success": True,
                "latency_ms": elapsed,
                "model": config["model"],
                "response": response.choices[0].message.content.strip(),
            }
        except Exception as e:
            elapsed = round((time.time() - start) * 1000)
            return {
                "success": False,
                "latency_ms": elapsed,
                "error": str(e),
            }
