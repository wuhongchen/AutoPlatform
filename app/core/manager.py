"""
应用主管理器
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from app.models import (
    Account, Article, ArticleStatus,
    InspirationRecord, InspirationStatus,
    StylePreset, Task, TaskStatus, TaskName
)
from app.services import StorageService, AIService, CollectorService, WechatService
from app.services.style_presets import STYLE_PRESETS
from app.core.logger import get_logger

logger = get_logger("manager")

class AppManager:
    """应用主管理器"""
    
    def __init__(self):
        self.storage = StorageService()
        self.ai = AIService()
        self.collector = CollectorService()
        self._init_builtin_presets()
        self._init_executor()
    
    def _init_executor(self):
        """初始化任务执行器"""
        from app.core.executor import TaskExecutor
        executor = TaskExecutor()
        executor.set_manager(self)
        logger.info("[manager] task executor initialized")
    
    def create_task(self, name: str, payload: dict, account_id: str = "", target_id: str = "") -> Task:
        """创建并提交异步任务"""
        from app.core.executor import TaskExecutor
        
        task = Task(
            id=str(uuid.uuid4()),
            name=TaskName(name),
            payload=payload,
            status=TaskStatus.PENDING,
            account_id=account_id or payload.get("account_id", ""),
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
    
    def get_account(self, account_id: str) -> Optional[Account]:
        return self.storage.get_account(account_id)
    
    def list_accounts(self) -> List[Account]:
        return self.storage.list_accounts()
    
    async def collect_inspiration(self, url: str, account_id: str) -> InspirationRecord:
        logger.info(f"[collect] url={url} account={account_id}")
        result = self.collector.fetch_url(url)
        if not result["success"]:
            logger.error(f"[collect] failed: {result.get('error')}")
            raise Exception(f"采集失败: {result.get('error')}")
        
        record_id = str(uuid.uuid4())
        
        # 下载图片到本地
        images = result["images"]
        content_html = result["content_html"]
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
            status=InspirationStatus.PENDING_DECISION,
            account_id=account_id
        )
        self.storage.create_inspiration(record)
        return self.storage.get_inspiration(record.id)
    
    async def analyze_inspiration(self, record_id: str):
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
                "status": InspirationStatus.PENDING_DECISION
            })
            logger.info(f"[analyze] scored record={record_id} score={score['score']}")
        except Exception as e:
            logger.error(f"[analyze] failed record={record_id}: {e}")
            self.storage.update_inspiration(record_id, {
                "status": InspirationStatus.PENDING_DECISION,
                "error_message": str(e)
            })
    
    def approve_inspiration(self, record_id: str) -> Article:
        record = self.storage.get_inspiration(record_id)
        if not record:
            raise Exception("记录不存在")
        
        article = Article(
            id=str(uuid.uuid4()),
            source_url=record.source_url,
            source_title=record.title,
            source_author=record.author,
            original_content=record.content,
            original_html=record.content_html,
            images=record.images,
            status=ArticleStatus.PENDING,
            account_id=record.account_id
        )
        self.storage.create_article(article)
        self.storage.update_inspiration(record_id, {
            "status": InspirationStatus.IN_PIPELINE,
            "article_id": article.id
        })
        return article
    
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
                    for i in inspirations if i.id != article_id
                ]

        self.storage.update_article(article_id, {"status": ArticleStatus.REWRITING})

        try:
            result = await self.ai.rewrite_with_context(
                content=article.original_content,
                style_preset=style,
                inspiration_records=reference_records if use_references else None,
                custom_instructions=custom_instructions
            )

            rewritten = result["content"]
            used_refs = result.get("used_references", [])

            # 回写风格使用次数
            self.storage.increment_preset_usage(style)

            rewrite_mode = "manual" if inspiration_ids else ("auto" if use_references else "none")
            self.storage.update_article(article_id, {
                "rewritten_html": rewritten,
                "status": ArticleStatus.REWRITTEN,
                "rewrite_style": style,
                "rewrite_references": used_refs,
                "custom_instructions": custom_instructions or "",
                "metadata": {
                    "used_inspiration_ids": inspiration_ids or [],
                    "reference_count": len(reference_records) if reference_records else 0,
                    "rewrite_mode": rewrite_mode
                }
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
        preset = StylePreset(
            id=str(uuid.uuid4()),
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
            content = wechat.render_with_template(
                title=article.source_title,
                content=article.rewritten_html or article.original_html,
                template_name=template,
                author=account.wechat_author,
                cover_image=article.cover_image
            )

            draft_id = wechat.create_draft(
                title=article.source_title,
                content=content,
                author=account.wechat_author
            )

            self.storage.update_article(article_id, {
                "wechat_draft_id": draft_id,
                "status": ArticleStatus.PUBLISHED,
                "published_at": datetime.now(),
                "metadata": {"template": template}
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
    
    def get_stats(self, account_id: Optional[str] = None) -> Dict:
        return self.storage.get_stats(account_id)
