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

import requests
from flask import Flask, jsonify, request, Response, send_from_directory, send_file, redirect

from admin_accounts import AccountStore
from config import Config
from modules.feishu import FeishuBitable
from modules.state_machine import PipelineState, canonical_pipeline_status
from modules.workflow_store import WorkflowStore
from modules.wechat_ingest_service import WechatIngestService
from modules.publisher import WeChatPublisher


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


def _run_plugin_async(name: str, plugin_type: str, record_id: str, params: dict = None, account: Optional[Dict] = None):
    """在线程中直接执行插件，替代子进程调用"""
    picked = account or accounts.get_active()
    accounts.mark_runtime(_safe_text(picked.get("id")))
    job_id = jobs.create(name, [], account=picked)

    def _worker():
        jobs.patch(job_id, status="running", started_at=_now_str())
        jobs.append_log(job_id, f"[{_now_str()}] START {name}")
        jobs.append_log(job_id, f"[{_now_str()}] ACCOUNT: {_safe_text(picked.get('name'))} ({_safe_text(picked.get('id'))})")
        jobs.append_log(job_id, f"[{_now_str()}] PLUGIN: {plugin_type} | RECORD: {record_id}")
        try:
            from modules.plugins import get_plugin
            plugin = get_plugin(plugin_type, workflow_store, _account_scope(picked))
            if not plugin:
                raise ValueError(f"Unknown plugin type: {plugin_type}")
            result = plugin.execute(record_id, **(params or {}))
            if result.success:
                jobs.patch(job_id, status="success", return_code=0, ended_at=_now_str())
                jobs.append_log(job_id, f"[{_now_str()}] SUCCESS: {result.message}")
            else:
                jobs.patch(job_id, status="failed", return_code=1, ended_at=_now_str())
                jobs.append_log(job_id, f"[{_now_str()}] FAILED: {result.message}")
        except Exception as e:
            jobs.patch(job_id, status="failed", return_code=-1, ended_at=_now_str())
            jobs.append_log(job_id, f"[{_now_str()}] EXCEPTION: {e}")
        jobs.append_log(job_id, f"[{_now_str()}] END")

    threading.Thread(target=_worker, daemon=True).start()
    return job_id


def _run_capture_async(name: str, record_id: str, url: str, account: Optional[Dict] = None):
    """在线程中直接执行文章采集，替代子进程调用 capture_article.py"""
    picked = account or accounts.get_active()
    accounts.mark_runtime(_safe_text(picked.get("id")))
    job_id = jobs.create(name, [], account=picked)

    def _worker():
        jobs.patch(job_id, status="running", started_at=_now_str())
        jobs.append_log(job_id, f"[{_now_str()}] START {name}")
        try:
            from modules.collector import ContentCollector
            collector = ContentCollector()
            article = collector.collect(url)
            workflow_store.save_article_content(
                record_id=record_id,
                account_id=_account_scope(picked),
                original_html=article.get("content_html", ""),
                original_text=article.get("content_text", ""),
                original_json=article
            )
            workflow_store.update_inspiration(record_id, status="采集完成", updated_at=_now_str())
            jobs.patch(job_id, status="success", return_code=0, ended_at=_now_str())
            jobs.append_log(job_id, f"[{_now_str()}] SUCCESS: 采集完成 {article.get('title', '')[:50]}")
        except Exception as e:
            workflow_store.update_inspiration(record_id, status="采集失败", remark=str(e), updated_at=_now_str())
            jobs.patch(job_id, status="failed", return_code=-1, ended_at=_now_str())
            jobs.append_log(job_id, f"[{_now_str()}] EXCEPTION: {e}")
        jobs.append_log(job_id, f"[{_now_str()}] END")

    threading.Thread(target=_worker, daemon=True).start()
    return job_id


def _run_manager_async(name: str, action: str, params: dict = None, account: Optional[Dict] = None):
    """在线程中直接执行 manager 方法，替代子进程调用"""
    picked = account or accounts.get_active()
    accounts.mark_runtime(_safe_text(picked.get("id")))
    job_id = jobs.create(name, [], account=picked)

    def _worker():
        jobs.patch(job_id, status="running", started_at=_now_str())
        jobs.append_log(job_id, f"[{_now_str()}] START {name}")
        try:
            account_id = _account_scope(picked)
            if action == "inspiration-scan":
                from core.manager_inspiration import InspirationManager
                manager = InspirationManager(account_id=account_id)
                result = manager.run_once()
                jobs.append_log(job_id, f"[{_now_str()}] 分析完成: {result.get('analyzed', 0)} 篇")
            elif action == "pipeline-once":
                from core.manager import AutoPlatformManager
                manager = AutoPlatformManager(account_id=account_id)
                result = manager.run_pipeline_once(batch_size=params.get("batch_size", 3) if params else 3)
                jobs.append_log(job_id, f"[{_now_str()}] 处理完成: {result.get('processed', 0)} 条")
            elif action == "single-article":
                from core.manager import AutoPlatformManager
                manager = AutoPlatformManager(account_id=account_id)
                result = manager.run_full_flow(
                    params.get("url"),
                    params.get("role", "tech_expert"),
                    params.get("model", "auto")
                )
                jobs.append_log(job_id, f"[{_now_str()}] 全流程: {'成功' if result.get('success') else '失败'}")
            jobs.patch(job_id, status="success", return_code=0, ended_at=_now_str())
        except Exception as e:
            jobs.patch(job_id, status="failed", return_code=-1, ended_at=_now_str())
            jobs.append_log(job_id, f"[{_now_str()}] EXCEPTION: {e}")
        jobs.append_log(job_id, f"[{_now_str()}] END")

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

    # 计算汇总数据（前端期望的格式）
    total_articles = len(inspiration_items)
    pending = inspiration_status.get('待采集', 0) + inspiration_status.get('待改写', 0) + inspiration_status.get('待发布', 0)
    processing = inspiration_status.get('采集中', 0) + inspiration_status.get('改写中', 0) + inspiration_status.get('发布中', 0)
    failed = inspiration_status.get('采集失败', 0) + inspiration_status.get('改写失败', 0) + inspiration_status.get('发布失败', 0)
    skipped = inspiration_status.get('已跳过', 0)
    published = inspiration_status.get('已发布', 0)
    completed = inspiration_status.get('已改写', 0) + published
    
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
            "pipeline_total": 0,
            "workflow_backend": "local",
            "workflow_db": _safe_text(Config.WORKFLOW_DB),
            "migration": migration,
            "updated_at": _now_str(),
        },
        "summary": {
            "total_articles": total_articles,
            "pending": pending,
            "processing": processing,
            "failed": failed,
            "skipped": skipped,
            "published": published,
            "completed": completed,
        },
        "state_groups": {
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
        },
        "status_breakdown": inspiration_status,
        "stats": {
            "inspiration_status": inspiration_status,
            "pipeline_status": {},
        },
        "recent": {
            "inspiration": recent_inspiration,
            "pipeline": [],
        },
        "recent_items": recent_inspiration,  # 兼容旧字段
    }
    # 飞书导入已废弃，本地数据库是唯一数据源
    if not workflow_store.has_inspiration_records(account_id):
        warning = (warning + "\n" if warning else "") + "本地灵感库为空，请添加文章URL开始采集。"
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
    """飞书数据导入已废弃 - 保留函数签名用于兼容，但不再执行导入"""
    account = account or accounts.get_active()
    account_id = _account_scope(account)
    return {
        "pipeline_imported": 0,
        "publish_imported": 0,
        "inspiration_imported": 0,
        "pipeline_table_id": "",
        "publish_table_id": "",
        "inspiration_table_id": "",
        "used_feishu": False,
        "message": "飞书导入已废弃，数据已全部迁移到本地 SQLite",
    }


def run_pipeline_once_job(source="manual", account_id: str = ""):
    """调度器回调：直接在线程中执行流水线，替代子进程"""
    account = _pick_account(account_id)
    _ensure_account_enabled(account)
    return _run_manager_async(
        name=f"流水线单次巡检({source}) [{_safe_text(account.get('name'))}]",
        action="pipeline-once",
        params={"batch_size": int(account.get("pipeline_batch_size") or DEFAULT_BATCH)},
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
    return jsonify({"ok": True, "item": item, "active_account_id": accounts.get_active().get("id", "") if accounts.get_active() else ""})


@app.post("/api/accounts/<account_id>/activate")
def api_accounts_activate(account_id: str):
    try:
        item = accounts.activate(account_id)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "item": item, "active_account_id": accounts.get_active().get("id", "") if accounts.get_active() else ""})


@app.post("/api/accounts/<account_id>/delete")
def api_accounts_delete(account_id: str):
    try:
        accounts.delete(account_id)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "active_account_id": accounts.get_active().get("id", "") if accounts.get_active() else ""})


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

        # 直接在线程中执行采集，替代子进程
        job_id = _run_capture_async(
            name=f"文章采集 - {item.get('title', record_id)} [{_safe_text(account.get('name'))}]",
            record_id=record_id,
            url=url,
            account=account,
        )
        return jsonify({
            "ok": True,
            "job_id": job_id,
            "message": "已开始抓取，请到「任务中心」查看进度",
        })
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/inspiration/<record_id>/rewrite")
def api_inspiration_rewrite(record_id: str):
    """执行AI改写 - 异步执行"""
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    account_id = _account_scope(account)
    
    role = _safe_text(payload.get("role")) or DEFAULT_ROLE
    model = _safe_text(payload.get("model")) or DEFAULT_MODEL
    
    # 获取记录信息用于任务名称
    item = workflow_store.get_inspiration(record_id, account_id)
    title = item.get("title", record_id) if item else record_id
    
    # 直接在线程中执行改写插件，替代子进程
    job_id = _run_plugin_async(
        name=f"AI改写 - {title} [{_safe_text(account.get('name'))}]",
        plugin_type="ai_rewrite",
        record_id=record_id,
        params={"role": role, "model": model},
        account=account,
    )
    
    return jsonify({
        "ok": True,
        "job_id": job_id,
        "message": "AI改写任务已提交，请在任务中心查看进度",
    })


@app.get("/api/inspiration/list-feishu")
def api_inspiration_list_feishu():
    """飞书直接读取已废弃，重定向到本地数据库"""
    return api_inspiration_list()


@app.get("/api/publish/list")
def api_publish_list():
    account = _pick_account(_extract_account_id())
    account_id = _account_scope(account)
    keyword = _safe_text(request.args.get("keyword")).lower()
    status = _safe_text(request.args.get("status"))
    limit = max(1, min(1000, int(request.args.get("limit", 500) or 500)))
    rows = workflow_store.list_publish_logs(account_id, status=status, keyword=keyword, limit=limit)

    return jsonify({
        "ok": True,
        "items": rows,
        "count": len(rows),
        "meta": {
            "source": "local",
            "workflow_db": _safe_text(Config.WORKFLOW_DB),
            "limit": limit,
            "has_more": len(rows) >= limit,
        },
        "account": {"id": _safe_text(account.get("id")), "name": _safe_text(account.get("name"))},
    })


@app.post("/api/publish/draft")
def api_publish_draft():
    """发布草稿到微信公众号"""
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    account_id = _account_scope(account)
    record_id = _safe_text(payload.get("record_id"))
    title = _safe_text(payload.get("title"))
    
    if not record_id:
        return jsonify({"ok": False, "error": "record_id is required"}), 400
    
    # 获取灵感记录
    inspiration = workflow_store.get_inspiration(record_id, account_id)
    if not inspiration:
        return jsonify({"ok": False, "error": "inspiration record not found"}), 404
    
    # 获取文章内容
    article_content = workflow_store.get_article_content(record_id, account_id)
    if not article_content:
        return jsonify({"ok": False, "error": "article content not found, please rewrite first"}), 400
    
    # 优先从 rewritten_html 字段读取，如果不存在则从 rewritten_data 字典读取
    content_html = article_content.get("rewritten_html", "")
    content_text = article_content.get("rewritten_text", "")
    
    # 兼容旧数据：如果 rewritten_html 为空，尝试从 rewritten_data 读取
    if not content_html:
        rewritten_data = article_content.get("rewritten_data", {})
        content_html = rewritten_data.get("content_html", "")
        content_text = rewritten_data.get("content_text", "") or rewritten_data.get("content", "")
    
    if not content_html:
        return jsonify({"ok": False, "error": "rewritten content is empty, please rewrite first"}), 400
    
    # 获取账户配置
    wechat_appid = _safe_text(account.get("wechat_appid") or Config.WECHAT_APPID)
    wechat_secret = _safe_text(account.get("wechat_secret") or Config.WECHAT_SECRET)
    wechat_author = _safe_text(account.get("wechat_author") or Config.WECHAT_AUTHOR or "W 小龙虾")
    
    if not wechat_appid or not wechat_secret:
        return jsonify({"ok": False, "error": "WeChat appid/secret not configured"}), 400
    
    # 创建发布任务
    job_id = str(uuid.uuid4())[:12]
    
    def _do_publish():
        try:
            _update_job(job_id, {"status": "running", "progress": 10, "message": "初始化发布器..."})
            publisher = WeChatPublisher(wechat_appid, wechat_secret, wechat_author)
            
            # 获取封面图
            _update_job(job_id, {"status": "running", "progress": 20, "message": "处理封面图..."})
            thumb_media_id = None
            cover_url = inspiration.get("cover_url", "")
            
            # 如果 inspiration 中有 cover_media_id，直接使用
            if inspiration.get("cover_media_id"):
                thumb_media_id = inspiration.get("cover_media_id")
                _update_job(job_id, {"status": "running", "progress": 30, "message": f"使用已有封面: {thumb_media_id}"})
            elif cover_url:
                # 上传封面图
                _update_job(job_id, {"status": "running", "progress": 30, "message": "上传封面图..."})
                thumb_media_id = publisher.upload_from_url(cover_url)
            
            # 处理正文图片（同时获取第一张图片作为封面）
            _update_job(job_id, {"status": "running", "progress": 40, "message": "处理正文图片..."})
            processed_html, first_image_media_id = _process_article_images(content_html, publisher, job_id)
            
            # 如果没有封面图，使用文章中的第一张图片
            if not thumb_media_id and first_image_media_id:
                thumb_media_id = first_image_media_id
                _update_job(job_id, {"status": "running", "progress": 35, "message": f"使用文章图片作为封面: {thumb_media_id}"})
            elif not thumb_media_id:
                _update_job(job_id, {"status": "running", "progress": 35, "message": "警告: 无封面图，尝试使用默认封面"})
            
            # 生成摘要
            _update_job(job_id, {"status": "running", "progress": 70, "message": "生成摘要..."})
            digest = content_text[:100] + "..." if len(content_text) > 100 else content_text
            
            # 发布草稿
            _update_job(job_id, {"status": "running", "progress": 80, "message": "创建微信草稿..."})
            use_title = title or inspiration.get("title", "未命名标题")
            media_id = publisher.publish_draft(use_title, processed_html, digest, thumb_media_id)
            
            if not media_id:
                raise Exception("Failed to create WeChat draft")
            
            # 记录发布日志
            _update_job(job_id, {"status": "running", "progress": 90, "message": "记录发布日志..."})
            publish_record = {
                "record_id": str(uuid.uuid4())[:16],
                "pipeline_record_id": record_id,
                "account_id": account_id,
                "title": use_title,
                "publish_status": "已发布",
                "result": "草稿创建成功",
                "url": inspiration.get("url", ""),
                "draft_id": media_id,
                "published_at": _now_str(),
            }
            workflow_store.add_publish_log(publish_record)
            
            # 更新灵感记录状态
            workflow_store.update_inspiration(record_id, status="已发布", updated_at=_now_str())
            
            _update_job(job_id, {
                "status": "completed",
                "progress": 100,
                "message": f"发布成功! Media ID: {media_id}",
                "result": {"media_id": media_id, "title": use_title}
            })
            
        except Exception as e:
            error_msg = str(e)
            _update_job(job_id, {"status": "failed", "progress": 0, "message": f"发布失败: {error_msg}"})
            # 记录失败日志
            try:
                workflow_store.add_publish_log({
                    "record_id": str(uuid.uuid4())[:16],
                    "pipeline_record_id": record_id,
                    "account_id": account_id,
                    "title": title or inspiration.get("title", "未命名标题"),
                    "publish_status": "发布失败",
                    "result": error_msg,
                    "url": inspiration.get("url", ""),
                    "draft_id": "",
                    "published_at": _now_str(),
                })
            except Exception:
                pass
    
    # 启动后台任务
    job_id = jobs.create(name=f"发布草稿: {title or inspiration.get('title', '未命名')}", command=[], account=account)
    jobs.patch(job_id, status="running", progress=0, message="任务已创建")
    threading.Thread(target=_do_publish, daemon=True).start()
    
    return jsonify({"ok": True, "job_id": job_id})


def _process_article_images(content_html: str, publisher: WeChatPublisher, job_id: str) -> tuple:
    """处理文章中的图片，上传到微信服务器
    返回: (处理后的HTML, 第一张图片的media_id用于封面)"""
    import re
    import tempfile
    
    # 查找所有图片标签
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
    first_image_bytes = None
    
    def replace_image(match):
        nonlocal first_image_bytes
        src = match.group(1)
        # 跳过已经是微信图片的
        if "mmbiz.qpic.cn" in src or "mmbizurl.cn" in src:
            return match.group(0)
        
        try:
            image_bytes = None
            
            # 处理本地文件路径
            if src.startswith('/local_images/') or src.startswith('/output/'):
                # 本地文件路径，尝试多个可能的位置
                local_path = None
                possible_paths = [
                    PROJECT_ROOT + src,
                    PROJECT_ROOT + '/output' + src,
                    PROJECT_ROOT + src.replace('/local_images/', '/output/article_images/'),
                    os.path.join(PROJECT_ROOT, 'output', src.lstrip('/')),
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        local_path = path
                        break
                
                if local_path:
                    with open(local_path, 'rb') as f:
                        image_bytes = f.read()
                    print(f"📷 读取本地图片: {src} (来自 {local_path})")
                else:
                    print(f"⚠️ 本地图片不存在: {src}")
            else:
                # 网络图片，使用 HTTP 下载
                resp = requests.get(src, timeout=30)
                if resp.status_code == 200:
                    image_bytes = resp.content
                    print(f"📷 下载网络图片: {src}")
            
            # 保存第一张图片用于封面
            if image_bytes and first_image_bytes is None:
                first_image_bytes = image_bytes
            
            # 上传到微信
            if image_bytes:
                wx_url = publisher.upload_article_image(image_bytes)
                if wx_url:
                    print(f"✅ 图片上传成功: {wx_url}")
                    return match.group(0).replace(src, wx_url)
                else:
                    print(f"❌ 图片上传失败: {src}")
        except Exception as e:
            print(f"⚠️ 图片处理失败 {src}: {e}")
        
        return match.group(0)
    
    processed_html = re.sub(img_pattern, replace_image, content_html)
    
    # 如果有第一张图片，上传作为封面
    thumb_media_id = None
    if first_image_bytes:
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(first_image_bytes)
                temp_path = f.name
            thumb_media_id = publisher.upload_material(temp_path, 'image')
            os.unlink(temp_path)
            print(f"✅ 封面图上传成功: {thumb_media_id}")
        except Exception as e:
            print(f"⚠️ 封面图上传失败: {e}")
    
    return processed_html, thumb_media_id


def _update_job(job_id: str, updates: dict):
    """更新任务状态"""
    jobs.patch(job_id, **updates)


@app.get("/api/media/preview")
def api_media_preview():
    """飞书媒体预览已废弃 - 本地图片请使用 /local_images/<path>"""
    return Response("飞书媒体预览已废弃，数据已全部迁移到本地存储", status=410, mimetype="text/plain")


@app.post("/api/actions/workflow-import")
def api_action_workflow_import():
    """飞书数据导入已废弃，保留接口用于兼容性提示"""
    account = _pick_account(_extract_account_id())
    account_id = _account_scope(account)
    return jsonify({
        "ok": True,
        "summary": {
            "pipeline_imported": 0,
            "publish_imported": 0,
            "inspiration_imported": 0,
            "message": "飞书导入已废弃，数据已全部迁移到本地 SQLite",
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
    job_id = _run_manager_async(
        name=f"灵感库扫描与评估 [{_safe_text(account.get('name'))}]",
        action="inspiration-scan",
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
    job_id = _run_manager_async(
        name=f"流水线单次巡检 [{_safe_text(account.get('name'))}]",
        action="pipeline-once",
        params={"batch_size": int(account.get("pipeline_batch_size") or DEFAULT_BATCH)},
        account=account,
    )
    return jsonify({"ok": True, "job_id": job_id})


@app.post("/api/actions/full-inspection-once")
def api_action_full_inspection_once():
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    try:
        _ensure_account_enabled(account)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    job_id = _run_manager_async(
        name=f"全流程单次巡检(灵感→改写→发布) [{_safe_text(account.get('name'))}]",
        action="pipeline-once",
        params={"batch_size": int(account.get("pipeline_batch_size") or DEFAULT_BATCH)},
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

    job_id = _run_manager_async(
        name=f"单篇文章即时处理 [{_safe_text(account.get('name'))}]",
        action="single-article",
        params={"url": url, "role": role, "model": model},
        account=account,
    )
    return jsonify({"ok": True, "job_id": job_id})


@app.post("/api/actions/full-demo")
def api_action_full_demo():
    """全流程Demo - 直接调用新管理器，替代子进程"""
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

    job_id = _run_manager_async(
        name=f"全流程 Demo [{_safe_text(account.get('name'))}]",
        action="single-article",
        params={"url": url, "role": DEFAULT_ROLE, "model": DEFAULT_MODEL},
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



@app.get("/api/plugin-tasks")
def api_list_plugin_tasks():
    """获取插件任务列表"""
    account_id = request.args.get("account_id", "")
    record_id = request.args.get("record_id", "")
    plugin_type = request.args.get("plugin_type", "")
    status = request.args.get("status", "")
    limit = int(request.args.get("limit", 100))

    tasks = workflow_store.get_plugin_tasks(
        record_id=record_id,
        account_id=account_id,
        plugin_type=plugin_type,
        status=status,
        limit=limit,
    )

    return jsonify({
        "ok": True,
        "tasks": tasks,
        "count": len(tasks),
    })


@app.get("/api/plugin-tasks/<task_id>")
def api_get_plugin_task(task_id: str):
    """获取单个插件任务详情"""
    tasks = workflow_store.get_plugin_tasks(
        plugin_type=None,
        status=None,
        limit=1
    )
    # 这里需要添加按task_id查询的方法，暂时用list过滤
    task = next((t for t in tasks if t.get("task_id") == task_id), None)

    if not task:
        return jsonify({"ok": False, "error": "Task not found"}), 404

    return jsonify({"ok": True, "task": task})


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


# ==================== 新插件 API ====================

@app.get("/api/plugins")
def api_list_plugins():
    """列出所有可用插件"""
    from modules.plugins import list_plugins
    return jsonify({
        "ok": True,
        "plugins": list_plugins()
    })


@app.post("/api/plugins/ai-score")
def api_plugin_ai_score():
    """执行AI评分插件"""
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    account_id = _account_scope(account)
    record_id = _safe_text(payload.get("record_id"))
    
    if not record_id:
        return jsonify({"ok": False, "error": "record_id is required"}), 400
    
    from modules.plugins import AIScorePlugin
    plugin = AIScorePlugin(workflow_store, account_id)
    result = plugin.execute(record_id)
    
    return jsonify({
        "ok": result.success,
        "message": result.message,
        "data": result.data
    })


@app.post("/api/plugins/ai-rewrite")
def api_plugin_ai_rewrite():
    """执行AI改写插件"""
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    account_id = _account_scope(account)
    record_id = _safe_text(payload.get("record_id"))
    role = _safe_text(payload.get("role")) or "tech_expert"
    model = _safe_text(payload.get("model")) or "auto"
    
    if not record_id:
        return jsonify({"ok": False, "error": "record_id is required"}), 400
    
    from modules.plugins import AIRewritePlugin
    plugin = AIRewritePlugin(workflow_store, account_id)
    result = plugin.execute(record_id, role=role, model=model)
    
    return jsonify({
        "ok": result.success,
        "message": result.message,
        "data": result.data
    })


@app.post("/api/plugins/publish")
def api_plugin_publish():
    """执行发布插件"""
    payload = request.get_json(silent=True) or {}
    account = _pick_account(_extract_account_id(payload))
    account_id = _account_scope(account)
    record_id = _safe_text(payload.get("record_id"))
    
    if not record_id:
        return jsonify({"ok": False, "error": "record_id is required"}), 400
    
    from modules.plugins import PublishPlugin
    plugin = PublishPlugin(workflow_store, account_id)
    result = plugin.execute(record_id)
    
    return jsonify({
        "ok": result.success,
        "message": result.message,
        "data": result.data
    })


@app.get("/api/articles/<record_id>/content")
def api_get_article_content(record_id: str):
    """获取文章内容"""
    account = _pick_account(_extract_account_id())
    account_id = _account_scope(account)
    
    content = workflow_store.get_article_content(record_id, account_id)
    if not content:
        return jsonify({"ok": False, "error": "Article content not found"}), 404
    
    return jsonify({
        "ok": True,
        "content": content
    })


@app.get("/local_images/<path:filename>")
def serve_local_images(filename: str):
    """提供本地图片文件服务 (兼容旧路径，实际指向 article_images)"""
    article_images_dir = Path(PROJECT_ROOT) / "output" / "article_images"
    if not article_images_dir.exists():
        return Response("Images directory not found", status=404, mimetype="text/plain")
    
    # 安全路径检查，防止目录遍历
    try:
        requested_path = (article_images_dir / filename).resolve()
        if not str(requested_path).startswith(str(article_images_dir.resolve())):
            return Response("Invalid path", status=403, mimetype="text/plain")
    except Exception:
        return Response("Invalid path", status=403, mimetype="text/plain")
    
    if not requested_path.exists():
        return Response("Image not found", status=404, mimetype="text/plain")
    
    return send_from_directory(article_images_dir, filename)


@app.get("/api/articles/<record_id>/preview-wechat")
def api_preview_wechat(record_id: str):
    """预览文章内容（返回HTML）"""
    account = _pick_account(_extract_account_id())
    account_id = _account_scope(account)
    content_type = request.args.get("type", "original")  # original or rewritten
    
    content = workflow_store.get_article_content(record_id, account_id)
    if not content:
        return "<h1>文章未找到</h1><p>请检查记录ID是否正确</p>", 404
    
    if content_type == "rewritten":
        html_content = content.get("rewritten_html", "")
        data = content.get("rewritten_data", {})
        title = data.get("title", "改写后文章")
    else:
        html_content = content.get("original_html", "")
        data = content.get("original_data", {})
        title = data.get("title", "原文")
    
    if not html_content:
        return f"<h1>{title}</h1><p>暂无{ '改写后' if content_type == 'rewritten' else '原文' }内容</p>", 200
    
    # 修复图片路径：将相对路径转换为绝对路径
    # HTML中的图片路径是 /local_images/... 需要添加服务器基础URL
    server_base = f"http://127.0.0.1:{os.getenv('ADMIN_PORT', '8701')}"
    html_content = html_content.replace('src="/local_images/', f'src="{server_base}/local_images/')
    html_content = html_content.replace('src="/output/', f'src="{server_base}/output/')
    html_content = html_content.replace("src='/local_images/", f'src="{server_base}/local_images/')
    html_content = html_content.replace("src='/output/", f'src="{server_base}/output/')
    
    # 包装成完整HTML页面
    preview_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 预览</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .article-container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #222;
        }}
        h2 {{
            font-size: 20px;
            font-weight: 600;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        h3 {{
            font-size: 18px;
            font-weight: 600;
            margin-top: 25px;
            margin-bottom: 10px;
        }}
        p {{
            margin: 15px 0;
            text-align: justify;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
        }}
        ul, ol {{
            padding-left: 25px;
        }}
        li {{
            margin: 8px 0;
        }}
        blockquote {{
            border-left: 4px solid #1890ff;
            padding-left: 15px;
            margin: 20px 0;
            color: #666;
            background: #f6f6f6;
            padding: 15px;
        }}
        .preview-header {{
            background: #1890ff;
            color: white;
            padding: 10px 20px;
            margin: -20px -20px 20px -20px;
            border-radius: 8px 8px 0 0;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="article-container">
        <div class="preview-header">📄 {'改写后预览' if content_type == 'rewritten' else '原文预览'} | {title[:50]}{'...' if len(title) > 50 else ''}</div>
        {html_content}
    </div>
</body>
</html>"""
    
    return Response(preview_html, mimetype='text/html')


# ==================== 工具 API ====================

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
