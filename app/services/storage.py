"""
存储服务
提供统一的数据持久化接口
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar
from contextlib import contextmanager

from app.config import get_settings
from app.models import (
    Account,
    Article,
    PipelineRecord,
    InspirationRecord,
    StylePreset,
    Task,
    TaskStatus,
    ImageAsset,
)

T = TypeVar("T")


class StorageService:
    """SQLite存储服务"""
    
    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        self.db_path = db_path or str(settings.data_dir / "db" / "autoplatform.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_tables(self):
        """初始化表结构"""
        with self._get_connection() as conn:
            # 账户表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    account_id TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'active',
                    wechat_appid TEXT DEFAULT '',
                    wechat_secret TEXT DEFAULT '',
                    wechat_author TEXT DEFAULT 'W 小龙虾',
                    ad_header_html TEXT DEFAULT '',
                    ad_footer_html TEXT DEFAULT '',
                    pipeline_role TEXT DEFAULT 'tech_expert',
                    pipeline_model TEXT DEFAULT 'auto',
                    pipeline_batch_size INTEGER DEFAULT 3,
                    content_direction TEXT DEFAULT '',
                    prompt_direction TEXT DEFAULT '',
                    wechat_prompt_direction TEXT DEFAULT '',
                    last_run_at TEXT,
                    run_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 文章表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    source_url TEXT NOT NULL,
                    source_title TEXT DEFAULT '',
                    source_author TEXT DEFAULT '',
                    original_content TEXT DEFAULT '',
                    original_html TEXT DEFAULT '',
                    rewritten_content TEXT DEFAULT '',
                    rewritten_html TEXT DEFAULT '',
                    images TEXT DEFAULT '[]',
                    cover_image TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    ai_score REAL,
                    ai_reason TEXT DEFAULT '',
                    ai_direction TEXT DEFAULT '',
                    wechat_draft_id TEXT DEFAULT '',
                    published_at TEXT,
                    published_url TEXT DEFAULT '',
                    account_id TEXT NOT NULL,
                    pipeline_id TEXT,
                    metadata TEXT DEFAULT '{}',
                    error_message TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 流水线表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_records (
                    id TEXT PRIMARY KEY,
                    article_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    status TEXT DEFAULT '🧲 待改写',
                    role TEXT DEFAULT 'tech_expert',
                    model TEXT DEFAULT 'auto',
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT DEFAULT '{}',
                    error_message TEXT DEFAULT '',
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    reviewer TEXT DEFAULT '',
                    review_note TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 灵感库表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inspiration_records (
                    id TEXT PRIMARY KEY,
                    source_url TEXT NOT NULL,
                    source_type TEXT DEFAULT 'wechat',
                    source_account TEXT DEFAULT '',
                    title TEXT DEFAULT '',
                    author TEXT DEFAULT '',
                    summary TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    content_html TEXT DEFAULT '',
                    images TEXT DEFAULT '[]',
                    read_count INTEGER,
                    like_count INTEGER,
                    ai_score REAL,
                    ai_reason TEXT DEFAULT '',
                    ai_direction TEXT DEFAULT '',
                    ai_insight TEXT DEFAULT '',
                    status TEXT DEFAULT '待分析',
                    account_id TEXT NOT NULL,
                    article_id TEXT,
                    collected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    analyzed_at TEXT,
                    metadata TEXT DEFAULT '{}',
                    error_message TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 任务表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    payload TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    result TEXT DEFAULT '{}',
                    error_message TEXT DEFAULT '',
                    account_id TEXT DEFAULT '',
                    target_id TEXT DEFAULT '',
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 图片素材表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS image_assets (
                    id TEXT PRIMARY KEY,
                    title TEXT DEFAULT '',
                    prompt TEXT DEFAULT '',
                    source_type TEXT DEFAULT 'upload',
                    image_url TEXT NOT NULL,
                    file_path TEXT DEFAULT '',
                    mime_type TEXT DEFAULT '',
                    account_id TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("PRAGMA journal_mode=WAL;")
            
            # 风格预设表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS style_presets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    system_prompt TEXT NOT NULL,
                    tone TEXT DEFAULT 'professional',
                    style TEXT DEFAULT 'analytical',
                    temperature REAL DEFAULT 0.7,
                    max_tokens INTEGER DEFAULT 4000,
                    is_builtin INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    params TEXT DEFAULT '{}',
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self._ensure_articles_schema(conn)
            self._ensure_accounts_schema(conn)

    def _ensure_accounts_schema(self, conn: sqlite3.Connection):
        """向后兼容：为历史数据库补齐账户字段"""
        rows = conn.execute("PRAGMA table_info(accounts)").fetchall()
        existing_columns = {row["name"] for row in rows}
        required_columns = {
            "wechat_author": "TEXT DEFAULT 'W 小龙虾'",
            "ad_header_html": "TEXT DEFAULT ''",
            "ad_footer_html": "TEXT DEFAULT ''",
        }
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(f"ALTER TABLE accounts ADD COLUMN {column_name} {column_type}")

    def _ensure_articles_schema(self, conn: sqlite3.Connection):
        """向后兼容：为历史数据库补齐新版本文章字段"""
        rows = conn.execute("PRAGMA table_info(articles)").fetchall()
        existing_columns = {row["name"] for row in rows}
        required_columns = {
            "rewrite_style": "TEXT DEFAULT 'tech_expert'",
            "rewrite_references": "TEXT DEFAULT '[]'",
            "custom_instructions": "TEXT DEFAULT ''",
        }
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(f"ALTER TABLE articles ADD COLUMN {column_name} {column_type}")
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """行转字典"""
        result = {}
        for key in row.keys():
            value = row[key]
            # 解析JSON字段
            if key in ["metadata", "images", "result", "params", "rewrite_references", "payload"] and isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = {} if key not in ["images", "rewrite_references"] else []
            result[key] = value
        return result
    
    # 账户操作
    def create_account(self, account: Account) -> Account:
        """创建账户"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO accounts (id, name, account_id, status, wechat_appid, 
                    wechat_secret, wechat_author, ad_header_html, ad_footer_html,
                    pipeline_role, pipeline_model,
                    pipeline_batch_size, content_direction, prompt_direction,
                    wechat_prompt_direction, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account.id or account.account_id,
                    account.name,
                    account.account_id,
                    account.status.value,
                    account.wechat_appid,
                    account.wechat_secret,
                    account.wechat_author,
                    account.ad_header_html,
                    account.ad_footer_html,
                    account.pipeline_role,
                    account.pipeline_model,
                    account.pipeline_batch_size,
                    account.content_direction,
                    account.prompt_direction,
                    account.wechat_prompt_direction,
                    json.dumps(account.metadata),
                )
            )
        return account
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM accounts WHERE account_id = ?",
                (account_id,)
            ).fetchone()
            if row:
                return Account.model_validate(self._row_to_dict(row))
            return None
    
    def list_accounts(self) -> List[Account]:
        """列出所有账户"""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM accounts ORDER BY created_at DESC").fetchall()
            return [Account.model_validate(self._row_to_dict(row)) for row in rows]
    
    def update_account(self, account_id: str, data: Dict[str, Any]) -> bool:
        """更新账户"""
        # 过滤掉未显式传入的键（值为None视为未设置），但允许空字符串/0/False
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return False
        
        # 处理特殊字段
        if "metadata" in data and isinstance(data["metadata"], dict):
            data["metadata"] = json.dumps(data["metadata"])
        
        data["updated_at"] = datetime.now().isoformat()
        
        fields = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [account_id]
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE accounts SET {fields} WHERE account_id = ?",
                values
            )
            return cursor.rowcount > 0
    
    def delete_account(self, account_id: str) -> bool:
        """删除账户"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM accounts WHERE account_id = ?",
                (account_id,)
            )
            return cursor.rowcount > 0
    
    # 文章操作
    def create_article(self, article: Article) -> Article:
        """创建文章"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO articles (id, source_url, source_title, source_author,
                    original_content, original_html, rewritten_content, rewritten_html,
                    images, cover_image, status, ai_score, ai_reason, ai_direction,
                    rewrite_style, rewrite_references, custom_instructions,
                    wechat_draft_id, published_at, published_url, account_id,
                    pipeline_id, metadata, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.id,
                    article.source_url,
                    article.source_title,
                    article.source_author,
                    article.original_content,
                    article.original_html,
                    article.rewritten_content,
                    article.rewritten_html,
                    json.dumps(article.images),
                    article.cover_image,
                    article.status.value,
                    article.ai_score,
                    article.ai_reason,
                    article.ai_direction,
                    article.rewrite_style,
                    json.dumps(article.rewrite_references),
                    article.custom_instructions,
                    article.wechat_draft_id,
                    article.published_at.isoformat() if article.published_at else None,
                    article.published_url,
                    article.account_id,
                    article.pipeline_id,
                    json.dumps(article.metadata),
                    article.error_message,
                )
            )
        return article
    
    def get_article(self, article_id: str) -> Optional[Article]:
        """获取文章"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM articles WHERE id = ?",
                (article_id,)
            ).fetchone()
            if row:
                return Article.model_validate(self._row_to_dict(row))
            return None
    
    def list_articles(self, account_id: Optional[str] = None, 
                     status: Optional[str] = None,
                     limit: int = 100) -> List[Article]:
        """列出文章"""
        query = "SELECT * FROM articles WHERE 1=1"
        params = []
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Article.model_validate(self._row_to_dict(row)) for row in rows]
    
    def update_article(self, article_id: str, data: Dict[str, Any]) -> bool:
        """更新文章"""
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return False
        
        if "metadata" in data and isinstance(data["metadata"], dict):
            data["metadata"] = json.dumps(data["metadata"])
        if "images" in data and isinstance(data["images"], list):
            data["images"] = json.dumps(data["images"])
        if "rewrite_references" in data and isinstance(data["rewrite_references"], list):
            data["rewrite_references"] = json.dumps(data["rewrite_references"])
        
        data["updated_at"] = datetime.now().isoformat()
        
        fields = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [article_id]
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE articles SET {fields} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    # 图片素材操作
    def create_image_asset(self, asset: ImageAsset) -> ImageAsset:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO image_assets (
                    id, title, prompt, source_type, image_url, file_path,
                    mime_type, account_id, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.id,
                    asset.title,
                    asset.prompt,
                    asset.source_type.value if hasattr(asset.source_type, "value") else asset.source_type,
                    asset.image_url,
                    asset.file_path,
                    asset.mime_type,
                    asset.account_id,
                    json.dumps(asset.metadata),
                ),
            )
        return asset

    def get_image_asset(self, asset_id: str) -> Optional[ImageAsset]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM image_assets WHERE id = ?",
                (asset_id,),
            ).fetchone()
            if row:
                return ImageAsset.model_validate(self._row_to_dict(row))
            return None

    def list_image_assets(self, account_id: Optional[str] = None, limit: int = 100) -> List[ImageAsset]:
        query = "SELECT * FROM image_assets WHERE 1=1"
        params = []
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [ImageAsset.model_validate(self._row_to_dict(row)) for row in rows]

    def delete_image_asset(self, asset_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM image_assets WHERE id = ?",
                (asset_id,),
            )
            return cursor.rowcount > 0
    
    # 流水线操作
    def create_pipeline_record(self, record: PipelineRecord) -> PipelineRecord:
        """创建流水线记录"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_records (id, article_id, account_id, status,
                    role, model, result, max_retries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.article_id,
                    record.account_id,
                    record.status.value,
                    record.role,
                    record.model,
                    json.dumps(record.result),
                    record.max_retries,
                )
            )
        return record
    
    def get_pipeline_record(self, record_id: str) -> Optional[PipelineRecord]:
        """获取流水线记录"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM pipeline_records WHERE id = ?",
                (record_id,)
            ).fetchone()
            if row:
                return PipelineRecord.model_validate(self._row_to_dict(row))
            return None
    
    def list_pipeline_records(self, account_id: Optional[str] = None,
                             status: Optional[str] = None,
                             limit: int = 100) -> List[PipelineRecord]:
        """列出流水线记录"""
        query = "SELECT * FROM pipeline_records WHERE 1=1"
        params = []
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [PipelineRecord.model_validate(self._row_to_dict(row)) for row in rows]
    
    # 灵感库操作
    def create_inspiration(self, record: InspirationRecord) -> InspirationRecord:
        """创建灵感记录"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO inspiration_records (id, source_url, source_type,
                    source_account, title, author, summary, content, content_html,
                    images, read_count, like_count, ai_score, ai_reason,
                    ai_direction, ai_insight, status, account_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.source_url,
                    record.source_type,
                    record.source_account,
                    record.title,
                    record.author,
                    record.summary,
                    record.content,
                    record.content_html,
                    json.dumps(record.images),
                    record.read_count,
                    record.like_count,
                    record.ai_score,
                    record.ai_reason,
                    record.ai_direction,
                    record.ai_insight,
                    record.status.value,
                    record.account_id,
                    json.dumps(record.metadata),
                )
            )
        return record
    
    def get_inspiration(self, record_id: str) -> Optional[InspirationRecord]:
        """获取灵感记录"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM inspiration_records WHERE id = ?",
                (record_id,)
            ).fetchone()
            if row:
                return InspirationRecord.model_validate(self._row_to_dict(row))
            return None
    
    def list_inspirations(self, account_id: Optional[str] = None,
                         status: Optional[str] = None,
                         limit: int = 100) -> List[InspirationRecord]:
        """列出灵感记录"""
        query = "SELECT * FROM inspiration_records WHERE 1=1"
        params = []
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [InspirationRecord.model_validate(self._row_to_dict(row)) for row in rows]

    def update_inspiration(self, record_id: str, data: Dict[str, Any]) -> bool:
        """更新灵感记录"""
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return False

        if "metadata" in data and isinstance(data["metadata"], dict):
            data["metadata"] = json.dumps(data["metadata"])
        if "images" in data and isinstance(data["images"], list):
            data["images"] = json.dumps(data["images"])

        data["updated_at"] = datetime.now().isoformat()

        fields = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [record_id]

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE inspiration_records SET {fields} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0
    
    # 统计信息
    def get_stats(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计数据"""
        article_statuses = [
            "pending", "rewriting", "rewritten",
            "publishing", "published", "failed",
        ]
        task_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        inspiration_statuses = ["待采集", "已采集"]

        with self._get_connection() as conn:
            stats = {
                "articles": {status: 0 for status in article_statuses},
                "tasks": {status: 0 for status in task_statuses},
                "inspiration": {status: 0 for status in inspiration_statuses},
            }
            
            # 文章统计
            query = "SELECT status, COUNT(*) as count FROM articles"
            params = []
            if account_id:
                query += " WHERE account_id = ?"
                params.append(account_id)
            query += " GROUP BY status"
            
            rows = conn.execute(query, params).fetchall()
            for row in rows:
                stats["articles"][row["status"]] = row["count"]
            
            # 任务统计
            query = "SELECT status, COUNT(*) as count FROM tasks"
            params = []
            if account_id:
                query += " WHERE account_id = ?"
                params.append(account_id)
            query += " GROUP BY status"
            
            rows = conn.execute(query, params).fetchall()
            for row in rows:
                stats["tasks"][row["status"]] = row["count"]
            
            # 灵感库统计
            query = "SELECT status, COUNT(*) as count FROM inspiration_records"
            params = []
            if account_id:
                query += " WHERE account_id = ?"
                params.append(account_id)
            query += " GROUP BY status"
            
            rows = conn.execute(query, params).fetchall()
            for row in rows:
                stats["inspiration"][row["status"]] = row["count"]
            
            return stats

    
    # 风格预设操作
    def create_style_preset(self, preset: StylePreset) -> StylePreset:
        """创建风格预设"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO style_presets (id, name, description, system_prompt,
                    tone, style, temperature, max_tokens, is_builtin, is_active,
                    params, usage_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preset.id,
                    preset.name,
                    preset.description,
                    preset.system_prompt,
                    preset.tone.value,
                    preset.style.value,
                    preset.temperature,
                    preset.max_tokens,
                    1 if preset.is_builtin else 0,
                    1 if preset.is_active else 0,
                    json.dumps(preset.params),
                    preset.usage_count,
                )
            )
        return preset
    
    def get_style_preset(self, preset_id: str) -> Optional[StylePreset]:
        """获取风格预设"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM style_presets WHERE id = ?",
                (preset_id,)
            ).fetchone()
            if row:
                data = self._row_to_dict(row)
                data['is_builtin'] = bool(data.get('is_builtin', 0))
                data['is_active'] = bool(data.get('is_active', 1))
                return StylePreset.model_validate(data)
            return None
    
    def list_style_presets(self, include_inactive: bool = False) -> List[StylePreset]:
        """列出所有风格预设"""
        query = "SELECT * FROM style_presets"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY is_builtin DESC, usage_count DESC, created_at DESC"
        
        with self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            presets = []
            for row in rows:
                data = self._row_to_dict(row)
                data['is_builtin'] = bool(data.get('is_builtin', 0))
                data['is_active'] = bool(data.get('is_active', 1))
                presets.append(StylePreset.model_validate(data))
            return presets
    
    def update_style_preset(self, preset_id: str, data: Dict[str, Any]) -> bool:
        """更新风格预设"""
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return False
        
        # 处理特殊字段
        if "params" in data and isinstance(data["params"], dict):
            data["params"] = json.dumps(data["params"])
        if "is_builtin" in data:
            data["is_builtin"] = 1 if data["is_builtin"] else 0
        if "is_active" in data:
            data["is_active"] = 1 if data["is_active"] else 0
        if "tone" in data and hasattr(data["tone"], "value"):
            data["tone"] = data["tone"].value
        if "style" in data and hasattr(data["style"], "value"):
            data["style"] = data["style"].value
        
        data["updated_at"] = datetime.now().isoformat()
        
        fields = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [preset_id]
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE style_presets SET {fields} WHERE id = ? AND is_builtin = 0",
                values
            )
            return cursor.rowcount > 0
    
    def delete_style_preset(self, preset_id: str) -> bool:
        """删除风格预设（只能删除非内置）"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM style_presets WHERE id = ? AND is_builtin = 0",
                (preset_id,)
            )
            return cursor.rowcount > 0
    
    def increment_preset_usage(self, preset_id: str) -> bool:
        """增加预设使用次数"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE style_presets SET usage_count = usage_count + 1 WHERE id = ?",
                (preset_id,)
            )
            return cursor.rowcount > 0
    
    def init_builtin_presets(self, presets: List[StylePreset]):
        """初始化内置预设"""
        with self._get_connection() as conn:
            for preset in presets:
                # 检查是否已存在
                existing = conn.execute(
                    "SELECT id FROM style_presets WHERE id = ?",
                    (preset.id,)
                ).fetchone()
                
                if not existing:
                    conn.execute(
                        """
                        INSERT INTO style_presets (id, name, description, system_prompt,
                            tone, style, temperature, max_tokens, is_builtin, is_active,
                            params, usage_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, 0)
                        """,
                        (
                            preset.id,
                            preset.name,
                            preset.description,
                            preset.system_prompt,
                            preset.tone.value,
                            preset.style.value,
                            preset.temperature,
                            preset.max_tokens,
                            json.dumps(preset.params),
                        )
                    )

    def delete_inspiration(self, record_id: str) -> bool:
        """删除灵感记录"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM inspiration_records WHERE id = ?",
                (record_id,)
            )
            return cursor.rowcount > 0

    # ============ 任务操作 ============
    def create_task(self, task: Task) -> Task:
        """创建任务记录"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tasks (id, name, payload, status, result, error_message,
                    account_id, target_id, max_retries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.name.value,
                    json.dumps(task.payload),
                    task.status.value,
                    json.dumps(task.result),
                    task.error_message,
                    task.account_id,
                    task.target_id,
                    task.max_retries,
                )
            )
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            ).fetchone()
            if row:
                return Task.model_validate(self._row_to_dict(row))
            return None

    def list_tasks(self, account_id: Optional[str] = None,
                   status: Optional[str] = None,
                   name: Optional[str] = None,
                   limit: int = 100,
                   offset: int = 0) -> List[Task]:
        """列出任务"""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        if name:
            query += " AND name = ?"
            params.append(name)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Task.model_validate(self._row_to_dict(row)) for row in rows]

    def update_task(self, task_id: str, data: Dict[str, Any]) -> bool:
        """更新任务"""
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return False

        if "payload" in data and isinstance(data["payload"], dict):
            data["payload"] = json.dumps(data["payload"])
        if "result" in data and isinstance(data["result"], dict):
            data["result"] = json.dumps(data["result"])
        if "status" in data and hasattr(data["status"], "value"):
            data["status"] = data["status"].value
        if "name" in data and hasattr(data["name"], "value"):
            data["name"] = data["name"].value

        data["updated_at"] = datetime.now().isoformat()

        fields = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [task_id]

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE tasks SET {fields} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,)
            )
            return cursor.rowcount > 0

    def get_task_stats(self, account_id: Optional[str] = None) -> Dict[str, int]:
        """获取任务统计"""
        with self._get_connection() as conn:
            query = "SELECT status, COUNT(*) as count FROM tasks"
            params = []
            if account_id:
                query += " WHERE account_id = ?"
                params.append(account_id)
            query += " GROUP BY status"
            rows = conn.execute(query, params).fetchall()
            return {row["status"]: row["count"] for row in rows}
