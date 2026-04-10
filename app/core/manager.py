"""
应用主管理器
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from app.models import (
    Account, Article, ArticleStatus, 
    InspirationRecord, InspirationStatus,
    StylePreset
)
from app.services import StorageService, AIService, CollectorService, WechatService
from app.services.style_presets import STYLE_PRESETS

class AppManager:
    """应用主管理器"""
    
    def __init__(self):
        self.storage = StorageService()
        self.ai = AIService()
        self.collector = CollectorService()
        self._init_builtin_presets()
    
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
        result = self.collector.fetch_url(url)
        if not result["success"]:
            raise Exception(f"采集失败: {result.get('error')}")
        
        record = InspirationRecord(
            id=str(uuid.uuid4()),
            source_url=url,
            title=result["title"],
            author=result["author"],
            content=result["content"],
            content_html=result["content_html"],
            images=result["images"],
            status=InspirationStatus.PENDING_ANALYSIS,
            account_id=account_id
        )
        self.storage.create_inspiration(record)
        await self.analyze_inspiration(record.id)
        return self.storage.get_inspiration(record.id)
    
    async def analyze_inspiration(self, record_id: str):
        record = self.storage.get_inspiration(record_id)
        if not record:
            return
        
        try:
            score = await self.ai.score_article(record.title, record.content)
            self.storage.update_inspiration(record_id, {
                "ai_score": score["score"],
                "ai_reason": score["reason"],
                "ai_direction": score["direction"],
                "status": InspirationStatus.PENDING_DECISION
            })
        except Exception as e:
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
        """
        改写文章
        
        Args:
            article_id: 文章ID
            style: 改写风格预设ID，如 tech_expert, business_analyst 等
            use_references: 是否引用灵感库相关内容
            custom_instructions: 额外定制指令
            inspiration_ids: 指定要作为参考的灵感库文章ID列表
        """
        article = self.storage.get_article(article_id)
        if not article:
            raise Exception("文章不存在")
        
        account = self.storage.get_account(article.account_id)
        
        # 确定改写风格
        if not style:
            style = article.rewrite_style or (account.pipeline_role if account else "tech_expert")
        
        # 获取参考文章
        reference_records = None
        if use_references:
            if inspiration_ids:
                # 使用指定的灵感库内容作为参考
                reference_records = []
                for insp_id in inspiration_ids[:5]:  # 最多5篇
                    insp = self.storage.get_inspiration(insp_id)
                    if insp:
                        reference_records.append({
                            "id": insp.id,
                            "title": insp.title,
                            "content": insp.content,
                            "source_url": insp.source_url
                        })
            else:
                # 自动从灵感库获取相关内容
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
            # 使用新的改写方法
            result = await self.ai.rewrite_with_context(
                content=article.original_content,
                style_preset=style,
                inspiration_records=reference_records if use_references else None
            )
            
            rewritten = result["content"]
            used_refs = result.get("used_references", [])
            
            # 更新文章
            self.storage.update_article(article_id, {
                "rewritten_html": rewritten,
                "status": ArticleStatus.REWRITTEN,
                "rewrite_style": style,
                "rewrite_references": used_refs,
                "custom_instructions": custom_instructions or "",
                "metadata": {
                    "used_inspiration_ids": inspiration_ids or [],
                    "reference_count": len(reference_records) if reference_records else 0
                }
            })
        except Exception as e:
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
        """
        发布文章
        
        Args:
            article_id: 文章ID
            template: 模板名称 (default, minimal, tech, business)
        """
        article = self.storage.get_article(article_id)
        if not article:
            raise Exception("文章不存在")
        
        account = self.storage.get_account(article.account_id)
        if not account or not account.wechat_appid:
            raise Exception("微信配置不完整")
        
        wechat = WechatService(account.wechat_appid, account.wechat_secret)
        self.storage.update_article(article_id, {"status": ArticleStatus.PUBLISHING})
        
        try:
            # 使用模板渲染内容
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
            
            # 保存使用的模板
            self.storage.update_article(article_id, {
                "wechat_draft_id": draft_id,
                "status": ArticleStatus.PUBLISHED,
                "published_at": datetime.now(),
                "metadata": {"template": template}
            })
        except Exception as e:
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
    
    async def process_pipeline(self, account_id: str, batch_size: int = 3):
        articles = self.storage.list_articles(
            account_id=account_id,
            status=ArticleStatus.PENDING,
            limit=batch_size
        )
        for article in articles:
            try:
                await self.rewrite_article(article.id)
                await self.publish_article(article.id)
            except Exception as e:
                print(f"处理失败 {article.id}: {e}")
    
    def get_stats(self, account_id: Optional[str] = None) -> Dict:
        return self.storage.get_stats(account_id)
