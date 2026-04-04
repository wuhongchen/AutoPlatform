import json
import os
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from config import Config


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(PROJECT_ROOT, "output", "admin_accounts.json")


def _safe_text(value) -> str:
    return str(value or "").strip()


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _example_content_direction() -> str:
    return "AI 工具实操、OpenClaw 使用技巧、公众号自动化运营经验分享"


def _example_prompt_direction() -> str:
    return "结论先行，少空话，多给明确步骤、场景收益和避坑提醒，语言保持专业但易读。"


def _example_wechat_prompt_direction() -> str:
    return "标题要有信息密度，导语直接点出问题，正文分段清晰，适合手机端阅读，结尾给执行建议。"


def _default_account_template() -> Dict:
    return {
        "id": "default",
        "name": "默认示例账户",
        "enabled": True,
        "wechat_appid": _safe_text(Config.WECHAT_APPID),
        "wechat_secret": _safe_text(Config.WECHAT_SECRET),
        "wechat_author": _safe_text(Config.WECHAT_AUTHOR or "W 小龙虾"),
        "feishu_app_id": _safe_text(Config.FEISHU_APP_ID),
        "feishu_app_secret": _safe_text(Config.FEISHU_APP_SECRET),
        "feishu_app_token": _safe_text(Config.FEISHU_APP_TOKEN),
        "feishu_inspiration_table": _safe_text(Config.FEISHU_INSPIRATION_TABLE),
        "feishu_pipeline_table": _safe_text(Config.FEISHU_PIPELINE_TABLE),
        "feishu_publish_log_table": _safe_text(Config.FEISHU_PUBLISH_LOG_TABLE),
        "feishu_admin_user_id": _safe_text(os.getenv("FEISHU_ADMIN_USER_ID", "")),
        "pipeline_role": _safe_text(os.getenv("OPENCLAW_PIPELINE_ROLE", "tech_expert")) or "tech_expert",
        "pipeline_model": _safe_text(os.getenv("OPENCLAW_PIPELINE_MODEL", "auto")) or "auto",
        "pipeline_batch_size": int(os.getenv("OPENCLAW_PIPELINE_BATCH_SIZE", "3") or "3"),
        "content_direction": _safe_text(os.getenv("OPENCLAW_CONTENT_DIRECTION", "")) or _example_content_direction(),
        "wechat_prompt_direction": _safe_text(os.getenv("OPENCLAW_WECHAT_PROMPT_DIRECTION", "")) or _example_wechat_prompt_direction(),
        "prompt_direction": _safe_text(os.getenv("OPENCLAW_PROMPT_DIRECTION", "")) or _example_prompt_direction(),
        "wechat_demo_cli": _safe_text(os.getenv("OPENCLAW_WECHAT_DEMO_CLI", "")),
        "wechat_workspace": "",
        "wechat_state_dir": "",
        "wechat_runtime_cwd": "",
        "wechat_default_mp_id": "",
        "created_at": _now_str(),
        "updated_at": _now_str(),
        "last_run_at": "",
    }


def _sanitize_account(raw: Dict, fallback_id: Optional[str] = None) -> Dict:
    base = _default_account_template()
    base["id"] = fallback_id or base["id"]
    if raw:
        base.update(raw)

    base["id"] = _safe_text(base.get("id")) or (fallback_id or uuid.uuid4().hex[:8])
    base["name"] = _safe_text(base.get("name")) or f"账户-{base['id'][:6]}"
    base["enabled"] = bool(base.get("enabled", True))

    text_fields = [
        "wechat_appid",
        "wechat_secret",
        "wechat_author",
        "feishu_app_id",
        "feishu_app_secret",
        "feishu_app_token",
        "feishu_inspiration_table",
        "feishu_pipeline_table",
        "feishu_publish_log_table",
        "feishu_admin_user_id",
        "pipeline_role",
        "pipeline_model",
        "content_direction",
        "wechat_prompt_direction",
        "prompt_direction",
        "wechat_demo_cli",
        "wechat_workspace",
        "wechat_state_dir",
        "wechat_runtime_cwd",
        "wechat_default_mp_id",
        "created_at",
        "updated_at",
        "last_run_at",
    ]
    for key in text_fields:
        base[key] = _safe_text(base.get(key))

    try:
        base["pipeline_batch_size"] = max(1, int(base.get("pipeline_batch_size", 3)))
    except Exception:
        base["pipeline_batch_size"] = 3

    return base


class AccountStore:
    def __init__(self, path: str = ACCOUNTS_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._state = {"active_account_id": "", "accounts": []}
        self._load()

    def _load(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            default = _default_account_template()
            self._state = {"active_account_id": default["id"], "accounts": [default]}
            self._save_unlocked()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            accounts = data.get("accounts") or []
            sanitized = []
            for i, item in enumerate(accounts):
                fallback_id = _safe_text(item.get("id")) or f"acc-{i+1}"
                sanitized.append(_sanitize_account(item, fallback_id=fallback_id))
            if not sanitized:
                sanitized = [_default_account_template()]
            active = _safe_text(data.get("active_account_id"))
            if not any(x["id"] == active for x in sanitized):
                active = sanitized[0]["id"]
            self._state = {"active_account_id": active, "accounts": sanitized}
            self._save_unlocked()
        except Exception:
            default = _default_account_template()
            self._state = {"active_account_id": default["id"], "accounts": [default]}
            self._save_unlocked()

    def _save_unlocked(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    def dump(self):
        with self._lock:
            return {
                "active_account_id": self._state["active_account_id"],
                "accounts": [dict(x) for x in self._state["accounts"]],
            }

    def list(self) -> List[Dict]:
        return self.dump()["accounts"]

    def get(self, account_id: str) -> Optional[Dict]:
        aid = _safe_text(account_id)
        with self._lock:
            for acc in self._state["accounts"]:
                if acc["id"] == aid:
                    return dict(acc)
        return None

    def get_active(self) -> Dict:
        with self._lock:
            active = self._state["active_account_id"]
            for acc in self._state["accounts"]:
                if acc["id"] == active:
                    return dict(acc)
            return dict(self._state["accounts"][0])

    def set_active(self, account_id: str) -> Dict:
        aid = _safe_text(account_id)
        with self._lock:
            if not any(x["id"] == aid for x in self._state["accounts"]):
                raise ValueError("account not found")
            self._state["active_account_id"] = aid
            self._save_unlocked()
            for acc in self._state["accounts"]:
                if acc["id"] == aid:
                    return dict(acc)
        raise ValueError("account not found")

    def upsert(self, payload: Dict) -> Dict:
        with self._lock:
            raw_id = _safe_text(payload.get("id"))
            if not raw_id:
                raw_id = uuid.uuid4().hex[:8]
            item = _sanitize_account(payload, fallback_id=raw_id)
            now = _now_str()
            replaced = False
            for i, acc in enumerate(self._state["accounts"]):
                if acc["id"] == raw_id:
                    item["created_at"] = _safe_text(acc.get("created_at")) or now
                    item["last_run_at"] = _safe_text(item.get("last_run_at") or acc.get("last_run_at"))
                    item["updated_at"] = now
                    self._state["accounts"][i] = item
                    replaced = True
                    break
            if not replaced:
                item["created_at"] = _safe_text(item.get("created_at")) or now
                item["updated_at"] = now
                item["last_run_at"] = _safe_text(item.get("last_run_at"))
                self._state["accounts"].append(item)
            if not self._state["active_account_id"]:
                self._state["active_account_id"] = item["id"]
            self._save_unlocked()
            return dict(item)

    def delete(self, account_id: str):
        aid = _safe_text(account_id)
        with self._lock:
            old = self._state["accounts"]
            left = [x for x in old if x["id"] != aid]
            if len(left) == len(old):
                raise ValueError("account not found")
            if not left:
                raise ValueError("cannot delete last account")
            self._state["accounts"] = left
            if self._state["active_account_id"] == aid:
                self._state["active_account_id"] = left[0]["id"]
            self._save_unlocked()

    def mark_runtime(self, account_id: str):
        aid = _safe_text(account_id)
        if not aid:
            return
        with self._lock:
            changed = False
            now = _now_str()
            for acc in self._state["accounts"]:
                if acc["id"] == aid:
                    acc["last_run_at"] = now
                    changed = True
                    break
            if changed:
                self._save_unlocked()
