import os
import re
import shlex
import subprocess
import threading
import time
import uuid
from datetime import datetime
from mimetypes import guess_type
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, request, Response, send_from_directory, send_file, redirect

from admin_accounts import AccountStore
from config import Config
from modules.feishu import FeishuBitable
from modules.state_machine import PipelineState, canonical_pipeline_status
from modules.workflow_store import WorkflowStore
from modules.wechat_ingest_service import WechatIngestService


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VUE_FRONTEND_DIR = Path(PROJECT_ROOT) / "frontend" / "admin"
VUE_DIST_DIR = VUE_FRONTEND_DIR / "dist"
VUE_INDEX_PATH = VUE_DIST_DIR / "index.html"
HUASHENG_EDITOR_DIR = Path(PROJECT_ROOT) / "third_party" / "huasheng_editor"
PYTHON_BIN = os.getenv("ADMIN_PYTHON_PATH", "python3")
DEFAULT_ROLE = os.getenv("OPENCLAW_ROLE", "tech_expert")
DEFAULT_MODEL = os.getenv("OPENCLAW_MODEL", "auto")
DEFAULT_BATCH = os.getenv("OPENCLAW_PIPELINE_BATCH_SIZE", "3")


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_text(value) -> str:
    return str(value or "").strip()


def _normalize_datetime_text(field_val) -> str:
    def _unwrap(val):
        if isinstance(val, list):
            return _unwrap(val[0]) if val else ""
        if isinstance(val, dict):
            for key in ("value", "datetime", "date", "text", "created_time", "updated_time", "time"):
                if val.get(key):
                    return _unwrap(val.get(key))
            return ""
        return val

    raw = _unwrap(field_val)
    if raw in (None, ""):
        return ""

    ts = None
    if isinstance(raw, (int, float)):
        ts = float(raw)
    else:
        text = _safe_text(raw)
        if not text:
            return ""
        if re.fullmatch(r"\d{10,16}", text):
            ts = float(text)
        else:
            normalized = text.replace("T", " ").replace("Z", "")
            normalized = re.sub(r"\.\d+$", "", normalized)
            normalized = re.sub(r"([+-]\d{2}:?\d{2})$", "", normalized).strip()
            matched_datetime = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", normalized)
            if matched_datetime:
                return matched_datetime.group(1)
            matched_date = re.match(r"^(\d{4}-\d{2}-\d{2})$", normalized)
            if matched_date:
                return f"{matched_date.group(1)} 00:00:00"
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    dt = dt.astimezone().replace(tzinfo=None)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return text

    if ts is None:
        return ""
    if ts > 1_000_000_000_000:
        ts /= 1000.0
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _field_to_text(field_val) -> str:
    if not field_val:
        return ""
    if isinstance(field_val, dict):
        return _safe_text(field_val.get("url") or field_val.get("link") or field_val.get("text"))
    if isinstance(field_val, list) and field_val:
        first = field_val[0]
        if isinstance(first, dict):
            return _safe_text(first.get("url") or first.get("link") or first.get("text"))
        return _safe_text(first)
    return _safe_text(field_val)


def _normalize_doc_url(field_val) -> str:
    value = _field_to_text(field_val)
    if not value:
        return ""
    matched = re.search(r"feishu\.cn/docx/([A-Za-z0-9]{27,})", value)
    if matched:
        return f"https://www.feishu.cn/docx/{matched.group(1)}"
    if re.fullmatch(r"[A-Za-z0-9]{27,60}", value):
        return f"https://www.feishu.cn/docx/{value}"
    return ""


def _normalize_http_url(field_val) -> str:
    value = _field_to_text(field_val)
    if not value:
        return ""
    return value if re.match(r"^https?://", value) else ""


def _pick_attachment_meta(field_val) -> Dict[str, str]:
    if not isinstance(field_val, list) or not field_val:
        return {}
    first = field_val[0]
    if not isinstance(first, dict):
        return {}
    return {
        "file_token": _safe_text(first.get("file_token")),
        "name": _safe_text(first.get("name")),
        "type": _safe_text(first.get("type")),
    }


def _guess_image_mimetype(file_name: str, fallback: str = "image/jpeg") -> str:
    guessed, _ = guess_type(file_name or "")
    return guessed or fallback


class JobStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict] = {}
        self._order: List[str] = []
        self._max_logs = 1500

    def create(self, name: str, command: List[str], account: Optional[Dict] = None) -> str:
        job_id = uuid.uuid4().hex[:12]
        account = account or {}
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "name": name,
                "command": " ".join(shlex.quote(x) for x in command),
                "account_id": _safe_text(account.get("id")),
                "account_name": _safe_text(account.get("name")),
                "status": "queued",
                "started_at": "",
                "ended_at": "",
                "return_code": None,
                "logs": [],
            }
            self._order.insert(0, job_id)
            self._order = self._order[:100]
        return job_id

    def append_log(self, job_id: str, line: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            logs = job["logs"]
            logs.append(line.rstrip("\n"))
            if len(logs) > self._max_logs:
                del logs[: len(logs) - self._max_logs]

    def patch(self, job_id: str, **kwargs):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.update(kwargs)

    def get(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return dict(job)

    def list(self):
        with self._lock:
            out = []
            for job_id in self._order:
                job = self._jobs.get(job_id)
                if job:
                    item = dict(job)
                    item.pop("logs", None)
                    out.append(item)
            return out


class Scheduler:
    def __init__(self, run_func):
        self._run_func = run_func
        self._thread = None
        self._stop = threading.Event()
        self._minutes = 0
        self._next_run_at = ""
        self._lock = threading.Lock()

    def start(self, minutes: int):
        minutes = max(1, int(minutes))
        with self._lock:
            if self._thread and self._thread.is_alive():
                self._minutes = minutes
                return
            self._minutes = minutes
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        with self._lock:
            self._stop.set()
            self._next_run_at = ""

    def status(self):
        with self._lock:
            running = bool(self._thread and self._thread.is_alive() and not self._stop.is_set())
            return {
                "running": running,
                "minutes": self._minutes,
                "next_run_at": self._next_run_at,
            }

    def _loop(self):
        while not self._stop.is_set():
            with self._lock:
                minutes = self._minutes
                next_run = datetime.fromtimestamp(time.time() + minutes * 60)
                self._next_run_at = next_run.strftime("%Y-%m-%d %H:%M:%S")
            if self._stop.wait(minutes * 60):
                break
            try:
                self._run_func(source="scheduler")
            except Exception as e:
                print(f"⚠️ scheduler run failed: {e}")
        with self._lock:
            self._next_run_at = ""


app = Flask(__name__)
jobs = JobStore()
accounts = AccountStore()
workflow_store = WorkflowStore(Config.WORKFLOW_DB)


def _base_env(extra=None):
    env = dict(os.environ)
    env.setdefault("OPENCLAW_NON_INTERACTIVE", "1")
    env.setdefault("OPENCLAW_AUTO_INSTALL", "0")
    env.setdefault("OPENCLAW_PIPELINE_BATCH_SIZE", DEFAULT_BATCH)
    if extra:
        env.update(extra)
    return env


def _account_env(account: Optional[Dict]) -> Dict[str, str]:
    account = account or {}
    mapping = {
        "OPENCLAW_ACCOUNT_ID": account.get("id"),
        "WECHAT_APPID": account.get("wechat_appid"),
        "WECHAT_SECRET": account.get("wechat_secret"),
        "WECHAT_AUTHOR": account.get("wechat_author"),
        "FEISHU_APP_ID": account.get("feishu_app_id"),
        "FEISHU_APP_SECRET": account.get("feishu_app_secret"),
        "FEISHU_APP_TOKEN": account.get("feishu_app_token"),
        "FEISHU_INSPIRATION_TABLE": account.get("feishu_inspiration_table"),
        "FEISHU_PIPELINE_TABLE": account.get("feishu_pipeline_table"),
        "FEISHU_PUBLISH_LOG_TABLE": account.get("feishu_publish_log_table"),
        "FEISHU_ADMIN_USER_ID": account.get("feishu_admin_user_id"),
        "OPENCLAW_PIPELINE_ROLE": account.get("pipeline_role"),
        "OPENCLAW_PIPELINE_MODEL": account.get("pipeline_model"),
        "OPENCLAW_PIPELINE_BATCH_SIZE": str(account.get("pipeline_batch_size") or DEFAULT_BATCH),
        "OPENCLAW_CONTENT_DIRECTION": account.get("content_direction"),
        "OPENCLAW_WECHAT_PROMPT_DIRECTION": account.get("wechat_prompt_direction"),
        "OPENCLAW_PROMPT_DIRECTION": account.get("prompt_direction"),
        "OPENCLAW_WECHAT_DEMO_CLI": account.get("wechat_demo_cli"),
    }
    out = {}
    for k, v in mapping.items():
        if v is None:
            continue
        out[k] = str(v)
    return out


def _pick_account(account_id: str = "") -> Dict:
    aid = _safe_text(account_id)
    if aid:
        acc = accounts.get(aid)
        if acc:
            return acc
    return accounts.get_active()


def _account_scope(account: Optional[Dict] = None) -> str:
    account = account or {}
    return _safe_text(account.get("id")) or "default"


def _ensure_account_enabled(account: Dict):
    if not bool(account.get("enabled", True)):
        raise ValueError(f"account disabled: {_safe_text(account.get('name') or account.get('id'))}")


def _run_command_async(name: str, command: List[str], env_extra=None, account: Optional[Dict] = None):
    picked = account or accounts.get_active()
    accounts.mark_runtime(_safe_text(picked.get("id")))
    job_id = jobs.create(name, command, account=picked)

    def _worker():
        jobs.patch(job_id, status="running", started_at=_now_str())
        jobs.append_log(job_id, f"[{_now_str()}] START {name}")
        jobs.append_log(job_id, f"[{_now_str()}] ACCOUNT: {_safe_text(picked.get('name'))} ({_safe_text(picked.get('id'))})")
        jobs.append_log(job_id, f"[{_now_str()}] CMD: {' '.join(shlex.quote(x) for x in command)}")
        try:
            run_env = _base_env(_account_env(picked))
            if env_extra:
                run_env.update(env_extra)
            proc = subprocess.Popen(
                command,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=run_env,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                jobs.append_log(job_id, line.rstrip("\n"))
            proc.wait()
            code = proc.returncode
            jobs.patch(
                job_id,
                status="success" if code == 0 else "failed",
                return_code=code,
                ended_at=_now_str(),
            )
            jobs.append_log(job_id, f"[{_now_str()}] END code={code}")
        except Exception as e:
            jobs.patch(job_id, status="failed", return_code=-1, ended_at=_now_str())
            jobs.append_log(job_id, f"[{_now_str()}] EXCEPTION: {e}")

    threading.Thread(target=_worker, daemon=True).start()
    return job_id


def _run_steps_async(name: str, steps: List[List[str]], env_extra=None, account: Optional[Dict] = None):
    picked = account or accounts.get_active()
    accounts.mark_runtime(_safe_text(picked.get("id")))
    first_cmd = steps[0] if steps else []
    job_id = jobs.create(name, first_cmd, account=picked)

    def _worker():
        jobs.patch(job_id, status="running", started_at=_now_str())
        jobs.append_log(job_id, f"[{_now_str()}] START {name}")
        jobs.append_log(job_id, f"[{_now_str()}] ACCOUNT: {_safe_text(picked.get('name'))} ({_safe_text(picked.get('id'))})")
        run_env = _base_env(_account_env(picked))
        if env_extra:
            run_env.update(env_extra)

        final_code = 0
        try:
            for idx, cmd in enumerate(steps):
                if not cmd:
                    continue
                cmd_text = " ".join(shlex.quote(x) for x in cmd)
                jobs.append_log(job_id, f"[{_now_str()}] STEP {idx + 1}/{len(steps)} CMD: {cmd_text}")
                proc = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=run_env,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    jobs.append_log(job_id, line.rstrip("\n"))
                proc.wait()
                final_code = proc.returncode or 0
                jobs.append_log(job_id, f"[{_now_str()}] STEP {idx + 1} END code={final_code}")
                if final_code != 0:
                    break
        except Exception as e:
            final_code = -1
            jobs.append_log(job_id, f"[{_now_str()}] EXCEPTION: {e}")

        jobs.patch(
            job_id,
            status="success" if final_code == 0 else "failed",
            return_code=final_code,
            ended_at=_now_str(),
        )
        jobs.append_log(job_id, f"[{_now_str()}] END code={final_code}")

    threading.Thread(target=_worker, daemon=True).start()
    return job_id


def _feishu_client(account: Optional[Dict] = None):
    account = account or accounts.get_active()
    app_id = _safe_text(account.get("feishu_app_id")) or Config.FEISHU_APP_ID
    app_secret = _safe_text(account.get("feishu_app_secret")) or Config.FEISHU_APP_SECRET
    app_token = _safe_text(account.get("feishu_app_token")) or Config.FEISHU_APP_TOKEN
    return FeishuBitable(app_id, app_secret, app_token)


def _wechat_service(account: Optional[Dict] = None):
    account = account or accounts.get_active()
    return WechatIngestService(account=account, python_bin=PYTHON_BIN, project_root=PROJECT_ROOT)


def _find_table_id(feishu: FeishuBitable, preferred: str, fallback_contains: List[str]):
    table_id = feishu.get_table_id_by_name(preferred)
    if table_id:
        return table_id
    tables = feishu.list_tables()
    for item in tables:
        name = _safe_text(item.get("name"))
        if any(x in name for x in fallback_contains):
            return item.get("table_id")
    return None


def _overview(account: Optional[Dict] = None):
    account = account or accounts.get_active()
    account_id = _account_scope(account)
    # 优化：不需要每次加载概览都尝试自动导入，导入只在用户手动点击时执行
    # 这大幅加快了概览页面的加载速度
    migration = {
        "pipeline_imported": 0,
        "publish_imported": 0,
        "inspiration_imported": 0,
        "message": "auto-check skipped",
    }
    # 灵感库数据从本地数据库直接读取
    inspiration_items = workflow_store.list_inspiration(account_id, limit=200)
    inspiration_pref = _safe_text(account.get("feishu_inspiration_table")) or Config.FEISHU_INSPIRATION_TABLE
    inspiration_id = ""
    warning = ""

    inspiration_status = {}
    for item in inspiration_items:
        st = _safe_text(item.get("status")) or "(空)"
        inspiration_status[st] = inspiration_status.get(st, 0) + 1

    pipeline_status = workflow_store.pipeline_status_counts(account_id)
    local_pipeline_rows = workflow_store.list_pipeline(account_id, limit=20)
    pipeline_total = sum(int(v or 0) for v in pipeline_status.values())

    # 最近 20 条灵感直接从本地拿
    recent_inspiration = []
    for item in inspiration_items[:20]:
        recent_inspiration.append({
            "record_id": item.get("record_id"),
            "title": _safe_text(item.get("title")),
            "url": _normalize_http_url(item.get("url")),
            "status": _safe_text(item.get("status")),
            "doc_url": item.get("doc_url"),
            "cover_token": item.get("cover_token", ""),
            "cover_name": item.get("cover_name", ""),
            "cover_type": item.get("cover_type", ""),
        })

    recent_pipeline = []
    for row in local_pipeline_rows:
        recent_pipeline.append({
            "record_id": row.get("record_id"),
            "title": _safe_text(row.get("title")),
            "status": _safe_text(canonical_pipeline_status(row.get("status"))),
            "model": _safe_text(row.get("model")),
            "role": _safe_text(row.get("role")),
            "url": _normalize_http_url(row.get("url")),
            "source_doc_url": _normalize_doc_url(row.get("source_doc_url")) or _normalize_http_url(row.get("source_doc_url")),
            "rewritten_doc": _normalize_doc_url(row.get("rewritten_doc")) or _normalize_http_url(row.get("rewritten_doc")),
            "remark": _safe_text(row.get("remark")),
            "updated_at": _safe_text(row.get("updated_at")),
            "published_at": _safe_text(row.get("published_at")),
            "source_type": _safe_text(row.get("source_type")),
        })

    payload = {
        "ok": True,
        "account": {
            "id": _safe_text(account.get("id")),
            "name": _safe_text(account.get("name")),
            "enabled": bool(account.get("enabled", True)),
            "pipeline_role": _safe_text(account.get("pipeline_role")),
            "pipeline_model": _safe_text(account.get("pipeline_model")),
            "content_direction": _safe_text(account.get("content_direction")),
            "wechat_prompt_direction": _safe_text(account.get("wechat_prompt_direction")),
        },
        "meta": {
            "inspiration_table_name": inspiration_pref,
            "inspiration_table_id": inspiration_id or "",
            "inspiration_total": len(inspiration_items) + (workflow_store.has_inspiration_records(account_id) and 0 or 0),
            "pipeline_total": pipeline_total,
            "workflow_backend": "local",
            "workflow_db": _safe_text(Config.WORKFLOW_DB),
            "migration": migration,
            "updated_at": _now_str(),
        },
        "stats": {
            "inspiration_status": inspiration_status,
            "pipeline_status": pipeline_status,
        },
        "recent": {
            "inspiration": recent_inspiration,
            "pipeline": recent_pipeline,
        },
    }
    # 如果本地没有灵感数据，但飞书可用，提示从飞书导入到本地
    if not workflow_store.has_inspiration_records(account_id):
        feishu = _feishu_client(account)
        if feishu._get_token():
            inspiration_id = _find_table_id(feishu, inspiration_pref, ["内容灵感库"]) or ""
            if inspiration_id:
                warning = (warning + "\n" if warning else "") + "本地灵感库为空，可点击「同步旧表数据」从飞书导入到本地数据库。"
        else:
            warning = "飞书鉴权失败，仅展示本地已同步的灵感库数据。"
    if warning:
        payload["warning"] = warning
    return payload


def _inspiration_row(item: Dict) -> Dict:
    fields = item.get("fields", {}) or {}
    doc_url = _normalize_doc_url(fields.get("原文文档")) or _normalize_doc_url(fields.get("原文文档链接"))
    source_url = _normalize_http_url(fields.get("文章 URL"))
    captured_at = ""
    for key in ("抓取时间", "采集时间", "入库时间", "同步时间", "创建时间", "更新时间", "发布时间"):
        captured_at = _normalize_datetime_text(fields.get(key))
        if captured_at:
            break
    if not captured_at:
        captured_at = _normalize_datetime_text(item.get("created_time") or item.get("updated_time"))
    attachment = _pick_attachment_meta(fields.get("图片") or fields.get("素材"))
    # AI 评分字段 - 优先从飞书字段获取，如果没有则从备注中解析
    ai_score = fields.get("AI 爆款潜力评分")
    try:
        ai_score = int(float(ai_score)) if ai_score is not None else None
    except (ValueError, TypeError):
        ai_score = None

    # 如果飞书字段没有评分，尝试从备注中解析 "AI评分: X - ..." 格式
    if ai_score is None:
        remark_text = _safe_text(fields.get("备注"))
        if remark_text.startswith("AI评分:"):
            try:
                score_part = remark_text.split("-")[0].replace("AI评分:", "").strip()
                ai_score = int(float(score_part))
            except (ValueError, TypeError, IndexError):
                ai_score = None
    return {
        "record_id": item.get("record_id"),
        "title": _safe_text(fields.get("标题") or fields.get("原始标题")),
        "url": source_url,
        "source_url": source_url,
        "status": _safe_text(fields.get("处理状态")),
        "doc_url": doc_url,
        "feishu_doc_url": doc_url,
        "captured_at": captured_at,
        "remark": _safe_text(fields.get("备注")),
        "cover_token": attachment.get("file_token", ""),
        "cover_name": attachment.get("name", ""),
        "cover_type": attachment.get("type", ""),
        "ai_score": ai_score,
        "ai_reason": _safe_text(fields.get("AI 推荐理由")),
    }


def _pick_first_datetime(fields: Dict, keys: List[str], fallback_item: Optional[Dict] = None) -> str:
    for key in keys:
        text = _normalize_datetime_text(fields.get(key))
        if text:
            return text
    if isinstance(fallback_item, dict):
        text = _normalize_datetime_text(fallback_item.get("updated_time") or fallback_item.get("created_time"))
        if text:
            return text
    return ""


def _pipeline_row(item: Dict) -> Dict:
    fields = item.get("fields", {}) or {}
    source_url = _normalize_http_url(fields.get("文章 URL"))
    source_doc_url = _normalize_doc_url(fields.get("原文文档链接")) or _normalize_doc_url(fields.get("原文文档"))
    rewritten_doc = _normalize_doc_url(fields.get("改后文档链接")) or _normalize_http_url(fields.get("改后文档链接"))
    stage = _safe_text(canonical_pipeline_status(fields.get("数据流程状态")))
    updated_at = _pick_first_datetime(
        fields,
        ["更新时间", "发布时间", "改写时间", "同步时间", "创建时间"],
        fallback_item=item,
    )
    return {
        "record_id": item.get("record_id"),
        "title": _safe_text(fields.get("标题") or fields.get("原始标题")),
        "status": stage,
        "model": _safe_text(fields.get("改写模型")),
        "url": source_url,
        "source_doc_url": source_doc_url,
        "rewritten_doc": rewritten_doc,
        "remark": _safe_text(fields.get("备注") or fields.get("失败原因")),
        "updated_at": updated_at,
    }


_PIPELINE_STAGE_ALIAS = {
    "待改写": PipelineState.QUEUED_REWRITE,
    "待重写": PipelineState.QUEUED_REWRITE,
    "改写中": PipelineState.REWRITE_RUNNING,
    "重写中": PipelineState.REWRITE_RUNNING,
    "待审核": PipelineState.REVIEW_READY,
    "待发布": PipelineState.PUBLISH_READY,
    "发布中": PipelineState.PUBLISH_RUNNING,
    "已发布": PipelineState.PUBLISHED,
    "改写失败": PipelineState.REWRITE_FAILED,
    "发布失败": PipelineState.PUBLISH_FAILED,
    "失败": PipelineState.FAILED,
    "失败异常": PipelineState.FAILED,
}


def _normalize_pipeline_target_status(raw_status: str) -> str:
    text = _safe_text(raw_status)
    if not text:
        return ""
    if text in _PIPELINE_STAGE_ALIAS:
        return _PIPELINE_STAGE_ALIAS[text]

    normalized = canonical_pipeline_status(text)
    all_values = {
        PipelineState.QUEUED_REWRITE,
        PipelineState.REWRITE_RUNNING,
        PipelineState.REVIEW_READY,
        PipelineState.PUBLISH_READY,
        PipelineState.PUBLISH_RUNNING,
        PipelineState.PUBLISHED,
        PipelineState.REWRITE_FAILED,
        PipelineState.PUBLISH_FAILED,
        PipelineState.FAILED,
    }
    if normalized in all_values:
        return normalized
    return ""


def _publish_log_row(item: Dict) -> Dict:
    fields = item.get("fields", {}) or {}
    publish_status = _safe_text(
        fields.get("发布状态")
        or fields.get("状态")
        or fields.get("结果")
        or fields.get("流程状态")
    )
    source_url = _normalize_http_url(fields.get("文章 URL"))
    rewritten_doc = _normalize_doc_url(fields.get("改后文档链接")) or _normalize_http_url(fields.get("改后文档链接"))
    published_at = _pick_first_datetime(
        fields,
        ["发布时间", "更新时间", "创建时间", "同步时间"],
        fallback_item=item,
    )
    return {
        "record_id": item.get("record_id"),
        "title": _safe_text(fields.get("标题") or fields.get("原始标题")),
        "publish_status": publish_status,
        "result": _safe_text(fields.get("结果") or fields.get("发布结果")),
        "remark": _safe_text(fields.get("备注") or fields.get("失败原因")),
        "url": source_url,
        "rewritten_doc": rewritten_doc,
        "published_at": published_at,
    }


def _sort_rows_by_time(rows: List[Dict], key: str) -> List[Dict]:
    def _k(item: Dict) -> str:
        return _safe_text(item.get(key))
    return sorted(rows, key=_k, reverse=True)


def _import_legacy_workflow(account: Optional[Dict] = None, force: bool = False) -> Dict[str, object]:
    account = account or accounts.get_active()
    account_id = _account_scope(account)
    summary = {
        "pipeline_imported": 0,
        "publish_imported": 0,
        "inspiration_imported": 0,
        "pipeline_table_id": "",
        "publish_table_id": "",
        "inspiration_table_id": "",
        "used_feishu": False,
        "message": "",
    }

    need_pipeline = force or not workflow_store.has_pipeline_records(account_id)
    need_publish = force or not workflow_store.has_publish_logs(account_id)
    need_inspiration = force or not workflow_store.has_inspiration_records(account_id)
    if not need_pipeline and not need_publish and not need_inspiration:
        summary["message"] = "local store already populated"
        return summary

    feishu = _feishu_client(account)
    if not feishu._get_token():
        summary["message"] = "feishu auth unavailable"
        return summary

    summary["used_feishu"] = True

    if need_pipeline:
        table_name = _safe_text(account.get("feishu_pipeline_table")) or Config.FEISHU_PIPELINE_TABLE
        table_id = _find_table_id(feishu, table_name, ["自动化发布队列", "智能内容库"])
        summary["pipeline_table_id"] = table_id or ""
        if table_id:
            raw = feishu.list_records_all(table_id, max_items=1000)
            rows = [_pipeline_row(it) for it in (raw.get("items") or [])]
            summary["pipeline_imported"] = workflow_store.import_pipeline_rows(account_id, rows)

    if need_publish:
        table_name = _safe_text(account.get("feishu_publish_log_table")) or Config.FEISHU_PUBLISH_LOG_TABLE
        table_id = _find_table_id(feishu, table_name, ["发布记录", "发布日志"])
        summary["publish_table_id"] = table_id or ""
        if table_id:
            raw = feishu.list_records_all(table_id, max_items=1000)
            rows = [_publish_log_row(it) for it in (raw.get("items") or [])]
            summary["publish_imported"] = workflow_store.import_publish_rows(account_id, rows)

    if need_inspiration:
        table_name = _safe_text(account.get("feishu_inspiration_table")) or Config.FEISHU_INSPIRATION_TABLE
        table_id = _find_table_id(feishu, table_name, ["内容灵感库"])
        summary["inspiration_table_id"] = table_id or ""
        if table_id:
            raw = feishu.list_records_all(table_id, max_items=1000)
            rows = [_inspiration_row(it) for it in (raw.get("items") or [])]
            summary["inspiration_imported"] = workflow_store.import_inspiration_rows(account_id, rows)

    if summary["pipeline_imported"] or summary["publish_imported"] or summary["inspiration_imported"]:
        summary["message"] = "legacy feishu data imported to local database"
    else:
        summary["message"] = "no legacy feishu rows imported"
    return summary


def run_pipeline_once_job(source="manual", account_id: str = ""):
    account = _pick_account(account_id)
    _ensure_account_enabled(account)
    return _run_command_async(
        name=f"流水线单次巡检({source}) [{_safe_text(account.get('name'))}]",
        command=[PYTHON_BIN, "core/manager.py", "pipeline-once"],
        account=account,
    )


scheduler = Scheduler(run_pipeline_once_job)


def _extract_account_id(payload: Optional[Dict] = None) -> str:
    payload = payload or {}
    return _safe_text(payload.get("account_id") or request.args.get("account_id"))


@app.get("/api/health")
def api_health():
    active = accounts.get_active()
    return jsonify({
        "ok": True,
        "time": _now_str(),
        "project_root": PROJECT_ROOT,
        "python": PYTHON_BIN,
        "active_account": {
            "id": _safe_text(active.get("id")),
            "name": _safe_text(active.get("name")),
        },
        "defaults": {
            "role": _safe_text(active.get("pipeline_role")) or DEFAULT_ROLE,
            "model": _safe_text(active.get("pipeline_model")) or DEFAULT_MODEL,
            "batch": str(active.get("pipeline_batch_size") or DEFAULT_BATCH),
        },
    })


@app.get("/api/overview")
def api_overview():
    account_id = _extract_account_id()
    account = _pick_account(account_id)
    return jsonify(_overview(account))


@app.get("/api/accounts")
def api_accounts_list():
    state = accounts.dump()
    return jsonify({
        "ok": True,
        "active_account_id": state.get("active_account_id", ""),
        "items": state.get("accounts", []),
    })


@app.get("/api/accounts/<account_id>")
def api_accounts_get(account_id: str):
    item = accounts.get(account_id)
    if not item:
        return jsonify({"ok": False, "error": "account not found"}), 404
    return jsonify({"ok": True, "item": item})


@app.post("/api/accounts/upsert")
def api_accounts_upsert():
    payload = request.get_json(silent=True) or {}
    item = accounts.upsert(payload)
    return jsonify({"ok": True, "item": item, "active_account_id": accounts.dump().get("active_account_id", "")})


@app.post("/api/accounts/<account_id>/activate")
def api_accounts_activate(account_id: str):
    try:
        item = accounts.set_active(account_id)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "item": item, "active_account_id": accounts.dump().get("active_account_id", "")})


@app.post("/api/accounts/<account_id>/delete")
def api_accounts_delete(account_id: str):
    try:
        accounts.delete(account_id)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "active_account_id": accounts.dump().get("active_account_id", "")})


@app.get("/api/jobs")
def api_jobs():
    return jsonify({"ok": True, "items": jobs.list()})


@app.get("/api/jobs/<job_id>")
def api_job_detail(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "job not found"}), 404
    return jsonify({"ok": True, "item": job})


@app.get("/api/inspiration/list")
def api_inspiration_list():
    account = _pick_account(_extract_account_id())
    keyword = _safe_text(request.args.get("keyword")).lower()
    status = _safe_text(request.args.get("status"))
    limit = max(1, min(1000, int(request.args.get("limit", 300) or 300)))

    account_id = _account_scope(account)
    # 灵感库数据从本地数据库读取（已从飞书同步过来）
    rows = workflow_store.list_inspiration(account_id, status=status, keyword=keyword, limit=limit)
    inspiration_pref = _safe_text(account.get("feishu_inspiration_table")) or Config.FEISHU_INSPIRATION_TABLE

    return jsonify({
        "ok": True,
        "items": rows,
        "count": len(rows),
        "meta": {
            "table_name": inspiration_pref,
            "table_id": "",
            "limit": limit,
            "source": "local-db",
        },
        "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
    })


@app.post("/api/inspiration/<record_id>/delete")
def api_inspiration_delete(record_id):
    account_id = _extract_account_id()
    account = _pick_account(account_id)
    aid = _account_scope(account)
    try:
        _ensure_account_enabled(account)
        success = workflow_store.delete_inspiration(record_id, aid)
        if success:
            return jsonify({"ok": True, "message": "删除成功"})
        else:
            return jsonify({"ok": False, "error": "删除失败，记录不存在"}), 404
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/inspiration/<record_id>/retry")
def api_inspiration_retry(record_id):
    account_id = _extract_account_id()
    account = _pick_account(account_id)
    aid = _account_scope(account)
    try:
        _ensure_account_enabled(account)
        # 先查询原有记录，保留原有信息
        with workflow_store._connect() as conn:
            row = conn.execute(
                "SELECT * FROM inspiration_records WHERE record_id = ? AND account_id = ?",
                (record_id, aid)
            ).fetchone()
            if not row:
                return jsonify({"ok": False, "error": "重试失败，记录不存在"}), 404
            record = dict(row)
        # 重置记录状态为待分析，清除错误信息，保留原有URL和标题等重要字段
        success = workflow_store.upsert_inspiration({
            **record,
            "status": "待分析",
            "remark": "",
            "doc_url": "",
            "updated_at": _now_str()
        })
        if success:
            return jsonify({"ok": True, "message": "已提交重试，下次分析任务会重新处理"})
        else:
            return jsonify({"ok": False, "error": "重试失败"}), 500
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/inspiration/add")
def api_inspiration_add():
    account_id = _extract_account_id()
    account = _pick_account(account_id)
    aid = _account_scope(account)
    try:
        _ensure_account_enabled(account)
        payload = request.get_json(silent=True) or {}
        urls_input = payload.get("urls") or ""
        default_status = _safe_text(payload.get("default_status") or "待分析")

        # 支持数组和文本两种格式
        urls = []
        if isinstance(urls_input, list):
            # 数组格式，直接处理
            for url in urls_input:
                url = _safe_text(url).strip()
                if url:
                    urls.append({"title": "", "url": url})
        else:
            # 文本格式，按行分割
            urls_text = _safe_text(urls_input)
            for line in urls_text.split("\n"):
                url = _safe_text(line).strip()
                if url:
                    # 支持 "标题 url" 格式，也支持纯 url 格式
                    parts = url.split(None, 1)
                    if len(parts) >= 2 and parts[0].startswith("http"):
                        urls.append({"title": "", "url": url})
                    elif len(parts) >= 2:
                        urls.append({"title": parts[0], "url": parts[1]})
                    else:
                        urls.append({"title": "", "url": url})

        added = []
        for item in urls:
            url = _safe_text(item.get("url") or "")
            title = _safe_text(item.get("title") or "")
            if not url:
                continue
            # 提取 domain 作为默认标题
            if not title:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    title = parsed.netloc.replace("www.", "")
                except Exception:
                    title = "未命名文章"
            now = _now_str()
            record = {
                "title": title,
                "url": url,
                "doc_url": "",
                "status": default_status,
                "captured_at": now,
                "remark": "手动添加",
            }
            result = workflow_store.upsert_inspiration({**record, "account_id": aid})
            added.append(result)

        return jsonify({
            "ok": True,
            "added_count": len(added),
            "added": added,
            "message": f"成功添加 {len(added)} 篇文章到灵感库",
        })
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/inspiration/<record_id>/capture")
def api_inspiration_capture(record_id):
    account_id = _extract_account_id()
    account = _pick_account(account_id)
    aid = _account_scope(account)
    try:
        _ensure_account_enabled(account)
        # 获取灵感记录
        item = workflow_store.get_inspiration(record_id, aid)
        if not item:
            return jsonify({"ok": False, "error": "记录不存在"}), 404

        url = item.get("url") or ""
        if not url:
            return jsonify({"ok": False, "error": "记录缺少文章 URL，无法抓取"}), 400

        # 触发异步抓取任务：单篇文章处理
        role = _safe_text(account.get("pipeline_role")) or DEFAULT_ROLE
        model = _safe_text(account.get("pipeline_model")) or DEFAULT_MODEL

        job_id = _run_command_async(
            name=f"灵感抓取 - {item.get('title', record_id)} [{_safe_text(account.get('name'))}]",
            command=[PYTHON_BIN, "core/manager.py", url, role, model],
            account=account,
        )
        return jsonify({
            "ok": True,
            "job_id": job_id,
            "message": "已开始抓取，请到「发布日志」或「追踪中心」查看进度",
        })
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/inspiration/list-feishu")
def api_inspiration_list_feishu():
    # 保留旧接口用于直接从飞书读取
    account = _pick_account(_extract_account_id())
    keyword = _safe_text(request.args.get("keyword")).lower()
    status = _safe_text(request.args.get("status"))
    limit = max(1, min(1000, int(request.args.get("limit", 300) or 300)))

    feishu = _feishu_client(account)
    if not feishu._get_token():
        return jsonify({"ok": False, "error": "飞书鉴权失败，请检查当前账户参数"}), 400

    inspiration_pref = _safe_text(account.get("feishu_inspiration_table")) or Config.FEISHU_INSPIRATION_TABLE
    inspiration_id = _find_table_id(feishu, inspiration_pref, ["内容灵感库"])
    if not inspiration_id:
        return jsonify({
            "ok": True,
            "items": [],
            "count": 0,
            "meta": {"table_name": inspiration_pref, "table_id": ""},
            "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
        })

    raw = feishu.list_records_all(inspiration_id, max_items=limit)
    rows = [_inspiration_row(it) for it in (raw.get("items") or [])]

    if status:
        rows = [it for it in rows if _safe_text(it.get("status")) == status]
    if keyword:
        rows = [
            it for it in rows
            if keyword in _safe_text(it.get("title")).lower()
            or keyword in _safe_text(it.get("url")).lower()
            or keyword in _safe_text(it.get("doc_url")).lower()
        ]

    rows = _sort_rows_by_time(rows, "captured_at")

    return jsonify({
        "ok": True,
        "items": rows,
        "count": len(rows),
        "meta": {
            "table_name": inspiration_pref,
            "table_id": inspiration_id,
            "limit": limit,
            "has_more": bool(raw.get("has_more")),
        },
        "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
    })


@app.get("/api/pipeline/list")
def api_pipeline_list():
    account = _pick_account(_extract_account_id())
    account_id = _account_scope(account)
    keyword = _safe_text(request.args.get("keyword")).lower()
    status = _safe_text(request.args.get("status"))
    limit = max(1, min(1000, int(request.args.get("limit", 500) or 500)))
    migration = _import_legacy_workflow(account, force=False)
    rows = workflow_store.list_pipeline(account_id, status=status, keyword=keyword, limit=limit)

    return jsonify({
        "ok": True,
        "items": rows,
        "count": len(rows),
        "meta": {
            "source": "local",
            "workflow_db": _safe_text(Config.WORKFLOW_DB),
            "migration": migration,
            "limit": limit,
            "has_more": len(rows) >= limit,
        },
        "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
    })


@app.get("/api/pipeline/preview")
def api_pipeline_preview():
    account = _pick_account(_extract_account_id())
    account_id = _account_scope(account)
    record_id = _safe_text(request.args.get("record_id"))
    if not record_id:
        return jsonify({"ok": False, "error": "record_id is required"}), 400

    _import_legacy_workflow(account, force=False)
    row = workflow_store.get_pipeline(record_id, account_id=account_id)
    if not row:
        return jsonify({"ok": False, "error": "record not found"}), 404

    preview_source = row.get("rewritten_doc") or row.get("source_doc_url")
    preview_content = ""
    preview_title = row.get("title") or ""
    preview_error = ""
    if preview_source:
        feishu = _feishu_client(account)
        if feishu._get_token():
            doc = feishu.get_docx_content(preview_source)
            if doc:
                preview_title = _safe_text(doc.get("title")) or preview_title
                preview_content = _safe_text(doc.get("content_markdown") or doc.get("content_raw"))
        else:
            preview_error = "飞书鉴权失败，无法读取文档正文。"

    if len(preview_content) > 8000:
        preview_content = preview_content[:8000] + "\n\n...(已截断)"

    return jsonify({
        "ok": True,
        "item": {
            **row,
            "record_id": record_id,
            "title": preview_title or row.get("title") or "未命名标题",
            "status": _safe_text(canonical_pipeline_status(row.get("status"))),
            "preview_source": preview_source,
            "preview_content": preview_content,
            "preview_error": preview_error,
        },
        "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
    })


@app.post("/api/pipeline/update-status")
def api_pipeline_update_status():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    account_id = _account_scope(account)
    record_id = _safe_text(payload.get("record_id"))
    target_status = _normalize_pipeline_target_status(payload.get("status"))
    remark = _safe_text(payload.get("remark"))
    if not record_id:
        return jsonify({"ok": False, "error": "record_id is required"}), 400
    if not target_status:
        return jsonify({"ok": False, "error": "status is invalid"}), 400

    _import_legacy_workflow(account, force=False)
    record = workflow_store.get_pipeline(record_id, account_id=account_id)
    if not record:
        return jsonify({"ok": False, "error": "record not found"}), 404

    update_fields = {"status": target_status, "updated_at": _now_str()}
    if remark:
        update_fields["remark"] = remark
    elif payload.get("clear_remark") is True:
        update_fields["remark"] = ""

    updated = workflow_store.update_pipeline(record_id, **update_fields)
    if not updated:
        return jsonify({"ok": False, "error": "更新流水线状态失败"}), 400
    return jsonify({
        "ok": True,
        "item": updated,
        "status": target_status,
        "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
    })


@app.post("/api/pipeline/<record_id>/delete")
def api_pipeline_delete(record_id):
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    account_id = _account_scope(account)
    rid = _safe_text(record_id)
    if not rid:
        return jsonify({"ok": False, "error": "record_id is required"}), 400
    success = workflow_store.delete_pipeline(rid, account_id)
    return jsonify({"ok": success})


@app.get("/api/publish/list")
def api_publish_list():
    account = _pick_account(_extract_account_id())
    account_id = _account_scope(account)
    keyword = _safe_text(request.args.get("keyword")).lower()
    status = _safe_text(request.args.get("status"))
    limit = max(1, min(1000, int(request.args.get("limit", 500) or 500)))
    migration = _import_legacy_workflow(account, force=False)
    rows = workflow_store.list_publish_logs(account_id, status=status, keyword=keyword, limit=limit)

    return jsonify({
        "ok": True,
        "items": rows,
        "count": len(rows),
        "meta": {
            "source": "local",
            "workflow_db": _safe_text(Config.WORKFLOW_DB),
            "migration": migration,
            "limit": limit,
            "has_more": len(rows) >= limit,
        },
        "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
    })


@app.get("/api/media/preview")
def api_media_preview():
    file_token = _safe_text(request.args.get("file_token"))
    account_id = _safe_text(request.args.get("account_id"))
    file_name = _safe_text(request.args.get("name"))
    mime_type = _safe_text(request.args.get("mime_type")) or _guess_image_mimetype(file_name)
    if not file_token:
        return Response("missing file_token", status=400, mimetype="text/plain")

    account = _pick_account(account_id)
    feishu = _feishu_client(account)
    content = feishu._download_image(f"feishu://{file_token}")
    if not content:
        return Response("media not found", status=404, mimetype="text/plain")
    return Response(content, mimetype=mime_type)


@app.post("/api/actions/workflow-import")
def api_action_workflow_import():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    force = bool(payload.get("force", True))
    summary = _import_legacy_workflow(account, force=force)
    account_id = _account_scope(account)
    return jsonify({
        "ok": True,
        "summary": {
            **summary,
            "pipeline_total": sum(workflow_store.pipeline_status_counts(account_id).values()),
            "publish_total": len(workflow_store.list_publish_logs(account_id, limit=1000)),
            "inspiration_total": len(workflow_store.list_inspiration(account_id, limit=1000)),
        },
        "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
    })


@app.post("/api/actions/inspiration-scan")
def api_action_inspiration_scan():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    try:
        _ensure_account_enabled(account)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    account_id = _account_scope(account)
    job_id = _run_command_async(
        name=f"灵感库扫描与评估 [{_safe_text(account.get('name'))}]",
        command=[PYTHON_BIN, "core/manager_inspiration.py", "run-once", f"--account-id={account_id}"],
        account=account,
    )
    return jsonify({"ok": True, "job_id": job_id})


@app.post("/api/actions/pipeline-once")
def api_action_pipeline_once():
    payload = request.get_json(silent=True) or {}
    account_id = _extract_account_id(payload)
    account = _pick_account(account_id)
    try:
        _ensure_account_enabled(account)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    job_id = run_pipeline_once_job(source="manual", account_id=account_id)
    return jsonify({"ok": True, "job_id": job_id})


@app.post("/api/actions/full-inspection-once")
def api_action_full_inspection_once():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    try:
        _ensure_account_enabled(account)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    steps = [
        [PYTHON_BIN, "core/manager_inspiration.py"],
        [PYTHON_BIN, "core/manager.py", "pipeline-once"],
    ]
    job_id = _run_steps_async(
        name=f"全流程单次巡检(灵感→改写→发布) [{_safe_text(account.get('name'))}]",
        steps=steps,
        account=account,
    )
    return jsonify({"ok": True, "job_id": job_id})


@app.post("/api/actions/single-article")
def api_action_single_article():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    try:
        _ensure_account_enabled(account)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    url = _safe_text(payload.get("url"))
    role = _safe_text(payload.get("role")) or _safe_text(account.get("pipeline_role")) or DEFAULT_ROLE
    model = _safe_text(payload.get("model")) or _safe_text(account.get("pipeline_model")) or DEFAULT_MODEL
    if not url:
        return jsonify({"ok": False, "error": "url is required"}), 400

    job_id = _run_command_async(
        name=f"单篇文章即时处理 [{_safe_text(account.get('name'))}]",
        command=[PYTHON_BIN, "core/manager.py", url, role, model],
        account=account,
    )
    return jsonify({"ok": True, "job_id": job_id})


@app.post("/api/actions/full-demo")
def api_action_full_demo():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    try:
        _ensure_account_enabled(account)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    url = _safe_text(payload.get("url"))
    skip_publish = bool(payload.get("skip_publish", True))
    if not url:
        return jsonify({"ok": False, "error": "url is required"}), 400

    cmd = [PYTHON_BIN, "scripts/internal/demo_full_flow.py", "--url", url]
    if skip_publish:
        cmd.append("--skip-publish")

    job_id = _run_command_async(
        name=f"全流程 Demo [{_safe_text(account.get('name'))}]",
        command=cmd,
        account=account,
    )
    return jsonify({"ok": True, "job_id": job_id})


@app.get("/api/wechat/status")
def api_wechat_status():
    account = _pick_account(_extract_account_id())
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.status()
        state = result.get("state") or {}
        if bool(state.get("qr_image_exists")):
            result["qr_image_url"] = f"/api/wechat/qr-image?account_id={_safe_text(account.get('id'))}&t={int(time.time())}"
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/api/wechat/qr-image")
def api_wechat_qr_image():
    account = _pick_account(_extract_account_id())
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        qr_path = svc.get_qr_image_path()
        status = None
        if not qr_path:
            status = svc.status()
            qr_path = svc.get_qr_image_path(runtime=status.get("runtime"))
        if qr_path:
            return send_file(str(qr_path), mimetype=_guess_image_mimetype(qr_path.name, fallback="image/png"), conditional=False)

        return Response("qr image not ready", status=404, mimetype="text/plain")
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/wechat/list-mp")
def api_wechat_list_mp():
    account = _pick_account(_extract_account_id())
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.list_mps()
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/api/wechat/list-articles")
def api_wechat_list_articles():
    account = _pick_account(_extract_account_id())
    mp_id = _safe_text(request.args.get("mp_id"))
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.list_articles(mp_id=mp_id, limit=60)
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/wechat/search-mp")
def api_wechat_search_mp():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    keyword = _safe_text(payload.get("keyword"))
    limit = int(payload.get("limit", 10) or 10)
    offset = int(payload.get("offset", 0) or 0)
    if not keyword:
        return jsonify({"ok": False, "error": "keyword is required"}), 400
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.search_mp(keyword=keyword, limit=limit, offset=offset)
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/wechat/add-mp")
def api_wechat_add_mp():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    keyword = _safe_text(payload.get("keyword"))
    pick = int(payload.get("pick", 1) or 1)
    limit = int(payload.get("limit", 10) or 10)
    offset = int(payload.get("offset", 0) or 0)
    if not keyword:
        return jsonify({"ok": False, "error": "keyword is required"}), 400
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.add_mp(keyword=keyword, pick=pick, limit=limit, offset=offset)
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/actions/wechat-login")
def api_action_wechat_login():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    wait = bool(payload.get("wait", True))
    qr_display = _safe_text(payload.get("qr_display") or "none")
    timeout = int(payload.get("timeout", 180) or 180)
    token_wait_timeout = int(payload.get("token_wait_timeout", 20) or 20)
    thread_join_timeout = int(payload.get("thread_join_timeout", 8) or 8)
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.login(
            wait=wait,
            qr_display=qr_display,
            timeout=max(30, timeout),
            token_wait_timeout=max(10, token_wait_timeout),
            thread_join_timeout=max(5, thread_join_timeout),
        )
        state = result.get("state") or {}
        if bool(result.get("qr_image_exists") or state.get("qr_image_exists")):
            result["qr_image_url"] = f"/api/wechat/qr-image?account_id={_safe_text(account.get('id'))}&t={int(time.time())}"
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/actions/wechat-pull-articles")
def api_action_wechat_pull_articles():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    mp_id = _safe_text(payload.get("mp_id"))
    pages = int(payload.get("pages", 1) or 1)
    mode = _safe_text(payload.get("mode") or "api")
    with_content = bool(payload.get("with_content", False))
    if not mp_id:
        return jsonify({"ok": False, "error": "mp_id is required"}), 400
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.pull_articles(mp_id=mp_id, pages=max(1, pages), mode=mode, with_content=with_content)
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/actions/wechat-sync-inspiration")
def api_action_wechat_sync_inspiration():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    mp_id = _safe_text(payload.get("mp_id"))
    limit = int(payload.get("limit", 20) or 20)
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.sync_articles_to_inspiration(mp_id=mp_id, limit=max(1, limit))
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/actions/wechat-full-flow")
def api_action_wechat_full_flow():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    mp_id = _safe_text(payload.get("mp_id"))
    keyword = _safe_text(payload.get("keyword"))
    pick = int(payload.get("pick", 1) or 1)
    pages = int(payload.get("pages", 1) or 1)
    mode = _safe_text(payload.get("mode") or "api")
    with_content = bool(payload.get("with_content", False))
    content_limit = int(payload.get("content_limit", 10) or 10)
    sync_limit = int(payload.get("sync_limit", 20) or 20)
    if not mp_id and not keyword:
        return jsonify({"ok": False, "error": "mp_id 或 keyword 至少提供一个"}), 400
    try:
        _ensure_account_enabled(account)
        svc = _wechat_service(account)
        result = svc.full_flow(
            mp_id=mp_id,
            keyword=keyword,
            pick=max(1, pick),
            pages=max(1, pages),
            mode=mode,
            with_content=with_content,
            content_limit=max(1, content_limit),
            sync_limit=max(1, sync_limit),
        )
        result.update({
            "account": {
                "id": _safe_text(account.get("id")),
                "name": _safe_text(account.get("name")),
            }
        })
        return jsonify(result)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/api/scheduler")
def api_scheduler_status():
    active = accounts.get_active()
    return jsonify({
        "ok": True,
        "scheduler": scheduler.status(),
        "active_account": {
            "id": _safe_text(active.get("id")),
            "name": _safe_text(active.get("name")),
        },
    })


@app.post("/api/scheduler/start")
def api_scheduler_start():
    payload = request.get_json(silent=True) or {}
    minutes = int(payload.get("minutes", 30))
    scheduler.start(minutes)
    return jsonify({"ok": True, "scheduler": scheduler.status()})


@app.post("/api/scheduler/stop")
def api_scheduler_stop():
    scheduler.stop()
    return jsonify({"ok": True, "scheduler": scheduler.status()})


@app.get("/tools/huasheng")
def ui_huasheng_redirect():
    return redirect("/tools/huasheng/", code=302)


@app.get("/tools/huasheng/")
def ui_huasheng_index():
    if not HUASHENG_EDITOR_DIR.exists():
        return Response("huasheng_editor not found", mimetype="text/plain", status=404)
    resp = send_from_directory(HUASHENG_EDITOR_DIR, "index.html", max_age=0)
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


@app.get("/tools/huasheng/<path:filename>")
def ui_huasheng_assets(filename: str):
    if not HUASHENG_EDITOR_DIR.exists():
        return Response("huasheng_editor not found", mimetype="text/plain", status=404)
    resp = send_from_directory(HUASHENG_EDITOR_DIR, filename, max_age=0)
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


@app.get("/")
def ui_home():
    if not VUE_INDEX_PATH.exists():
        message = (
            "Vue 管理后台尚未构建。请先进入 frontend/admin 执行 npm install && npm run build，"
            "或直接运行 ./run_admin.sh 让脚本自动完成前端构建。"
        )
        return Response(message, mimetype="text/plain", status=503)
    resp = Response(VUE_INDEX_PATH.read_text(encoding="utf-8"), mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


@app.get("/vue")
def ui_vue():
    if not VUE_INDEX_PATH.exists():
        message = (
            "Vue 管理后台尚未构建。请先进入 frontend/admin 执行 npm install && npm run build，"
            "或直接运行 ./run_admin.sh 让脚本自动完成前端构建。"
        )
        return Response(message, mimetype="text/plain", status=503)
    resp = Response(VUE_INDEX_PATH.read_text(encoding="utf-8"), mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


@app.get("/admin-assets/<path:filename>")
def ui_vue_assets(filename: str):
    if not VUE_DIST_DIR.exists():
        return Response("Vue assets not built", mimetype="text/plain", status=404)
    resp = send_from_directory(VUE_DIST_DIR, filename, max_age=0)
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


@app.get("/favicon.ico")
def ui_favicon():
    # Vue dist does not always include favicon; avoid noisy 404 in browser logs.
    return Response(status=204)


if __name__ == "__main__":
    port = int(os.getenv("ADMIN_PORT", "8701"))
    host = os.getenv("ADMIN_HOST", "127.0.0.1")
    print(f"🚀 AutoInfo 管理后台启动中: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
