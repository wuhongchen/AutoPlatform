import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Dict, Iterable, List, Optional


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_text(value) -> str:
    return str(value or "").strip()


def _normalize_datetime_text(value) -> str:
    raw = value
    if isinstance(raw, dict):
        for key in ("value", "datetime", "date", "text", "created_time", "updated_time", "time"):
            if raw.get(key):
                raw = raw.get(key)
                break
        else:
            raw = ""
    if raw in (None, ""):
        return ""
    if isinstance(raw, (int, float)):
        ts = float(raw)
        if ts > 1_000_000_000_000:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""

    text = _safe_text(raw)
    if not text:
        return ""
    try:
        normalized = text.replace("T", " ").replace("Z", "")
        normalized = normalized.split(".")[0].strip()
        if len(normalized) == 10 and normalized.count("-") == 2:
            return f"{normalized} 00:00:00"
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return normalized
    except Exception:
        return text


class WorkflowStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS pipeline_records (
                    record_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    source_record_id TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    source_doc_url TEXT NOT NULL DEFAULT '',
                    rewritten_doc TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL DEFAULT '',
                    remark TEXT NOT NULL DEFAULT '',
                    draft_id TEXT NOT NULL DEFAULT '',
                    owner TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT '',
                    published_at TEXT NOT NULL DEFAULT '',
                    extra_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_pipeline_account_updated
                ON pipeline_records(account_id, updated_at DESC);

                CREATE INDEX IF NOT EXISTS idx_pipeline_account_status
                ON pipeline_records(account_id, status);

                CREATE INDEX IF NOT EXISTS idx_pipeline_source_record
                ON pipeline_records(account_id, source_record_id);

                CREATE TABLE IF NOT EXISTS publish_logs (
                    record_id TEXT PRIMARY KEY,
                    pipeline_record_id TEXT NOT NULL DEFAULT '',
                    account_id TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    publish_status TEXT NOT NULL DEFAULT '',
                    result TEXT NOT NULL DEFAULT '',
                    remark TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    rewritten_doc TEXT NOT NULL DEFAULT '',
                    draft_id TEXT NOT NULL DEFAULT '',
                    published_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT '',
                    extra_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_publish_account_published
                ON publish_logs(account_id, published_at DESC);

                CREATE INDEX IF NOT EXISTS idx_publish_pipeline_record
                ON publish_logs(pipeline_record_id);

                CREATE TABLE IF NOT EXISTS inspiration_records (
                    record_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    doc_url TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    captured_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT '',
                    remark TEXT NOT NULL DEFAULT '',
                    cover_token TEXT NOT NULL DEFAULT '',
                    cover_name TEXT NOT NULL DEFAULT '',
                    cover_type TEXT NOT NULL DEFAULT '',
                    extra_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_inspiration_account_updated
                ON inspiration_records(account_id, captured_at DESC);

                CREATE INDEX IF NOT EXISTS idx_inspiration_account_status
                ON inspiration_records(account_id, status);

                -- 文章内容存储表（替换飞书文档）
                CREATE TABLE IF NOT EXISTS article_contents (
                    record_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    original_html TEXT NOT NULL DEFAULT '',
                    original_text TEXT NOT NULL DEFAULT '',
                    original_json TEXT NOT NULL DEFAULT '{}',
                    rewritten_html TEXT NOT NULL DEFAULT '',
                    rewritten_text TEXT NOT NULL DEFAULT '',
                    rewritten_json TEXT NOT NULL DEFAULT '{}',
                    images_json TEXT NOT NULL DEFAULT '[]',
                    files_dir TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_article_account
                ON article_contents(account_id);

                -- 插件任务表
                CREATE TABLE IF NOT EXISTS plugin_tasks (
                    task_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    plugin_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    params_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error_msg TEXT NOT NULL DEFAULT '',
                    started_at TEXT,
                    ended_at TEXT,
                    created_at TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_plugin_task_record
                ON plugin_tasks(record_id);

                CREATE INDEX IF NOT EXISTS idx_plugin_task_status
                ON plugin_tasks(status);
                """
            )

    def _row_to_pipeline(self, row: sqlite3.Row) -> Dict:
        item = dict(row)
        try:
            item["extra"] = json.loads(item.pop("extra_json", "{}") or "{}")
        except Exception:
            item["extra"] = {}
        return item

    def _row_to_publish(self, row: sqlite3.Row) -> Dict:
        item = dict(row)
        try:
            item["extra"] = json.loads(item.pop("extra_json", "{}") or "{}")
        except Exception:
            item["extra"] = {}
        return item

    def _make_pipeline_payload(self, payload: Dict) -> Dict:
        now = _now_str()
        out = {
            "record_id": _safe_text(payload.get("record_id")) or f"loc_{uuid.uuid4().hex[:12]}",
            "account_id": _safe_text(payload.get("account_id")) or "default",
            "source_record_id": _safe_text(payload.get("source_record_id")),
            "source_type": _safe_text(payload.get("source_type")),
            "title": _safe_text(payload.get("title")),
            "url": _safe_text(payload.get("url")),
            "source_doc_url": _safe_text(payload.get("source_doc_url")),
            "rewritten_doc": _safe_text(payload.get("rewritten_doc")),
            "status": _safe_text(payload.get("status")),
            "model": _safe_text(payload.get("model")),
            "role": _safe_text(payload.get("role")),
            "remark": _safe_text(payload.get("remark")),
            "draft_id": _safe_text(payload.get("draft_id")),
            "owner": _safe_text(payload.get("owner")),
            "created_at": _normalize_datetime_text(payload.get("created_at")) or now,
            "updated_at": _normalize_datetime_text(payload.get("updated_at")) or now,
            "published_at": _normalize_datetime_text(payload.get("published_at")),
            "extra_json": json.dumps(payload.get("extra") or {}, ensure_ascii=False),
        }
        return out

    def _make_publish_payload(self, payload: Dict) -> Dict:
        now = _now_str()
        published_at = _normalize_datetime_text(payload.get("published_at")) or now
        out = {
            "record_id": _safe_text(payload.get("record_id")) or f"pub_{uuid.uuid4().hex[:12]}",
            "pipeline_record_id": _safe_text(payload.get("pipeline_record_id")),
            "account_id": _safe_text(payload.get("account_id")) or "default",
            "title": _safe_text(payload.get("title")),
            "publish_status": _safe_text(payload.get("publish_status")) or _safe_text(payload.get("result")) or "已发布",
            "result": _safe_text(payload.get("result")) or _safe_text(payload.get("publish_status")) or "已发布",
            "remark": _safe_text(payload.get("remark")),
            "url": _safe_text(payload.get("url")),
            "rewritten_doc": _safe_text(payload.get("rewritten_doc")),
            "draft_id": _safe_text(payload.get("draft_id")),
            "published_at": published_at,
            "created_at": _normalize_datetime_text(payload.get("created_at")) or now,
            "extra_json": json.dumps(payload.get("extra") or {}, ensure_ascii=False),
        }
        return out

    def has_pipeline_records(self, account_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM pipeline_records WHERE account_id = ?",
                (_safe_text(account_id) or "default",),
            ).fetchone()
        return bool((row["cnt"] if row else 0) > 0)

    def has_publish_logs(self, account_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM publish_logs WHERE account_id = ?",
                (_safe_text(account_id) or "default",),
            ).fetchone()
        return bool((row["cnt"] if row else 0) > 0)

    def upsert_pipeline(self, payload: Dict) -> Dict:
        item = self._make_pipeline_payload(payload)
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT created_at FROM pipeline_records WHERE record_id = ?",
                (item["record_id"],),
            ).fetchone()
            if existing and _safe_text(existing["created_at"]):
                item["created_at"] = _safe_text(existing["created_at"])
            conn.execute(
                """
                INSERT INTO pipeline_records (
                    record_id, account_id, source_record_id, source_type, title, url,
                    source_doc_url, rewritten_doc, status, model, role, remark,
                    draft_id, owner, created_at, updated_at, published_at, extra_json
                ) VALUES (
                    :record_id, :account_id, :source_record_id, :source_type, :title, :url,
                    :source_doc_url, :rewritten_doc, :status, :model, :role, :remark,
                    :draft_id, :owner, :created_at, :updated_at, :published_at, :extra_json
                )
                ON CONFLICT(record_id) DO UPDATE SET
                    account_id = excluded.account_id,
                    source_record_id = excluded.source_record_id,
                    source_type = excluded.source_type,
                    title = excluded.title,
                    url = excluded.url,
                    source_doc_url = excluded.source_doc_url,
                    rewritten_doc = excluded.rewritten_doc,
                    status = excluded.status,
                    model = excluded.model,
                    role = excluded.role,
                    remark = excluded.remark,
                    draft_id = excluded.draft_id,
                    owner = excluded.owner,
                    updated_at = excluded.updated_at,
                    published_at = excluded.published_at,
                    extra_json = excluded.extra_json
                """,
                item,
            )
            row = conn.execute(
                "SELECT * FROM pipeline_records WHERE record_id = ?",
                (item["record_id"],),
            ).fetchone()
        return self._row_to_pipeline(row) if row else dict(item)

    def create_pipeline(self, payload: Dict) -> Dict:
        return self.upsert_pipeline(payload)

    def update_pipeline(self, record_id: str, **fields) -> Optional[Dict]:
        current = self.get_pipeline(record_id)
        if not current:
            return None
        merged = dict(current)
        merged.update(fields)
        merged["record_id"] = current["record_id"]
        merged["account_id"] = _safe_text(fields.get("account_id") or current.get("account_id")) or "default"
        merged["updated_at"] = _normalize_datetime_text(fields.get("updated_at")) or _now_str()
        return self.upsert_pipeline(merged)

    def get_pipeline(self, record_id: str, account_id: str = "") -> Optional[Dict]:
        rid = _safe_text(record_id)
        if not rid:
            return None
        sql = "SELECT * FROM pipeline_records WHERE record_id = ?"
        params: List[str] = [rid]
        if _safe_text(account_id):
            sql += " AND account_id = ?"
            params.append(_safe_text(account_id))
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return self._row_to_pipeline(row) if row else None

    def find_pipeline_by_source_record(self, account_id: str, source_record_id: str) -> Optional[Dict]:
        aid = _safe_text(account_id) or "default"
        sid = _safe_text(source_record_id)
        if not sid:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM pipeline_records
                WHERE account_id = ? AND source_record_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (aid, sid),
            ).fetchone()
        return self._row_to_pipeline(row) if row else None

    def find_pipeline_by_url(self, account_id: str, url: str) -> Optional[Dict]:
        """根据URL查找是否已有重复内容"""
        aid = _safe_text(account_id) or "default"
        url = _safe_text(url)
        if not url or len(url) < 10:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM pipeline_records
                WHERE account_id = ? AND url = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (aid, url),
            ).fetchone()
        return self._row_to_pipeline(row) if row else None

    def list_pipeline(self, account_id: str, status: str = "", keyword: str = "", limit: int = 500) -> List[Dict]:
        clauses = ["account_id = ?"]
        params: List = [_safe_text(account_id) or "default"]
        if _safe_text(status):
            clauses.append("status = ?")
            params.append(_safe_text(status))
        if _safe_text(keyword):
            q = f"%{_safe_text(keyword).lower()}%"
            clauses.append(
                "(LOWER(title) LIKE ? OR LOWER(url) LIKE ? OR LOWER(rewritten_doc) LIKE ? OR LOWER(remark) LIKE ? OR LOWER(record_id) LIKE ?)"
            )
            params.extend([q, q, q, q, q])
        params.append(max(1, int(limit or 500)))
        sql = f"""
            SELECT * FROM pipeline_records
            WHERE {' AND '.join(clauses)}
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_pipeline(row) for row in rows]

    def list_pipeline_pending(self, account_id: str, statuses: Iterable[str], limit: int) -> List[Dict]:
        status_list = [_safe_text(item) for item in statuses if _safe_text(item)]
        if not status_list:
            return []
        placeholders = ",".join("?" for _ in status_list)
        sql = f"""
            SELECT * FROM pipeline_records
            WHERE account_id = ? AND status IN ({placeholders})
            ORDER BY updated_at ASC, created_at ASC
            LIMIT ?
        """
        params: List = [_safe_text(account_id) or "default", *status_list, max(1, int(limit or 1))]
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_pipeline(row) for row in rows]

    def pipeline_status_counts(self, account_id: str) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS cnt
                FROM pipeline_records
                WHERE account_id = ?
                GROUP BY status
                """,
                (_safe_text(account_id) or "default",),
            ).fetchall()
        return {_safe_text(row["status"]) or "(空)": int(row["cnt"] or 0) for row in rows}

    def upsert_publish_log(self, payload: Dict) -> Dict:
        item = self._make_publish_payload(payload)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO publish_logs (
                    record_id, pipeline_record_id, account_id, title, publish_status, result,
                    remark, url, rewritten_doc, draft_id, published_at, created_at, extra_json
                ) VALUES (
                    :record_id, :pipeline_record_id, :account_id, :title, :publish_status, :result,
                    :remark, :url, :rewritten_doc, :draft_id, :published_at, :created_at, :extra_json
                )
                ON CONFLICT(record_id) DO UPDATE SET
                    pipeline_record_id = excluded.pipeline_record_id,
                    account_id = excluded.account_id,
                    title = excluded.title,
                    publish_status = excluded.publish_status,
                    result = excluded.result,
                    remark = excluded.remark,
                    url = excluded.url,
                    rewritten_doc = excluded.rewritten_doc,
                    draft_id = excluded.draft_id,
                    published_at = excluded.published_at,
                    extra_json = excluded.extra_json
                """,
                item,
            )
            row = conn.execute(
                "SELECT * FROM publish_logs WHERE record_id = ?",
                (item["record_id"],),
            ).fetchone()
        return self._row_to_publish(row) if row else dict(item)

    def add_publish_log(self, payload: Dict) -> Dict:
        return self.upsert_publish_log(payload)

    def list_publish_logs(self, account_id: str, status: str = "", keyword: str = "", limit: int = 500) -> List[Dict]:
        clauses = ["account_id = ?"]
        params: List = [_safe_text(account_id) or "default"]
        if _safe_text(status):
            clauses.append("publish_status = ?")
            params.append(_safe_text(status))
        if _safe_text(keyword):
            q = f"%{_safe_text(keyword).lower()}%"
            clauses.append(
                "(LOWER(title) LIKE ? OR LOWER(url) LIKE ? OR LOWER(rewritten_doc) LIKE ? OR LOWER(remark) LIKE ? OR LOWER(record_id) LIKE ?)"
            )
            params.extend([q, q, q, q, q])
        params.append(max(1, int(limit or 500)))
        sql = f"""
            SELECT * FROM publish_logs
            WHERE {' AND '.join(clauses)}
            ORDER BY published_at DESC, created_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_publish(row) for row in rows]

    def import_pipeline_rows(self, account_id: str, rows: List[Dict]) -> int:
        imported = 0
        for row in rows or []:
            payload = {
                "record_id": row.get("record_id"),
                "account_id": account_id,
                "title": row.get("title"),
                "status": row.get("status"),
                "model": row.get("model"),
                "url": row.get("url"),
                "source_doc_url": row.get("source_doc_url"),
                "rewritten_doc": row.get("rewritten_doc"),
                "remark": row.get("remark"),
                "updated_at": row.get("updated_at"),
                "source_type": "feishu_pipeline_import",
            }
            self.upsert_pipeline(payload)
            imported += 1
        return imported

    def import_publish_rows(self, account_id: str, rows: List[Dict]) -> int:
        imported = 0
        for row in rows or []:
            payload = {
                "record_id": row.get("record_id"),
                "account_id": account_id,
                "title": row.get("title"),
                "publish_status": row.get("publish_status"),
                "result": row.get("result"),
                "remark": row.get("remark"),
                "url": row.get("url"),
                "rewritten_doc": row.get("rewritten_doc"),
                "published_at": row.get("published_at"),
            }
            self.upsert_publish_log(payload)
            imported += 1
        return imported

    # === Inspiration Records (灵感库本地存储) ===
    def _row_to_inspiration(self, row: sqlite3.Row) -> Dict:
        item = dict(row)
        try:
            item["extra"] = json.loads(item.pop("extra_json", "{}") or "{}")
        except Exception:
            item["extra"] = {}
        return item

    def _make_inspiration_payload(self, payload: Dict) -> Dict:
        now = _now_str()
        # 构建extra_json，包含AI评分等额外字段
        extra = payload.get("extra") or {}
        ai_score = payload.get("ai_score")
        ai_reason = payload.get("ai_reason")
        if ai_score is not None:
            extra["ai_score"] = ai_score
        if ai_reason:
            extra["ai_reason"] = ai_reason

        out = {
            "record_id": _safe_text(payload.get("record_id")) or f"ins_{uuid.uuid4().hex[:12]}",
            "account_id": _safe_text(payload.get("account_id")) or "default",
            "title": _safe_text(payload.get("title")),
            "url": _safe_text(payload.get("url")),
            "doc_url": _safe_text(payload.get("doc_url")),
            "status": _safe_text(payload.get("status")),
            "captured_at": _normalize_datetime_text(payload.get("captured_at")) or now,
            "updated_at": _normalize_datetime_text(payload.get("updated_at")) or now,
            "remark": _safe_text(payload.get("remark")),
            "cover_token": _safe_text(payload.get("cover_token")),
            "cover_name": _safe_text(payload.get("cover_name")),
            "cover_type": _safe_text(payload.get("cover_type")),
            "extra_json": json.dumps(extra, ensure_ascii=False),
        }
        return out

    def has_inspiration_records(self, account_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM inspiration_records WHERE account_id = ?",
                (_safe_text(account_id) or "default",),
            ).fetchone()
        return bool((row["cnt"] if row else 0) > 0)

    def upsert_inspiration(self, payload: Dict) -> Dict:
        item = self._make_inspiration_payload(payload)
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM inspiration_records WHERE record_id = ?",
                (item["record_id"],),
            ).fetchone()

            if existing:
                # 存在旧记录：空值不覆盖原有值，保护URL等重要字段不被清空
                existing_dict = dict(existing)
                # 只更新非空字段
                for key in ["title", "url", "doc_url", "status", "remark", "cover_token", "cover_name", "cover_type"]:
                    if not _safe_text(item.get(key)):
                        item[key] = existing_dict.get(key, "")
                # 保留原始创建时间
                if _safe_text(existing_dict.get("captured_at")):
                    item["captured_at"] = _safe_text(existing_dict["captured_at"])

            conn.execute(
                """
                INSERT INTO inspiration_records (
                    record_id, account_id, title, url, doc_url,
                    status, captured_at, updated_at, remark,
                    cover_token, cover_name, cover_type, extra_json
                ) VALUES (
                    :record_id, :account_id, :title, :url, :doc_url,
                    :status, :captured_at, :updated_at, :remark,
                    :cover_token, :cover_name, :cover_type, :extra_json
                )
                ON CONFLICT(record_id) DO UPDATE SET
                    account_id = excluded.account_id,
                    title = excluded.title,
                    url = excluded.url,
                    doc_url = excluded.doc_url,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    remark = excluded.remark,
                    cover_token = excluded.cover_token,
                    cover_name = excluded.cover_name,
                    cover_type = excluded.cover_type,
                    extra_json = excluded.extra_json
                """,
                item,
            )
            row = conn.execute(
                "SELECT * FROM inspiration_records WHERE record_id = ?",
                (item["record_id"],),
            ).fetchone()
        return self._row_to_inspiration(row) if row else dict(item)

    def get_inspiration(self, record_id: str, account_id: str = "") -> Optional[Dict]:
        rid = _safe_text(record_id)
        if not rid:
            return None
        sql = "SELECT * FROM inspiration_records WHERE record_id = ?"
        params: List[str] = [rid]
        if _safe_text(account_id):
            sql += " AND account_id = ?"
            params.append(_safe_text(account_id))
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return self._row_to_inspiration(row) if row else None

    def list_inspiration(self, account_id: str, status: str = "", keyword: str = "", limit: int = 500) -> List[Dict]:
        clauses = ["account_id = ?"]
        params: List = [_safe_text(account_id) or "default"]
        if _safe_text(status):
            clauses.append("status = ?")
            params.append(_safe_text(status))
        if _safe_text(keyword):
            q = f"%{_safe_text(keyword).lower()}%"
            clauses.append(
                "(LOWER(title) LIKE ? OR LOWER(url) LIKE ? OR LOWER(doc_url) LIKE ? OR LOWER(remark) LIKE ?)"
            )
            params.extend([q, q, q, q])
        params.append(max(1, int(limit or 500)))
        sql = f"""
            SELECT * FROM inspiration_records
            WHERE {' AND '.join(clauses)}
            ORDER BY captured_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_inspiration(row) for row in rows]

    def publish_status_counts(self, account_id: str) -> Dict[str, int]:
        """统计发布日志各状态数量"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT publish_status, COUNT(*) AS cnt
                FROM publish_logs
                WHERE account_id = ?
                GROUP BY publish_status
                """,
                (_safe_text(account_id) or "default",),
            ).fetchall()
        return {_safe_text(row["publish_status"]) or "(空)": int(row["cnt"] or 0) for row in rows}

    def inspiration_status_counts(self, account_id: str) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS cnt
                FROM inspiration_records
                WHERE account_id = ?
                GROUP BY status
                """,
                (_safe_text(account_id) or "default",),
            ).fetchall()
        return {_safe_text(row["status"]) or "(空)": int(row["cnt"] or 0) for row in rows}

    def import_inspiration_rows(self, account_id: str, rows: List[Dict]) -> int:
        imported = 0
        for row in rows or []:
            payload = {
                "record_id": row.get("record_id"),
                "account_id": account_id,
                "title": row.get("title"),
                "url": row.get("url"),
                "doc_url": row.get("doc_url"),
                "status": row.get("status"),
                "captured_at": row.get("captured_at"),
                "remark": row.get("remark"),
                "cover_token": row.get("cover_token"),
                "cover_name": row.get("cover_name"),
                "cover_type": row.get("cover_type"),
                "ai_score": row.get("ai_score"),
                "ai_reason": row.get("ai_reason"),
            }
            self.upsert_inspiration(payload)
            imported += 1
        return imported

    def delete_inspiration(self, record_id: str, account_id: str = "") -> bool:
        rid = _safe_text(record_id)
        if not rid:
            return False
        with self._lock, self._connect() as conn:
            sql = "DELETE FROM inspiration_records WHERE record_id = ?"
            params = [rid]
            if _safe_text(account_id):
                sql += " AND account_id = ?"
                params.append(_safe_text(account_id))
            conn.execute(sql, params)
            return True

    def delete_pipeline(self, record_id: str, account_id: str = "") -> bool:
        rid = _safe_text(record_id)
        if not rid:
            return False
        with self._lock, self._connect() as conn:
            sql = "DELETE FROM pipeline_records WHERE record_id = ?"
            params = [rid]
            if _safe_text(account_id):
                sql += " AND account_id = ?"
                params.append(_safe_text(account_id))
            conn.execute(sql, params)
            return True

    # ═══════════════════════════════════════════════════════
    # 文章内容存储 (替代飞书文档)
    # ═══════════════════════════════════════════════════════

    def save_article_content(self, record_id: str, account_id: str,
                             original_html: str = "", original_text: str = "",
                             original_data: dict = None,
                             rewritten_html: str = "", rewritten_text: str = "",
                             rewritten_data: dict = None,
                             images: list = None, files_dir: str = "") -> dict:
        """保存文章内容"""
        now = _now_str()
        item = {
            "record_id": record_id,
            "account_id": _safe_text(account_id) or "default",
            "original_html": original_html or "",
            "original_text": original_text or "",
            "original_json": json.dumps(original_data or {}, ensure_ascii=False),
            "rewritten_html": rewritten_html or "",
            "rewritten_text": rewritten_text or "",
            "rewritten_json": json.dumps(rewritten_data or {}, ensure_ascii=False),
            "images_json": json.dumps(images or [], ensure_ascii=False),
            "files_dir": files_dir or "",
            "created_at": now,
            "updated_at": now,
        }

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO article_contents (
                    record_id, account_id, original_html, original_text, original_json,
                    rewritten_html, rewritten_text, rewritten_json, images_json, files_dir,
                    created_at, updated_at
                ) VALUES (
                    :record_id, :account_id, :original_html, :original_text, :original_json,
                    :rewritten_html, :rewritten_text, :rewritten_json, :images_json, :files_dir,
                    :created_at, :updated_at
                )
                ON CONFLICT(record_id) DO UPDATE SET
                    original_html = COALESCE(excluded.original_html, original_html),
                    original_text = COALESCE(excluded.original_text, original_text),
                    original_json = COALESCE(excluded.original_json, original_json),
                    rewritten_html = COALESCE(excluded.rewritten_html, rewritten_html),
                    rewritten_text = COALESCE(excluded.rewritten_text, rewritten_text),
                    rewritten_json = COALESCE(excluded.rewritten_json, rewritten_json),
                    images_json = COALESCE(excluded.images_json, images_json),
                    files_dir = COALESCE(excluded.files_dir, files_dir),
                    updated_at = excluded.updated_at
                """,
                item
            )
        return item

    def get_article_content(self, record_id: str, account_id: str = "") -> Optional[dict]:
        """获取文章内容"""
        rid = _safe_text(record_id)
        if not rid:
            return None

        sql = "SELECT * FROM article_contents WHERE record_id = ?"
        params: List[str] = [rid]
        if _safe_text(account_id):
            sql += " AND account_id = ?"
            params.append(_safe_text(account_id))

        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()

        if not row:
            return None

        item = dict(row)
        try:
            item["original_data"] = json.loads(item.pop("original_json", "{}"))
            item["rewritten_data"] = json.loads(item.pop("rewritten_json", "{}"))
            item["images"] = json.loads(item.pop("images_json", "[]"))
        except Exception:
            item["original_data"] = {}
            item["rewritten_data"] = {}
            item["images"] = []
        return item

    def delete_article_content(self, record_id: str, account_id: str = "") -> bool:
        """删除文章内容"""
        rid = _safe_text(record_id)
        if not rid:
            return False

        sql = "DELETE FROM article_contents WHERE record_id = ?"
        params = [rid]
        if _safe_text(account_id):
            sql += " AND account_id = ?"
            params.append(_safe_text(account_id))

        with self._lock, self._connect() as conn:
            conn.execute(sql, params)
        return True

    # ═══════════════════════════════════════════════════════
    # 插件任务管理
    # ═══════════════════════════════════════════════════════

    def create_plugin_task(self, record_id: str, account_id: str,
                           plugin_type: str, params: dict = None) -> str:
        """创建插件任务"""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = _now_str()

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO plugin_tasks (
                    task_id, account_id, record_id, plugin_type, status,
                    params_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, _safe_text(account_id) or "default", record_id,
                 plugin_type, "pending", json.dumps(params or {}), now)
            )
        return task_id

    def update_plugin_task(self, task_id: str, status: str = None,
                           result: dict = None, error_msg: str = None) -> bool:
        """更新插件任务状态"""
        tid = _safe_text(task_id)
        if not tid:
            return False

        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
            if status in ("running",):
                updates.append("started_at = ?")
                params.append(_now_str())
            if status in ("success", "failed"):
                updates.append("ended_at = ?")
                params.append(_now_str())

        if result is not None:
            updates.append("result_json = ?")
            params.append(json.dumps(result, ensure_ascii=False))

        if error_msg is not None:
            updates.append("error_msg = ?")
            params.append(error_msg)

        if not updates:
            return False

        params.append(tid)
        sql = f"UPDATE plugin_tasks SET {', '.join(updates)} WHERE task_id = ?"

        with self._lock, self._connect() as conn:
            conn.execute(sql, params)
        return True

    def get_plugin_tasks(self, record_id: str = None, account_id: str = "",
                         plugin_type: str = None, status: str = None,
                         limit: int = 100) -> List[dict]:
        """获取插件任务列表"""
        clauses = []
        params = []

        if _safe_text(record_id):
            clauses.append("record_id = ?")
            params.append(record_id)

        if _safe_text(account_id):
            clauses.append("account_id = ?")
            params.append(account_id)

        if _safe_text(plugin_type):
            clauses.append("plugin_type = ?")
            params.append(plugin_type)

        if _safe_text(status):
            clauses.append("status = ?")
            params.append(status)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT * FROM plugin_tasks
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(max(1, int(limit)))

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            try:
                item["params"] = json.loads(item.pop("params_json", "{}"))
                item["result"] = json.loads(item.pop("result_json", "{}"))
            except Exception:
                item["params"] = {}
                item["result"] = {}
            result.append(item)
        return result
