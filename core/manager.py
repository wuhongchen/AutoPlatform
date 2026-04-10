import os
import sys
import signal

# 兼容 OpenClaw 运行方式：确保能从项目根目录找到 modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from modules.collector import ContentCollector
from modules.processor import ContentProcessor
from modules.mp_processor import DeepMPProcessor
from modules.discovery import DiscoverProcessor, ContentSearchAgent
from modules.publisher import WeChatPublisher
from modules.models import MODEL_POOL, get_runtime_default_model_key
from modules.state_machine import PipelineState, canonical_pipeline_status, is_rewrite_stage, is_publish_stage
from modules.workflow_store import WorkflowStore
from config import Config

from modules.feishu import FeishuBitable
import time
import re


class PipelineTimeout:
    """流水线全局超时控制器"""
    def __init__(self, seconds=300):
        self.seconds = seconds
        self.original_handler = None

    def _timeout_handler(self, signum, frame):
        raise TimeoutError(f"Pipeline execution exceeded {self.seconds} seconds")

    def __enter__(self):
        try:
            self.original_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.seconds)
        except Exception:
            pass  # Windows doesn't support SIGALRM
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            signal.alarm(0)
            if self.original_handler:
                signal.signal(signal.SIGALRM, self.original_handler)
        except Exception:
            pass
        return False


def _now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class AutoPlatformManager:
    def __init__(self):
        self.account_id = (os.getenv("OPENCLAW_ACCOUNT_ID") or "default").strip() or "default"
        self.feishu = FeishuBitable(
            app_id=Config.FEISHU_APP_ID,
            app_secret=Config.FEISHU_APP_SECRET,
            app_token=Config.FEISHU_APP_TOKEN
        )
        self.workflow = WorkflowStore(Config.WORKFLOW_DB)
        self.processing_records = set()
        self.collector = ContentCollector()
        self.processor = ContentProcessor(volc_ak=Config.VOLCENGINE_AK, volc_sk=Config.VOLCENGINE_SK)
        self.mp_processor = DeepMPProcessor(feishu_client=self.feishu)
        self.search_agent = ContentSearchAgent(max_results=3)
        self.discovery_processor = DiscoverProcessor(self.mp_processor.client)
        self.publisher = WeChatPublisher(
            appid=Config.WECHAT_APPID, 
            secret=Config.WECHAT_SECRET,
            author=Config.WECHAT_AUTHOR
        )
        self.table_ids = {}
        self._refresh_table_cache()

    def _refresh_table_cache(self):
        """缓存灵感库表 ID，用于回写来源状态。"""
        tables = self.feishu.list_tables()
        if not tables:
            return

        def _pick_id(matchers):
            for t in tables:
                name = t.get("name", "")
                if any(m in name for m in matchers):
                    return t.get("table_id")
            return None

        self.table_ids["inspiration"] = _pick_id([Config.FEISHU_INSPIRATION_TABLE, "内容灵感库"])

    def _resolve_table_id(self, key, refresh=False):
        """按业务键获取表 ID，必要时自动刷新缓存。"""
        if refresh or not self.table_ids.get(key):
            self._refresh_table_cache()
        return self.table_ids.get(key)

    def _schema_stamp_path(self):
        out_dir = Config.OUTPUT_DIR or PROJECT_ROOT
        os.makedirs(out_dir, exist_ok=True)
        token_tag = re.sub(r"[^A-Za-z0-9_-]", "_", str(Config.FEISHU_APP_TOKEN or "default"))
        return os.path.join(out_dir, f".schema_checked_{token_tag}.stamp")

    def _should_run_schema_check(self):
        """减少 OpenClaw 定时调用时的重复建字段请求。"""
        if os.getenv("OPENCLAW_SCHEMA_CHECK_ENABLED", "1") != "1":
            return False

        try:
            interval = int(os.getenv("OPENCLAW_SCHEMA_CHECK_INTERVAL_SEC", "21600"))
        except Exception:
            interval = 21600

        if interval <= 0:
            return True

        stamp_path = self._schema_stamp_path()
        if not os.path.exists(stamp_path):
            return True

        try:
            with open(stamp_path, "r", encoding="utf-8") as f:
                last_ts = float((f.read() or "0").strip())
            return (time.time() - last_ts) >= interval
        except Exception:
            return True

    def _mark_schema_checked(self):
        try:
            with open(self._schema_stamp_path(), "w", encoding="utf-8") as f:
                f.write(str(time.time()))
        except Exception:
            pass

    def _field_to_text(self, field_val):
        """将飞书字段值统一转成可解析文本。"""
        if not field_val:
            return ""
        if isinstance(field_val, dict):
            return str(field_val.get('url', '') or field_val.get('link', '') or field_val.get('text', '')).strip()
        if isinstance(field_val, list) and len(field_val) > 0:
            first = field_val[0]
            if isinstance(first, dict):
                return str(first.get('url', '') or first.get('link', '') or first.get('text', '')).strip()
            return str(first).strip()
        return str(field_val).strip()

    def _extract_doc_token(self, *field_vals):
        """从多个字段里提取 docx token（优先 URL，再退化到纯 token 文本）。"""
        for field_val in field_vals:
            val_str = self._field_to_text(field_val)
            if not val_str:
                continue

            # 优先从标准 docx URL 中提取，避免标题里的英文串误判
            m_url = re.search(r'feishu\.cn/docx/([A-Za-z0-9]{27,})', val_str)
            if m_url:
                return m_url.group(1)

            # 兼容只保存 token 的场景
            if re.fullmatch(r'[A-Za-z0-9]{27,60}', val_str):
                return val_str
        return None

    def _resolve_publish_doc_token(self, fields):
        """
        发布阶段解析文档 token：
        1) 改后文档链接
        2) 备注
        3) 原文文档链接
        4) 原文文档
        返回: (token, normalized_url, source_field)
        """
        candidates = [
            ("rewritten_doc", fields.get("rewritten_doc") or fields.get("改后文档链接")),
            ("remark", fields.get("remark") or fields.get("备注")),
            ("source_doc_url", fields.get("source_doc_url") or fields.get("原文文档链接")),
            ("原文文档", fields.get("原文文档")),
        ]
        for source_field, value in candidates:
            token = self._extract_doc_token(value)
            if token:
                return token, f"https://www.feishu.cn/docx/{token}", source_field
        return None, "", ""

    def _update_pipeline_failure(self, record_id, status, reason):
        """失败状态回写到本地工作流。"""
        payload = {
            "status": status or PipelineState.FAILED,
            "remark": reason,
        }
        return self.workflow.update_pipeline(record_id, **payload)
    def _shorten_title_with_ai(self, title, max_bytes=60):
        """使用AI将标题精简到指定字节数以内"""
        from modules.ai_caller import get_unified_caller

        title_bytes = title.encode('utf-8')
        if len(title_bytes) <= max_bytes:
            return title

        ai_caller = get_unified_caller()
        messages = [
            {"role": "system", "content": "你是一个专业的标题编辑。请将给定标题精简得更短，保留核心信息，不超过20个汉字。只输出精简后的标题，不要解释。"},
            {"role": "user", "content": f"原标题：{title}\n\n请精简到20字以内："}
        ]

        try:
            result = ai_caller.call_with_fallback(messages, temperature=0.3, task_type="shorten_title")
            if result:
                shortened = result.strip().strip('"\'').strip()
                # 确保不超过字节限制
                if len(shortened.encode('utf-8')) > max_bytes:
                    # 直接截断
                    shortened = shortened[:20].strip()
                return shortened
        except Exception as e:
            print(f"   ⚠️ AI精简标题失败: {e}")

        # 兜底：直接截断
        return title[:20].strip() + "..." if len(title) > 20 else title

    def _validate_content_for_publish(self, article):
        """
        验证内容是否适合发布，标题过长时自动精简。
        返回: (is_valid, error_reason)
        """
        title = article.get('title', '') or ''
        content = article.get('content_html', '') or article.get('content', '') or ''
        content_raw = article.get('content_raw', '') or ''

        # 1. 检查标题
        if not title or title.strip() in ['', 'None', 'null', '未命名标题']:
            return False, "标题为空或无效"

        # 2. 检查标题长度（微信限制 64 字节），超长则自动精简
        title_bytes = title.encode('utf-8')
        if len(title_bytes) > 64:
            print(f"   ✂️ 标题超长（{len(title_bytes)} 字节），AI精简中...")
            original_title = title
            title = self._shorten_title_with_ai(title, max_bytes=60)
            article['title'] = title
            print(f"   ✅ 标题已精简: {original_title[:30]}... → {title}")
        
        # 3. 检查内容是否为空
        if not content or not content.strip():
            return False, "内容为空"
        
        # 4. 检查实质内容长度（去除 HTML 标签后）
        text_only = re.sub(r'<[^>]+>', '', content)
        text_only = text_only.strip()
        
        if len(text_only) < 100:
            return False, f"实质内容过少（{len(text_only)} 字，最少需要 100 字）"
        
        # 5. 检查是否有有效段落
        paragraphs = [p.strip() for p in text_only.split('\n') if p.strip()]
        if len(paragraphs) == 0:
            return False, "没有有效的段落内容"
        
        # 6. 检查内容是否抓取完整
        if content_raw and len(content_raw) < 50 and len(text_only) < 50:
            return False, "内容可能抓取不完整"
        
        return True, "内容检查通过"


    def _normalize_model_key(self, raw_key):
        """标准化 model_key，支持别名。"""
        key = self._field_to_text(raw_key).strip()
        if not key or key.lower() in {"auto", "default"}:
            key = get_runtime_default_model_key()
        if not key:
            return ""
        if key in MODEL_POOL:
            return key

        low = key.lower()
        if low in MODEL_POOL:
            return low

        alias = {
            "doubao": "volcengine",
            "volc": "volcengine",
            "ark": "volcengine",
            "qwen": "qwen3.5-plus",
            "bailian": "qwen3.5-plus",
            "kimi": "kimi-k2.5",
            "k2.5": "kimi-k2.5",
            "zhipu": "glm-5",
            "glm": "glm-5",
            "minimax": "MiniMax-M2.5",
            "m2.5": "MiniMax-M2.5",
            "openclawproxy": "openclaw",
            "openclaw_proxy": "openclaw",
        }
        mapped = alias.get(low, "")
        if mapped in MODEL_POOL:
            return mapped
        return ""

    def _resolve_pipeline_rewrite_config(self, fields):
        """流水线改写配置：本地记录优先，环境变量兜底。"""
        raw_role = (
            self._field_to_text(fields.get("role"))
            or self._field_to_text(fields.get("改写角色"))
            or os.getenv("OPENCLAW_PIPELINE_ROLE", "tech_expert")
        )
        role_key = (raw_role or "tech_expert").strip()
        if not role_key:
            role_key = "tech_expert"

        default_model = (os.getenv("OPENCLAW_PIPELINE_MODEL") or "").strip()
        if not default_model:
            default_model = get_runtime_default_model_key()
        model_key = self._normalize_model_key(fields.get("model") or fields.get("改写模型"))
        if not model_key:
            model_key = self._normalize_model_key(default_model)
        if not model_key:
            model_key = get_runtime_default_model_key()

        return role_key, model_key

    def _mark_inspiration_processed(self, source_record_id: str = "", source_url: str = ""):
        inbox_table_id = self._resolve_table_id("inspiration")
        if not inbox_table_id:
            return
        target_record_id = self._field_to_text(source_record_id)
        if target_record_id:
            self.feishu.update_record(inbox_table_id, target_record_id, {"处理状态": "已处理"})
            return
        if not source_url:
            return
        records = self.feishu.list_records(inbox_table_id).get('items', [])
        for record in records:
            fields = record.get('fields', {})
            if fields.get('文章 URL') == source_url or fields.get('原链接') == source_url:
                self.feishu.update_record(inbox_table_id, record['record_id'], {"处理状态": "已处理"})
                break

    def log_publish_result(self, data, pipeline_record=None):
        pipeline_record = pipeline_record or {}
        self.workflow.add_publish_log({
            "account_id": self.account_id,
            "pipeline_record_id": pipeline_record.get("record_id", ""),
            "title": data.get("title", ""),
            "publish_status": "已发布",
            "result": f"已同步至草稿箱 ID: {data.get('draft_id', '')}",
            "remark": pipeline_record.get("remark", ""),
            "url": data.get("url", "") or pipeline_record.get("url", ""),
            "rewritten_doc": pipeline_record.get("rewritten_doc", ""),
            "draft_id": data.get("draft_id", ""),
            "published_at": _now_str(),
            "extra": {
                "platform": "微信公众号",
                "owner": Config.WECHAT_AUTHOR or "System",
            },
        })
        self._mark_inspiration_processed(
            source_record_id=pipeline_record.get("source_record_id", ""),
            source_url=data.get("url", "") or pipeline_record.get("url", ""),
        )
        print("📊 已完成本地工作流与来源状态同步。")

    # --- 步骤 1: 内容抓取 ---
    def step_collect(self, url):
        print(f"\n📥 [步骤 1/3] 正在抓取内容: {url}")
        article_data = self.collector.fetch(url)
        if not article_data:
            print("❌ 抓取失败")
            return None
        char_count = len(article_data.get('content_raw', ''))
        img_count = len(article_data.get('images', []))
        print(f"   ✅ 抓取成功: {article_data['title']} ({char_count}字, {img_count}图)")
        article_data['url'] = url
        return article_data

    # --- 步骤 2: 内容改写 (AI 创作) ---
    def step_rewrite(self, article_data, role_key, model_key):
        print(f"\n🤖 [步骤 2/3] 正在进行 AI 角色改写 (模型: {model_key}, 角色: {role_key})")
        
        if role_key == "tech_expert" and model_key == "volcengine":
            # 升级版公众号深度专家模式 (MP-Deep-Pro)
            result = self.mp_processor.process(article_data['url'], article_data, publisher=self.publisher)
            
            content_len = len(result.get("full_content", ""))
            if content_len < 300:
                print(f"   ⚠️ [预警] AI 生成内容较短 ({content_len} 字)")
            else:
                print(f"   📊 [生成成功] 共 {content_len} 字。")

            return {
                "title": result.get("title", "公众号精选标题"),
                "content": result.get("full_content", ""),
                "digest": "深度重构的长文逻辑",
                "originality": 92
            }
        elif role_key == "tech_expert" and model_key != "volcengine":
            print("   ℹ️ 当前模型非 volcengine，自动切换为通用改写流程以兼容多模型。")
            
        rewritten = self.processor.rewrite(article_data, role_key=role_key, model_key=model_key)
        if not rewritten:
            print("❌ 改写失败")
            return None
        print(f"   ✅ 改写完成: {rewritten['title']}")
        return rewritten

    # --- 步骤 3: 内容发布 (微信 + 封面图) ---
    def step_publish(self, rewritten_data, original_images=[]):
        print(f"\n📤 [步骤 3/3] 正在同步至微信公众平台...")
        
        # A. 封面图生成（带容错）
        thumb_media_id = ""
        try:
            cover_path = self.processor.generate_cover(f"为文章 '{rewritten_data['title']}' 生成一张高质量封面图")
            if cover_path and os.path.exists(cover_path):
                thumb_media_id = self.publisher.upload_material(cover_path)
        except Exception as e:
            print(f"   ⚠️ 封面生成失败，尝试使用备用封面: {e}")
            
        if not thumb_media_id:
            fallback_url = (original_images[0] if original_images else None) or Config.DEFAULT_COVER_URL
            if fallback_url:
                print(f"   🖼️ 使用备用封面...")
                thumb_media_id = self.publisher.upload_from_url(fallback_url)

        if not thumb_media_id:
            raise Exception("封面图上传失败（即梦生图失败且备用封面也无法上传），终止发布以避免微信 40007 错误")
        
        # B. 处理正文图片与标题清洗
        content_html = rewritten_data['content']
        img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content_html)
        for src in set(img_urls):
            if src.startswith('feishu://'):
                img_bytes = self.feishu._download_image(src)
                if img_bytes:
                    wx_url = self.publisher.upload_article_image(img_bytes)
                    if wx_url:
                        content_html = content_html.replace(src, wx_url)
            elif src.startswith('local://wechat_ad_image'):
                ad_path = (Config.WECHAT_AD_IMAGE_PATH or "").strip()
                if ad_path and os.path.exists(ad_path):
                    try:
                        with open(ad_path, "rb") as f:
                            img_bytes = f.read()
                        wx_url = self.publisher.upload_article_image(img_bytes)
                        if wx_url:
                            content_html = content_html.replace(src, wx_url)
                        else:
                            print(f"   ⚠️ 广告图片上传失败，将保留原占位: {ad_path}")
                    except Exception as e:
                        print(f"   ⚠️ 读取广告图片失败: {e}")
                else:
                    print(f"   ⚠️ 未找到广告图片路径: {ad_path}")

        # 深度应用公众号排版（默认：huasheng wechat-default）
        try:
            from modules.huasheng_formatter import HuashengWeChatFormatter
            content_html = HuashengWeChatFormatter.deep_optimize_format(content_html)
            clean_title = HuashengWeChatFormatter.optimize_title(rewritten_data['title'])
        except Exception as e:
            print(f"   ⚠️ huasheng 默认排版失败，回退内置排版: {e}")
            from modules.mp_processor import WeChatFormatter
            content_html = WeChatFormatter.deep_optimize_format(content_html)
            clean_title = WeChatFormatter.optimize_title(rewritten_data['title'])
        
        draft_id = self.publisher.publish_draft(
            title=clean_title,
            content_html=content_html,
            digest=rewritten_data['digest'],
            thumb_media_id=thumb_media_id
        )
        
        if draft_id:
            print(f"   ✅ 微信同步成功! 草稿 ID: {draft_id}")
        return draft_id

    def run_pipeline_step_1(self, record_id, fields):
        """环节 1: AI 改写"""
        force_rewrite = os.getenv("OPENCLAW_FORCE_REWRITE", "0") == "1"

        # 去重保护：如果已经有可读取的改后文档，则直接复用，避免重复调用模型
        if not force_rewrite:
            existing_token = self._extract_doc_token(fields.get("rewritten_doc"), fields.get("remark"))
            if existing_token:
                existing_meta = self.feishu.get_docx_meta(existing_token)
                if existing_meta:
                    normalized_url = f"https://www.feishu.cn/docx/{existing_meta['document_id']}"
                    self.workflow.update_pipeline(
                        record_id,
                        status=PipelineState.REVIEW_READY,
                        rewritten_doc=normalized_url,
                        remark=f"检测到已有改后稿，已跳过重复改写：{normalized_url}",
                    )
                    print(f"   ♻️ 检测到已有可用改后稿，跳过重复改写: {normalized_url}")
                    return

        doc_link = fields.get("source_doc_url") or fields.get("原文文档")
        url = fields.get("url")
        
        article_data = None
        doc_token = self._extract_doc_token(doc_link)
        if doc_token:
            article_data = self.feishu.get_docx_content(doc_token)
            if article_data:
                article_data['url'] = url
        
        if not article_data and url:
            article_data = self.step_collect(url)
            
        if not article_data:
            raise Exception("无法获取原文内容（原文文档读取与URL抓取均失败）")

        role_key, model_key = self._resolve_pipeline_rewrite_config(fields)
        print(f"   🧠 [流水线配置] role={role_key}, model={model_key}")
        
        # 保存原文内容到本地
        self.workflow.save_article_content(
            record_id=record_id,
            account_id=self.account_id,
            original_html=article_data.get('content', ''),
            original_text=article_data.get('content_raw', ''),
            original_data=article_data,
            images=article_data.get('images', [])
        )
        
        rewritten = self.step_rewrite(article_data, role_key=role_key, model_key=model_key)
        if not rewritten:
            raise Exception("AI 改写返回空结果")
        
        # 保存改写后内容到本地
        self.workflow.save_article_content(
            record_id=record_id,
            account_id=self.account_id,
            original_html=article_data.get('content', ''),
            original_text=article_data.get('content_raw', ''),
            original_data=article_data,
            rewritten_html=rewritten.get('content', ''),
            rewritten_text=rewritten.get('content', ''),
            rewritten_data=rewritten,
            images=article_data.get('images', [])
        )

        new_doc_id, new_doc_url = self.feishu.create_docx(title=f"【AI改后稿】{rewritten['title']}")
        if not new_doc_id or not new_doc_url:
            raise Exception("AI 改写文档创建失败，未获取到有效文档链接")

        self.feishu.set_tenant_manageable(new_doc_id)
        admin_id = os.getenv("FEISHU_ADMIN_USER_ID")
        if admin_id:
            self.feishu.add_collaborator(new_doc_id, admin_id, "full_access")
        blocks, _ = self.feishu.html_to_docx_blocks(rewritten['content'], new_doc_id)
        if blocks and not self.feishu.append_docx_blocks(new_doc_id, blocks):
            raise Exception("AI 改写文档写入失败")

        doc_token = self._extract_doc_token(new_doc_url)
        if not doc_token:
            raise Exception(f"AI 改写文档链接无效: {new_doc_url}")

        normalized_url = f"https://www.feishu.cn/docx/{doc_token}"

        updated = self.workflow.update_pipeline(
            record_id,
            status=PipelineState.REVIEW_READY,
            remark=f"AI 已生成草稿：{normalized_url}（模型: {model_key}）",
            model=model_key,
            role=role_key,
            rewritten_doc=normalized_url,
            title=rewritten.get("title") or fields.get("title") or "",
            updated_at=_now_str(),
        )
        if not updated:
            raise Exception("改写结果回写本地工作流失败")

    def run_pipeline_step_2(self, record_id, fields):
        """环节 2: 确认发布"""
        # 优先使用改后文档；缺失时回退原文文档字段，避免因历史回填缺失导致发布失败
        doc_token, normalized_url, source_field = self._resolve_publish_doc_token(fields)
        if not doc_token:
            raise Exception("无法从‘改后文档链接/备注/原文文档链接’中解析有效 Feishu Doc Token")

        # 自动自愈：若 token 来自回退字段，补齐改后文档链接，便于后续发布流程稳定运行
        if source_field != "rewritten_doc":
            old_remark = self._field_to_text(fields.get("remark"))
            marker = "[AutoBackfill]"
            repair_note = f"{marker} 发布阶段已从“{source_field}”回填改后文档链接：{normalized_url}"
            if marker in old_remark:
                new_remark = old_remark
            else:
                new_remark = f"{old_remark} {repair_note}".strip()
            self.workflow.update_pipeline(record_id, rewritten_doc=normalized_url, remark=new_remark, updated_at=_now_str())

        final_article = self.feishu.get_docx_content(doc_token)
        if not final_article:
            raise Exception(f"读取确认稿失败（token={doc_token}）")
        
        # 发布前内容完整性检查
        is_valid, error_reason = self._validate_content_for_publish(final_article)
        if not is_valid:
            raise Exception(f"内容检查未通过: {error_reason}")
        
        clean_title = re.sub(r'^【AI改后稿】\s*', '', final_article['title'])
        clean_title = re.sub(r'^[标题|Title][:：]\s*', '', clean_title)
        clean_title = re.sub(r'^#+\s*', '', clean_title).strip()

        digest_clean = final_article['content_raw'].replace('\n', ' ').strip()
        draft_id = self.step_publish({
            "title": clean_title,
            "content": final_article['content_html'],
            "digest": digest_clean[:54] + "..." if len(digest_clean) > 54 else digest_clean
        }, original_images=[])

        if not draft_id:
            raise Exception("微信草稿创建失败（未返回 draft_id）")

        if draft_id:
            updated = self.workflow.update_pipeline(
                record_id,
                title=clean_title,
                draft_id=draft_id,
                status=PipelineState.PUBLISHED,
                remark=f"已同步至草稿箱 ID: {draft_id}",
                published_at=_now_str(),
                updated_at=_now_str(),
            )
            self.log_publish_result({
                "url": fields.get("url", ""),
                "title": clean_title,
                "draft_id": draft_id
            }, pipeline_record=updated or fields)

    def run_with_params(self, url, role_key="tech_expert", model_key="auto"):
        """手动运行单篇文章的全流程"""
        resolved_model = self._normalize_model_key(model_key) or get_runtime_default_model_key()

        # 创建采集任务
        collect_task_id = self.workflow.create_plugin_task(
            record_id="manual", account_id=self.account_id,
            plugin_type="collect", params={"url": url}
        )

        pipeline_record = self.workflow.create_pipeline({
            "account_id": self.account_id,
            "source_type": "manual",
            "title": "手动任务",
            "url": url,
            "status": PipelineState.REWRITE_RUNNING,
            "role": role_key,
            "model": resolved_model,
            "remark": "手动创建任务，开始抓取原文。",
            "owner": Config.WECHAT_AUTHOR or "System",
            "created_at": _now_str(),
            "updated_at": _now_str(),
        })
        # 1. 采集
        self.workflow.update_plugin_task(collect_task_id, status="running")
        article_data = self.step_collect(url)
        if not article_data:
            self.workflow.update_plugin_task(collect_task_id, status="failed", error_msg="采集流程中断")
            self._update_pipeline_failure(pipeline_record["record_id"], PipelineState.REWRITE_FAILED, "采集流程中断。")
            print("❌ 采集流程中断。")
            return
        self.workflow.update_plugin_task(collect_task_id, status="success", result={"title": article_data.get("title"), "char_count": len(article_data.get('content_raw', ''))})
        
        # 保存原文内容到本地
        self.workflow.save_article_content(
            record_id=pipeline_record["record_id"],
            account_id=self.account_id,
            original_html=article_data.get('content', ''),
            original_text=article_data.get('content_raw', ''),
            original_data=article_data,
            images=article_data.get('images', [])
        )
        
        # 2. 改写
        rewrite_task_id = self.workflow.create_plugin_task(
            record_id=pipeline_record["record_id"], account_id=self.account_id,
            plugin_type="ai_rewrite", params={"role": role_key, "model": resolved_model}
        )
        self.workflow.update_plugin_task(rewrite_task_id, status="running")

        self.workflow.update_pipeline(
            pipeline_record["record_id"],
            title=article_data.get("title") or "未命名标题",
            remark="原文采集完成，开始改写。",
            updated_at=_now_str(),
        )
        rewritten = self.step_rewrite(article_data, role_key, resolved_model)
        if not rewritten:
            self.workflow.update_plugin_task(rewrite_task_id, status="failed", error_msg="AI 改写失败")
            self._update_pipeline_failure(pipeline_record["record_id"], PipelineState.REWRITE_FAILED, "AI 改写流程中断。")
            print("❌ AI 改写流程中断。")
            return
        self.workflow.update_plugin_task(rewrite_task_id, status="success", result={"title": rewritten.get("title"), "originality": rewritten.get("originality", 0)})
        
        # 保存改写后内容到本地
        self.workflow.save_article_content(
            record_id=pipeline_record["record_id"],
            account_id=self.account_id,
            original_html=article_data.get('content', ''),
            original_text=article_data.get('content_raw', ''),
            original_data=article_data,
            rewritten_html=rewritten.get('content', ''),
            rewritten_text=rewritten.get('content', ''),
            rewritten_data=rewritten,
            images=article_data.get('images', [])
        )

        new_doc_id, new_doc_url = self.feishu.create_docx(title=f"【AI改后稿】{rewritten['title']}")
        if not new_doc_id or not new_doc_url:
            self._update_pipeline_failure(pipeline_record["record_id"], PipelineState.REWRITE_FAILED, "AI 改写文档创建失败。")
            print("❌ AI 改写文档创建失败。")
            return

        self.feishu.set_tenant_manageable(new_doc_id)
        admin_id = os.getenv("FEISHU_ADMIN_USER_ID")
        if admin_id:
            self.feishu.add_collaborator(new_doc_id, admin_id, "full_access")
        blocks, _ = self.feishu.html_to_docx_blocks(rewritten['content'], new_doc_id)
        if blocks and not self.feishu.append_docx_blocks(new_doc_id, blocks):
            self._update_pipeline_failure(pipeline_record["record_id"], PipelineState.REWRITE_FAILED, "AI 改写文档写入失败。")
            print("❌ AI 改写文档写入失败。")
            return

        doc_token = self._extract_doc_token(new_doc_url)
        if not doc_token:
            self._update_pipeline_failure(pipeline_record["record_id"], PipelineState.REWRITE_FAILED, "AI 改写文档链接无效。")
            print("❌ AI 改写文档链接无效。")
            return

        normalized_url = f"https://www.feishu.cn/docx/{doc_token}"
        pipeline_record = self.workflow.update_pipeline(
            pipeline_record["record_id"],
            title=rewritten.get("title") or article_data.get("title") or "未命名标题",
            rewritten_doc=normalized_url,
            status=PipelineState.PUBLISH_RUNNING,
            remark=f"AI 已生成草稿：{normalized_url}（模型: {resolved_model}），开始发布。",
            role=role_key,
            model=resolved_model,
            updated_at=_now_str(),
        ) or pipeline_record

        # 3. 发布
        publish_task_id = self.workflow.create_plugin_task(
            record_id=pipeline_record["record_id"], account_id=self.account_id,
            plugin_type="publish", params={"title": rewritten.get("title")}
        )
        self.workflow.update_plugin_task(publish_task_id, status="running")

        draft_id = self.step_publish(rewritten, article_data.get('images', []))
        
        if draft_id:
            self.workflow.update_plugin_task(publish_task_id, status="success", result={"draft_id": draft_id})
            pipeline_record = self.workflow.update_pipeline(
                pipeline_record["record_id"],
                draft_id=draft_id,
                status=PipelineState.PUBLISHED,
                remark=f"已同步至草稿箱 ID: {draft_id}",
                published_at=_now_str(),
                updated_at=_now_str(),
            ) or pipeline_record
            print(f"\n✨ 手动任务执行成功！草稿 ID: {draft_id}")
            self.log_publish_result({
                "url": url,
                "title": rewritten['title'],
                "draft_id": draft_id
            }, pipeline_record=pipeline_record)
        else:
            self.workflow.update_plugin_task(publish_task_id, status="failed", error_msg="微信发布失败")
            self._update_pipeline_failure(pipeline_record["record_id"], PipelineState.PUBLISH_FAILED, "微信发布流程中断。")
            print("❌ 微信发布流程中断。")

    def run_pipeline_once(self):
        """执行单次全流水线巡检（带全局5分钟超时保护）"""
        try:
            batch_size = int(os.getenv("OPENCLAW_PIPELINE_BATCH_SIZE", "3"))
        except Exception:
            batch_size = 3

        records = self.workflow.list_pipeline_pending(
            self.account_id,
            [
                PipelineState.QUEUED_REWRITE,
                PipelineState.REWRITE_RUNNING,
                PipelineState.PUBLISH_READY,
                PipelineState.PUBLISH_RUNNING,
            ],
            batch_size,
        )
        if not records:
            print("😴 本地写作链暂无待处理任务。")
            return

        handled = 0
        for fields in records:
            status = canonical_pipeline_status(fields.get('status', ''))
            record_id = fields.get('record_id')
            if record_id in self.processing_records:
                continue

            if is_rewrite_stage(status):
                print(f"🚀 开始改写: {fields.get('title')}")
                try:
                    with PipelineTimeout(seconds=300):  # 5分钟超时保护
                        self.workflow.update_pipeline(record_id, status=PipelineState.REWRITE_RUNNING, updated_at=_now_str())
                        self.processing_records.add(record_id)
                        self.run_pipeline_step_1(record_id, fields)
                except TimeoutError as e:
                    print(f"⏱️ 改写超时: {e}")
                    self._update_pipeline_failure(
                        record_id,
                        PipelineState.REWRITE_FAILED,
                        f"AI 改写超时（超过5分钟），请检查网络或模型可用性"
                    )
                except Exception as e:
                    print(f"❌ 改写步骤异常: {e}")
                    self._update_pipeline_failure(
                        record_id,
                        PipelineState.REWRITE_FAILED,
                        f"AI 改写或排版失败，原因: {str(e)}"
                    )
                finally:
                    if record_id in self.processing_records:
                        self.processing_records.remove(record_id)
                handled += 1

            elif is_publish_stage(status):
                print(f"📤 开始发布: {fields.get('title')}")
                try:
                    with PipelineTimeout(seconds=120):  # 2分钟超时保护
                        self.workflow.update_pipeline(record_id, status=PipelineState.PUBLISH_RUNNING, updated_at=_now_str())
                        self.processing_records.add(record_id)
                        self.run_pipeline_step_2(record_id, fields)
                except TimeoutError as e:
                    print(f"⏱️ 发布超时: {e}")
                    self._update_pipeline_failure(
                        record_id,
                        PipelineState.PUBLISH_FAILED,
                        f"发布操作超时（超过2分钟）"
                    )
                except Exception as e:
                    print(f"❌ 发布步骤异常: {e}")
                    self._update_pipeline_failure(
                        record_id,
                        PipelineState.PUBLISH_FAILED,
                        f"推送到微信失败，原因: {str(e)}"
                    )
                finally:
                    if record_id in self.processing_records:
                        self.processing_records.remove(record_id)
                handled += 1

            if batch_size > 0 and handled >= batch_size:
                print(f"⏸️ 已达到本轮批处理上限({batch_size})，等待下次巡检继续。")
                break

    def start_pipeline_loop(self, interval=30):
        print(f"🕵️ [流水线] 监听中...")
        while True:
            try:
                self.run_pipeline_once()
            except Exception as e: print(f"❌ 循环异常: {e}")
            time.sleep(interval)

    def publish_from_inspiration(self, record_id, title):
        """从灵感库发布文章到微信"""
        from modules.article_state import ArticleState
        
        print(f"📤 开始发布记录: {record_id}")
        
        # 获取文章内容
        content = self.workflow.get_article_content(record_id, self.account_id)
        if not content:
            print(f"❌ 文章内容不存在: {record_id}")
            return False
        
        # 获取改写后的内容
        rewritten_data = {
            "title": title or content.get("rewritten_data", {}).get("title", "未命名"),
            "content": content.get("rewritten_html", content.get("original_html", "")),
            "digest": content.get("rewritten_data", {}).get("digest", "")[:54] + "..." if len(content.get("rewritten_data", {}).get("digest", "")) > 54 else content.get("rewritten_data", {}).get("digest", "")
        }
        
        # 执行发布
        try:
            draft_id = self.step_publish(rewritten_data, content.get("images", []))
            if draft_id:
                print(f"✅ 发布成功，草稿ID: {draft_id}")
                # 更新灵感库状态
                self.workflow.upsert_inspiration({
                    "record_id": record_id,
                    "account_id": self.account_id,
                    "status": ArticleState.PUBLISHED,
                    "remark": f"已发布到微信，草稿ID: {draft_id}",
                })
                return True
            else:
                print("❌ 发布失败")
                return False
        except Exception as e:
            print(f"❌ 发布异常: {e}")
            return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoInfo Platform Manager")
    parser.add_argument("cmd", help="命令: pipeline, pipeline-once, publish, 或文章URL")
    parser.add_argument("role", nargs="?", default=os.getenv("OPENCLAW_ROLE", "tech_expert"), help="角色")
    parser.add_argument("model", nargs="?", default=os.getenv("OPENCLAW_MODEL", "auto"), help="模型")
    parser.add_argument("--account-id", dest="account_id", default=os.getenv("OPENCLAW_ACCOUNT_ID", "default"), help="账户ID")
    parser.add_argument("--record-id", dest="record_id", default=None, help="记录ID（用于发布）")
    parser.add_argument("--title", dest="title", default=None, help="文章标题（用于发布）")
    
    args = parser.parse_args()
    
    # 设置环境变量供 AutoPlatformManager 读取
    os.environ["OPENCLAW_ACCOUNT_ID"] = args.account_id
    
    manager = AutoPlatformManager()
    
    if args.cmd == "pipeline":
        manager.start_pipeline_loop()
    elif args.cmd == "pipeline-once":
        manager.run_pipeline_once()
    elif args.cmd == "publish":
        # 发布模式
        if args.record_id and args.title:
            success = manager.publish_from_inspiration(args.record_id, args.title)
            sys.exit(0 if success else 1)
        else:
            print("❌ 发布模式需要 --record-id 和 --title 参数")
            sys.exit(1)
    else:
        # 单篇模式参数优先级：CLI > OPENCLAW_* 环境变量 > 默认值
        manager.run_with_params(args.cmd, args.role, args.model)
