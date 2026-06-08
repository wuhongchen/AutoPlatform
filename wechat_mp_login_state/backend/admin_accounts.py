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


def _default_account_template() -> Dict:
    return {
        "id": "default",
        "name": "默认账户",
        "enabled": True,
        "wechat_appid": _safe_text(Config.WECHAT_APPID),
        "wechat_secret": _safe_text(Config.WECHAT_SECRET),
        "wechat_author": _safe_text(Config.WECHAT_AUTHOR or "W 小龙虾"),
        "created_at": _now_str(),
        "updated_at": _now_str(),
    }


def _sanitize_account(raw: Dict, fallback_id: Optional[str] = None) -> Dict:
    # 只保留核心字段，丢弃所有旧字段
    base = _default_account_template()
    
    # 从原始数据中提取核心字段
    base["id"] = _safe_text(raw.get("id")) or (fallback_id or uuid.uuid4().hex[:8])
    base["name"] = _safe_text(raw.get("name")) or f"账户-{base['id'][:6]}"
    base["enabled"] = bool(raw.get("enabled", True))
    base["wechat_appid"] = _safe_text(raw.get("wechat_appid"))
    base["wechat_secret"] = _safe_text(raw.get("wechat_secret"))
    base["wechat_author"] = _safe_text(raw.get("wechat_author"))
    # 保留创建时间，更新更新时间
    base["created_at"] = _safe_text(raw.get("created_at")) or _now_str()
    base["updated_at"] = _now_str()

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

    def list(self) -> List[Dict]:
        with self._lock:
            return [dict(x) for x in self._state["accounts"]]

    def get(self, account_id: str) -> Optional[Dict]:
        with self._lock:
            for x in self._state["accounts"]:
                if x["id"] == account_id:
                    return dict(x)
            return None

    def get_active(self) -> Optional[Dict]:
        with self._lock:
            active_id = self._state.get("active_account_id")
            for x in self._state["accounts"]:
                if x["id"] == active_id:
                    return dict(x)
            return None

    def upsert(self, account: Dict) -> Dict:
        with self._lock:
            sanitized = _sanitize_account(account)
            exists = False
            for i, x in enumerate(self._state["accounts"]):
                if x["id"] == sanitized["id"]:
                    self._state["accounts"][i] = sanitized
                    exists = True
                    break
            if not exists:
                self._state["accounts"].append(sanitized)
            self._save_unlocked()
            return dict(sanitized)

    def delete(self, account_id: str) -> bool:
        with self._lock:
            original_len = len(self._state["accounts"])
            self._state["accounts"] = [x for x in self._state["accounts"] if x["id"] != account_id]
            if len(self._state["accounts"]) < original_len:
                if self._state.get("active_account_id") == account_id:
                    self._state["active_account_id"] = self._state["accounts"][0]["id"] if self._state["accounts"] else ""
                self._save_unlocked()
                return True
            return False

    def activate(self, account_id: str) -> bool:
        with self._lock:
            for x in self._state["accounts"]:
                if x["id"] == account_id:
                    self._state["active_account_id"] = account_id
                    self._save_unlocked()
                    return True
            return False

    def dump(self) -> Dict:
        """返回完整状态（用于API）"""
        with self._lock:
            return {
                "active_account_id": self._state.get("active_account_id", ""),
                "accounts": [dict(x) for x in self._state["accounts"]]
            }

    def mark_runtime(self, account_id: str):
        """标记账户最后运行时间（用于任务调度）"""
        with self._lock:
            for x in self._state["accounts"]:
                if x["id"] == account_id:
                    x["last_runtime"] = _now_str()
                    self._save_unlocked()
                    return
