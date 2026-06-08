"""
公众号平台扫码登录态服务

基于 vendored 的 wechat-demo-cli runtime，提供：
1. 登录状态检查与二维码登录
2. 公众号搜索/关注
3. 文章列表拉取与正文抓取
4. 同步到当前项目的素材库
"""

from __future__ import annotations

import json
import html
import ast
import os
import re
import shlex
import shutil
import signal
import struct
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from app.config import get_settings
from app.models import InspirationRecord, InspirationStatus


FIXED_QR_FILENAME = "qr_login.png"


def _safe_text(value) -> str:
    return str(value or "").strip()


def _extract_json_from_text(text: str):
    raw = _safe_text(text)
    if not raw:
        return None
    lines = raw.splitlines()
    for i in range(len(lines)):
        start = lines[i].lstrip()
        if not start.startswith("{") and not start.startswith("["):
            continue
        for j in range(len(lines), i, -1):
            snippet = "\n".join(lines[i:j]).strip()
            if not snippet:
                continue
            try:
                return json.loads(snippet)
            except Exception:
                continue
    return None


def _normalize_qr_display(value: str) -> str:
    raw = _safe_text(value).lower()
    if raw == "open":
        return "open"
    return "none"


def _read_png_size(path: Path) -> Optional[tuple]:
    try:
        with path.open("rb") as f:
            header = f.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width = struct.unpack(">I", header[16:20])[0]
        height = struct.unpack(">I", header[20:24])[0]
        return int(width), int(height)
    except Exception:
        return None


def _is_plausible_qr_image(path: Path) -> bool:
    try:
        size = path.stat().st_size
    except Exception:
        return False
    if size < 500:
        return False
    dims = _read_png_size(path)
    if not dims:
        return True
    width, height = dims
    return 80 <= width <= 5000 and 80 <= height <= 5000


def _normalize_qr_remote_url(url: str) -> str:
    raw = _safe_text(url)
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return ""
    if parsed.scheme not in {"http", "https"}:
        return ""
    if parsed.netloc != "mp.weixin.qq.com":
        return ""
    if parsed.path != "/cgi-bin/scanloginqrcode":
        return ""
    query = parse_qs(parsed.query or "", keep_blank_values=True)
    if "login_appid" in query and not _safe_text((query.get("login_appid") or [""])[0]):
        return ""
    has_uuid = bool(_safe_text((query.get("uuid") or [""])[0]))
    has_random = bool(_safe_text((query.get("random") or [""])[0]))
    if not (has_uuid or has_random):
        return ""
    return raw


def _extract_qr_remote_url(text: str) -> str:
    raw = _safe_text(text)
    if not raw:
        return ""
    match = re.search(r"code_src:(https?://mp\.weixin\.qq\.com/cgi-bin/scanloginqrcode\?[^\s]+)", raw)
    if match:
        return _normalize_qr_remote_url(match.group(1))
    match = re.search(r"code_src:(/cgi-bin/scanloginqrcode\?[^\s]+)", raw)
    if match:
        return _normalize_qr_remote_url(f"https://mp.weixin.qq.com{match.group(1)}")
    return ""


def _missing_modules_from_error(text: str) -> List[str]:
    raw = _safe_text(text)
    if not raw:
        return []
    modules = []
    for item in re.findall(r"No module named '([^']+)'", raw):
        if item not in modules:
            modules.append(item)
    return modules


class WechatLoginStateService:
    """公众号平台扫码登录态服务。"""

    def __init__(self, account=None):
        settings = get_settings()
        if account is None:
            account_data = {}
        elif hasattr(account, "model_dump"):
            account_data = account.model_dump()
        elif isinstance(account, dict):
            account_data = dict(account)
        else:
            account_data = dict(getattr(account, "__dict__", {}) or {})

        self.settings = settings
        self.account = account_data
        self.account_id = _safe_text(account_data.get("account_id") or account_data.get("id")) or "default"
        self.metadata = dict(account_data.get("metadata") or {})
        self.project_root = settings.project_root.resolve()
        self.wrapper_path = (
            self.project_root
            / "wechat_mp_login_state"
            / "backend"
            / "scripts"
            / "internal"
            / "wechat_demo_wrapper.py"
        ).resolve()
        self.demo_cli_path = self._resolve_demo_cli_path()
        self.python_bin = self._resolve_python_bin()
        self.workspace_dir = self._resolve_workspace_dir()
        self.runtime_cwd = self._resolve_runtime_cwd()
        self.state_dir = self._resolve_state_dir()
        self.state_file = self.state_dir / "state.json"
        self.login_daemon_pid_file = self.state_dir / "login_daemon.pid"
        self.login_daemon_log_file = self.state_dir / "login_daemon.log"

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_cwd.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._prepare_runtime_support_files()

    def _resolve_workspace_dir(self) -> Path:
        raw = _safe_text(self.metadata.get("wechat_workspace"))
        if raw:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = self.project_root / path
            return path.resolve()

        root = _safe_text(os.getenv("OPENCLAW_WECHAT_ACCOUNTS_ROOT"))
        if root:
            root_path = Path(root).expanduser()
            if not root_path.is_absolute():
                root_path = self.project_root / root_path
            return (root_path.resolve() / self.account_id).resolve()

        return (self.settings.output_dir / "wechat_accounts" / self.account_id).resolve()

    def _resolve_runtime_cwd(self) -> Path:
        raw = _safe_text(self.metadata.get("wechat_runtime_cwd"))
        if raw:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = self.workspace_dir / path
            return path.resolve()
        return (self.workspace_dir / "runtime").resolve()

    def _resolve_state_dir(self) -> Path:
        raw = _safe_text(self.metadata.get("wechat_state_dir"))
        if raw:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = self.workspace_dir / path
            return path.resolve()
        return (self.workspace_dir / "state").resolve()

    def _resolve_demo_cli_path(self) -> str:
        candidates = [
            _safe_text(self.metadata.get("wechat_demo_cli")),
            _safe_text(os.getenv("OPENCLAW_WECHAT_DEMO_CLI")),
            str(
                (
                    self.project_root
                    / "wechat_mp_login_state"
                    / "third_party"
                    / "we-mp-rss-runtime"
                    / "demo_cli"
                    / "wechat_demo_cli.py"
                ).resolve()
            ),
        ]
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            path = Path(candidate).expanduser()
            if path.exists() and path.is_file():
                return str(path.resolve())
        return _safe_text(candidates[0])

    def _resolve_python_bin(self) -> str:
        picked = (
            _safe_text(self.metadata.get("wechat_demo_python"))
            or _safe_text(os.getenv("OPENCLAW_WECHAT_DEMO_PYTHON"))
            or "python3"
        )
        cli_path = Path(self.demo_cli_path).expanduser()
        if cli_path.exists():
            venv_python = cli_path.parent.parent / ".venv" / "bin" / "python"
            if picked in {"python", "python3"} and venv_python.exists():
                return str(venv_python.resolve())
        return picked

    def _prepare_runtime_support_files(self):
        cli_path = Path(self.demo_cli_path).expanduser()
        if not cli_path.exists():
            return
        demo_root = cli_path.parent.parent
        for name in ("config.yaml", "config.example.yaml"):
            src = demo_root / name
            dst = self.runtime_cwd / name
            if src.exists() and not dst.exists():
                try:
                    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                except Exception:
                    pass

    def ensure_ready(self):
        if not self.wrapper_path.exists():
            raise RuntimeError(f"wechat wrapper missing: {self.wrapper_path}")
        cli_path = Path(self.demo_cli_path).expanduser()
        if not cli_path.exists() or not cli_path.is_file():
            raise RuntimeError(
                "wechat_demo_cli.py 不可用，请先检查 wechat_mp_login_state runtime 是否存在，或通过 OPENCLAW_WECHAT_DEMO_CLI 指定路径"
            )

    def _build_demo_cmd(self, args: List[str]) -> List[str]:
        self.ensure_ready()
        return [
            self.python_bin,
            str(self.wrapper_path),
            "--cli-path",
            self.demo_cli_path,
            "--state-dir",
            str(self.state_dir),
            "--cwd",
            str(self.runtime_cwd),
            "--",
        ] + list(args)

    def _demo_env(self) -> Dict[str, str]:
        env = dict(os.environ)
        env.setdefault("OPENCLAW_NON_INTERACTIVE", "1")
        env.setdefault("BROWSER_TYPE", "chromium")
        env.setdefault("PYTHONUNBUFFERED", "1")
        return env

    def _run_demo(self, args: List[str], timeout: int = 600, check: bool = True) -> Dict:
        cmd = self._build_demo_cmd(args)
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_root,
                env=self._demo_env(),
                capture_output=True,
                text=True,
                timeout=max(30, int(timeout)),
            )
            out = {
                "ok": proc.returncode == 0,
                "return_code": proc.returncode,
                "command": " ".join(shlex.quote(x) for x in cmd),
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "timeout": False,
            }
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            out = {
                "ok": False,
                "return_code": 124,
                "command": " ".join(shlex.quote(x) for x in cmd),
                "stdout": stdout,
                "stderr": stderr,
                "timeout": True,
            }

        if check and out.get("timeout"):
            raise RuntimeError(f"wechat demo command timeout after {max(30, int(timeout))}s")
        if check and out.get("return_code") != 0:
            last_line = _safe_text(
                (out.get("stderr") or out.get("stdout") or "").splitlines()[-1]
                if (out.get("stderr") or out.get("stdout"))
                else ""
            )
            raise RuntimeError(last_line or f"wechat demo command failed: code={out.get('return_code')}")
        return out

    def _pid_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return False

    def _read_daemon_pid(self) -> int:
        try:
            return int(_safe_text(self.login_daemon_pid_file.read_text(encoding="utf-8")))
        except Exception:
            return 0

    def _cleanup_dead_daemon_pid(self):
        pid = self._read_daemon_pid()
        if pid > 0 and not self._pid_alive(pid):
            try:
                self.login_daemon_pid_file.unlink()
            except Exception:
                pass

    def _stop_login_daemon_if_running(self):
        pid = self._read_daemon_pid()
        if pid <= 0:
            return
        if not self._pid_alive(pid):
            self._cleanup_dead_daemon_pid()
            return
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        for _ in range(20):
            if not self._pid_alive(pid):
                break
            time.sleep(0.2)
        if self._pid_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
        self._cleanup_dead_daemon_pid()

    def _tail_daemon_log(self, max_lines: int = 40) -> str:
        try:
            raw = self.login_daemon_log_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
        return "\n".join(raw.splitlines()[-max_lines:])

    def _cleanup_stale_login_lock(self, timeout_sec: int = 300):
        lock_path = self.runtime_cwd / "data" / "lock.lock"
        if not lock_path.exists() or not lock_path.is_file():
            return
        try:
            content = _safe_text(lock_path.read_text(encoding="utf-8"))
            parts = content.split("|")
            pid = int(parts[0]) if parts and parts[0] else 0
            ts = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
        except Exception:
            try:
                lock_path.unlink()
            except Exception:
                pass
            return

        if ts > 0 and time.time() - ts > float(timeout_sec):
            try:
                lock_path.unlink()
            except Exception:
                pass
            return

        if pid > 0 and not self._pid_alive(pid):
            try:
                lock_path.unlink()
            except Exception:
                pass

    def fixed_qr_image_path(self) -> Path:
        return (self.state_dir / FIXED_QR_FILENAME).resolve()

    def _qr_image_candidates(self, runtime: Optional[Dict] = None) -> List[Path]:
        runtime = runtime if isinstance(runtime, dict) else {}
        demo_root = Path(self.demo_cli_path).expanduser().parent.parent
        candidates = [
            self.fixed_qr_image_path(),
            self.state_dir / "last_qr.png",
            demo_root / "static" / "wx_qrcode.png",
            self.runtime_cwd / "wx_qrcode.png",
            self.runtime_cwd / "static" / "wx_qrcode.png",
            self.workspace_dir / "wx_qrcode.png",
        ]
        code_val = _safe_text(runtime.get("code") or runtime.get("qrcode") or runtime.get("qr_image"))
        if code_val:
            if code_val.startswith("/"):
                candidates.insert(0, demo_root / code_val.lstrip("/"))
            elif not code_val.startswith("http"):
                candidates.insert(0, (self.runtime_cwd / code_val).resolve())
        return candidates

    def get_qr_image_path(self, runtime: Optional[Dict] = None) -> Optional[Path]:
        latest = None
        latest_mtime = -1.0
        for path in self._qr_image_candidates(runtime):
            if not path.exists() or not path.is_file():
                continue
            if not _is_plausible_qr_image(path):
                continue
            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0
            if mtime >= latest_mtime:
                latest = path
                latest_mtime = mtime
        return latest

    def _persist_qr_image(self, source: Optional[Path]) -> Optional[Path]:
        if not source or not source.exists() or not source.is_file():
            return None
        target = self.fixed_qr_image_path()
        try:
            source_resolved = source.resolve()
        except Exception:
            source_resolved = source
        try:
            if source_resolved != target:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(source_resolved), str(target))
            return target if target.exists() else source_resolved
        except Exception:
            return source_resolved if source_resolved.exists() else None

    def _download_qr_image(self, remote_url: str) -> Optional[Path]:
        url = _normalize_qr_remote_url(remote_url)
        if not url:
            return None
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://mp.weixin.qq.com/"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read()
        except (urllib.error.URLError, TimeoutError, ValueError):
            return None
        if not body or len(body) < 500:
            return None
        target = self.fixed_qr_image_path()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            return target if _is_plausible_qr_image(target) else None
        except Exception:
            return None

    def _token_file_path(self) -> Path:
        return (self.runtime_cwd / "data" / "wx.lic").resolve()

    def _load_local_token_payload(self) -> Dict:
        path = self._token_file_path()
        if not path.exists() or not path.is_file():
            return {}
        raw_text = _safe_text(path.read_text(encoding="utf-8", errors="ignore"))
        if not raw_text:
            return {}

        payload = None
        try:
            payload = json.loads(raw_text)
        except Exception:
            payload = None

        if payload is None:
            try:
                import yaml  # type: ignore

                payload = yaml.safe_load(raw_text)
            except Exception:
                payload = None

        if not isinstance(payload, dict):
            return {}
        token_data = payload.get("token_data")
        if isinstance(token_data, str):
            try:
                token_data = json.loads(token_data)
            except Exception:
                token_data = {}
        if not isinstance(token_data, dict):
            token_data = {}
        return token_data

    def _local_token_exists(self) -> bool:
        token_data = self._load_local_token_payload()
        return bool(_safe_text(token_data.get("token")))

    def _local_runtime_status(self, qr_path: Optional[Path] = None) -> Dict:
        token_exists = self._local_token_exists()
        return {
            "login_status": bool(token_exists),
            "qr_code": bool(qr_path),
            "token_exists": bool(token_exists),
        }

    def _merge_runtime_status(self, runtime: Optional[Dict], qr_path: Optional[Path] = None) -> Dict:
        base = dict(runtime or {})
        token_exists = bool(base.get("token_exists")) or self._local_token_exists()
        qr_exists = bool(base.get("qr_code")) or bool(qr_path)
        if token_exists:
            base["login_status"] = True
        base["token_exists"] = token_exists
        base["qr_code"] = qr_exists
        return base

    def _build_diagnostics(self, runtime: Optional[Dict], state: Optional[Dict] = None) -> Dict:
        runtime = runtime if isinstance(runtime, dict) else {}
        state = state if isinstance(state, dict) else {}
        blockers = []
        missing_modules = []

        for key, label in (
            ("wx_runtime_error", "微信运行时"),
            ("token_runtime_error", "Token 运行时"),
        ):
            message = _safe_text(runtime.get(key))
            if not message:
                continue
            blockers.append({
                "key": key,
                "label": label,
                "message": message,
            })
            for module_name in _missing_modules_from_error(message):
                if module_name not in missing_modules:
                    missing_modules.append(module_name)

        install_hint = ""
        browser_install_hint = ""
        if missing_modules:
            install_hint = f"python3 -m pip install {' '.join(missing_modules)}"
            if "playwright" in missing_modules:
                browser_install_hint = "python3 -m playwright install chromium"

        return {
            "ready": not blockers,
            "blockers": blockers,
            "missing_modules": missing_modules,
            "can_generate_qr": not blockers and bool(state.get("qr_image_path")),
            "can_check_login": not blockers,
            "summary": "运行环境正常" if not blockers else f"运行环境缺少依赖: {', '.join(missing_modules) or 'unknown'}",
            "install_hint": install_hint,
            "browser_install_hint": browser_install_hint,
        }

    def _start_login_daemon(self, timeout: int, token_wait_timeout: int, thread_join_timeout: int) -> Dict:
        self._stop_login_daemon_if_running()
        for path in [self.fixed_qr_image_path(), self.state_dir / "last_qr.png"]:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass

        cmd = self._build_demo_cmd([
            "login",
            "--wait",
            "--qr-display",
            "none",
            "--timeout",
            str(max(30, int(timeout))),
            "--token-wait-timeout",
            str(max(10, int(token_wait_timeout))),
            "--thread-join-timeout",
            str(max(5, int(thread_join_timeout))),
        ])

        self.login_daemon_log_file.parent.mkdir(parents=True, exist_ok=True)
        log_fp = self.login_daemon_log_file.open("w", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            env=self._demo_env(),
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        log_fp.close()
        self.login_daemon_pid_file.write_text(str(proc.pid), encoding="utf-8")

        deadline = time.time() + 22
        qr_path = None
        while time.time() < deadline:
            qr_path = self.get_qr_image_path()
            if qr_path or proc.poll() is not None:
                break
            time.sleep(0.5)
        if qr_path:
            qr_path = self._persist_qr_image(qr_path)

        return {
            "pid": int(proc.pid),
            "running": self._pid_alive(proc.pid),
            "qr_image_path": str(qr_path) if qr_path else "",
            "log_tail": self._tail_daemon_log(),
        }

    def load_state(self) -> Dict:
        if not self.state_file.exists():
            return {"mps": [], "articles": {}, "meta": {}}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("mps", [])
        data.setdefault("articles", {})
        data.setdefault("meta", {})
        return data

    def _iter_articles(self, mp_id: str = "") -> List[Dict]:
        state = self.load_state()
        article_map = state.get("articles") or {}
        target = _safe_text(mp_id)
        if target:
            items = list(article_map.get(target) or [])
        else:
            items = []
            for rows in article_map.values():
                items.extend(rows or [])
        items.sort(key=lambda x: int(x.get("publish_time") or 0), reverse=True)
        return items

    def _summarize_article(self, article: Dict) -> Dict:
        raw_content = _safe_text(article.get("content"))
        cache_output = _safe_text((article.get("content_cache") or {}).get("output"))
        publish_time = int(article.get("publish_time") or 0)
        publish_time_str = _safe_text(article.get("publish_time_str"))
        if publish_time and not publish_time_str:
            try:
                publish_time_str = datetime.fromtimestamp(publish_time).strftime("%Y-%m-%d %H:%M")
            except Exception:
                publish_time_str = ""
        return {
            "id": _safe_text(article.get("id")),
            "mp_id": _safe_text(article.get("mp_id")),
            "title": _safe_text(article.get("title")),
            "url": _safe_text(article.get("url")),
            "author": _safe_text(article.get("author")),
            "description": _safe_text(article.get("description")),
            "cover": _safe_text(article.get("cover")),
            "topic_image": _safe_text(article.get("topic_image")),
            "publish_time": publish_time,
            "publish_time_str": publish_time_str,
            "has_content": bool(raw_content or cache_output),
        }

    def _extract_content_noencode_html(self, raw_html: str) -> str:
        raw = _safe_text(raw_html)
        marker = "content_noencode: JsDecode('"
        start = raw.find(marker)
        if start < 0:
            return ""
        i = start + len(marker)
        payload = []
        escaped = False
        while i < len(raw):
            ch = raw[i]
            if escaped:
                payload.append(ch)
                escaped = False
            elif ch == "\\":
                payload.append(ch)
                escaped = True
            elif ch == "'" and raw[i:i + 2] == "')":
                break
            else:
                payload.append(ch)
            i += 1
        if i >= len(raw):
            return ""
        try:
            decoded = ast.literal_eval("'" + "".join(payload) + "'")
        except Exception:
            return ""
        return html.unescape(decoded).strip()

    def _normalize_cached_article_html(self, raw_html: str) -> str:
        raw = _safe_text(raw_html)
        if not raw:
            return ""
        lowered = raw.lstrip().lower()
        if lowered.startswith("<") or "<body" in lowered or "<html" in lowered:
            return raw
        decoded = self._extract_content_noencode_html(raw)
        return decoded or raw

    def status(self) -> Dict:
        self._cleanup_dead_daemon_pid()
        daemon_pid = self._read_daemon_pid()
        daemon_running = bool(daemon_pid and self._pid_alive(daemon_pid))
        local_qr_path = self.get_qr_image_path()
        if local_qr_path:
            local_qr_path = self._persist_qr_image(local_qr_path)

        if daemon_running:
            result = {
                "ok": True,
                "return_code": 0,
                "stdout": "",
                "stderr": "",
                "timeout": False,
            }
            runtime = self._local_runtime_status(qr_path=local_qr_path)
        else:
            result = self._run_demo(["status"], timeout=180, check=False)
            parsed = _extract_json_from_text(result.get("stdout", ""))
            runtime = parsed if isinstance(parsed, dict) else {}

        state = self.load_state()
        meta = state.get("meta") or {}
        qr_remote_url = _normalize_qr_remote_url(_safe_text(meta.get("qr_remote_url")))
        if not qr_remote_url:
            qr_remote_url = _extract_qr_remote_url(result.get("stdout", ""))

        qr_path = self.get_qr_image_path(runtime=runtime) or local_qr_path
        if qr_path:
            qr_path = self._persist_qr_image(qr_path)
        elif qr_remote_url:
            qr_path = self._download_qr_image(qr_remote_url)
        runtime = self._merge_runtime_status(runtime=runtime, qr_path=qr_path)

        state_summary = {
            "mp_count": len(state.get("mps") or []),
            "article_count": sum(len(v or []) for v in (state.get("articles") or {}).values()),
            "state_file": str(self.state_file),
            "workspace_dir": str(self.workspace_dir),
            "runtime_cwd": str(self.runtime_cwd),
            "demo_cli_path": self.demo_cli_path,
            "qr_image_exists": bool(qr_path),
            "qr_image_path": str(qr_path) if qr_path else "",
            "qr_remote_url": qr_remote_url,
            "login_daemon_pid": daemon_pid or 0,
            "login_daemon_running": bool(daemon_pid and self._pid_alive(daemon_pid)),
        }
        diagnostics = self._build_diagnostics(runtime=runtime, state=state_summary)

        return {
            "ok": bool(result.get("ok")),
            "runtime": runtime,
            "state": state_summary,
            "diagnostics": diagnostics,
            "return_code": result.get("return_code"),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "timeout": bool(result.get("timeout")),
        }

    def login(
        self,
        wait: bool = True,
        qr_display: str = "none",
        timeout: int = 180,
        token_wait_timeout: int = 60,
        thread_join_timeout: int = 20,
    ) -> Dict:
        self._cleanup_stale_login_lock()
        preflight = self.status()
        diagnostics = preflight.get("diagnostics") or {}
        if diagnostics.get("blockers"):
            preflight.update({
                "login_ok": False,
                "login_mode": "blocked",
                "error": diagnostics.get("summary") or "运行环境异常，二维码无法生成",
                "login_note": "请先安装登录态采集依赖后再重试。",
                "install_hint": diagnostics.get("install_hint") or "",
                "browser_install_hint": diagnostics.get("browser_install_hint") or "",
            })
            return preflight
        if not wait:
            daemon = self._start_login_daemon(
                timeout=max(120, int(timeout)),
                token_wait_timeout=max(20, int(token_wait_timeout)),
                thread_join_timeout=max(10, int(thread_join_timeout)),
            )
            summary = self.status()
            summary["login_ok"] = bool(daemon.get("running"))
            summary["login_mode"] = "daemon"
            summary["login_daemon_pid"] = int(daemon.get("pid") or 0)
            summary["login_note"] = "已启动后台登录进程，请扫码并确认。"
            summary["login_stdout"] = _safe_text(daemon.get("log_tail"))
            summary["login_stderr"] = ""
            return summary

        picked_qr_display = _normalize_qr_display(qr_display)
        args = [
            "login",
            "--wait",
            "--qr-display",
            picked_qr_display,
            "--timeout",
            str(max(30, int(timeout))),
            "--token-wait-timeout",
            str(max(10, int(token_wait_timeout))),
            "--thread-join-timeout",
            str(max(5, int(thread_join_timeout))),
        ]
        run_timeout = max(180, int(timeout) + int(token_wait_timeout) + int(thread_join_timeout))
        result = self._run_demo(args, timeout=run_timeout, check=False)
        summary = self.status()
        qr_remote_url = _extract_qr_remote_url(result.get("stdout", ""))
        qr_path = self.get_qr_image_path(runtime=summary.get("runtime"))
        if qr_path:
            qr_path = self._persist_qr_image(qr_path)
        elif qr_remote_url:
            qr_path = self._download_qr_image(qr_remote_url)
        summary.update({
            "login_ok": bool(result.get("ok")),
            "login_stdout": result.get("stdout", ""),
            "login_stderr": result.get("stderr", ""),
            "login_return_code": result.get("return_code"),
            "login_timeout": bool(result.get("timeout")),
            "qr_display_used": picked_qr_display,
            "qr_image_exists": bool(qr_path),
            "qr_image_path": str(qr_path) if qr_path else "",
            "qr_remote_url": qr_remote_url,
        })
        return summary

    def search_mp(self, keyword: str, limit: int = 10, offset: int = 0) -> Dict:
        diagnostics = self.status().get("diagnostics") or {}
        if diagnostics.get("blockers"):
            raise RuntimeError(diagnostics.get("summary") or "运行环境异常，无法检索公众号")
        kw = _safe_text(keyword)
        if not kw:
            raise RuntimeError("keyword is required")
        result = self._run_demo(
            ["search-mp", kw, "--limit", str(max(1, int(limit))), "--offset", str(max(0, int(offset))), "--raw"],
            timeout=180,
            check=True,
        )
        parsed = _extract_json_from_text(result.get("stdout", ""))
        items = parsed if isinstance(parsed, list) else []
        return {"ok": True, "keyword": kw, "items": items, "count": len(items)}

    def list_mps(self) -> Dict:
        items = self.load_state().get("mps") or []
        return {"ok": True, "items": items, "count": len(items)}

    def add_mp(self, keyword: str, pick: int = 1, limit: int = 10, offset: int = 0) -> Dict:
        diagnostics = self.status().get("diagnostics") or {}
        if diagnostics.get("blockers"):
            raise RuntimeError(diagnostics.get("summary") or "运行环境异常，无法关注公众号")
        kw = _safe_text(keyword)
        if not kw:
            raise RuntimeError("keyword is required")
        before = self.list_mps().get("items") or []
        before_ids = {str(item.get("id") or "").strip() for item in before}
        self._run_demo(
            [
                "add-mp",
                "--keyword",
                kw,
                "--pick",
                str(max(1, int(pick))),
                "--limit",
                str(max(1, int(limit))),
                "--offset",
                str(max(0, int(offset))),
            ],
            timeout=240,
            check=True,
        )
        after = self.list_mps().get("items") or []
        added = {}
        for item in after:
            item_id = str(item.get("id") or "").strip()
            if item_id and item_id not in before_ids:
                added = item
                break
        if not added and after:
            added = after[-1]
        return {"ok": True, "added": added, "items": after, "count": len(after)}

    def pull_articles(self, mp_id: str, pages: int = 1, mode: str = "api", with_content: bool = False) -> Dict:
        diagnostics = self.status().get("diagnostics") or {}
        if diagnostics.get("blockers"):
            raise RuntimeError(diagnostics.get("summary") or "运行环境异常，无法拉取文章")
        target_mp_id = _safe_text(mp_id)
        if not target_mp_id:
            raise RuntimeError("mp_id is required")
        args = [
            "pull-articles",
            "--mp-id",
            target_mp_id,
            "--pages",
            str(max(1, int(pages))),
            "--mode",
            _safe_text(mode) or "api",
            "--show",
            "20",
        ]
        if with_content:
            args.append("--with-content")
        result = self._run_demo(args, timeout=max(300, int(pages) * 120), check=True)
        listed = self.list_articles(mp_id=target_mp_id, include_content=False)
        return {
            "ok": True,
            "mp_id": target_mp_id,
            "count": listed.get("count", 0),
            "items": listed.get("items", []),
            "stdout": result.get("stdout", ""),
        }

    def list_articles(self, mp_id: str = "", limit: int = 50, include_content: bool = False) -> Dict:
        target = _safe_text(mp_id)
        items = self._iter_articles(mp_id=target)
        safe_limit = max(1, int(limit)) if int(limit) != 0 else 0
        if safe_limit > 0:
            items = items[:safe_limit]
        if not include_content:
            items = [self._summarize_article(item) for item in items]
        return {"ok": True, "mp_id": target, "count": len(items), "items": items}

    def batch_fetch_content(
        self,
        mp_id: str = "",
        limit: int = 10,
        skip_existing: bool = True,
        continue_on_error: bool = True,
        sleep_sec: float = 0.8,
    ) -> Dict:
        diagnostics = self.status().get("diagnostics") or {}
        if diagnostics.get("blockers"):
            raise RuntimeError(diagnostics.get("summary") or "运行环境异常，无法抓取正文")
        args = ["batch-fetch-content"]
        if _safe_text(mp_id):
            args += ["--mp-id", _safe_text(mp_id)]
        if int(limit) > 0:
            args += ["--limit", str(int(limit))]
        if skip_existing:
            args.append("--skip-existing")
        if continue_on_error:
            args.append("--continue-on-error")
        else:
            args.append("--stop-on-error")
        args += ["--sleep", str(max(0.0, float(sleep_sec)))]

        result = self._run_demo(args, timeout=max(300, int(limit) * 90 if int(limit) > 0 else 600), check=False)
        target_name = _safe_text(mp_id) if _safe_text(mp_id) else "all_mps"
        summary_path = self.state_dir / "contents" / target_name / "_batch_result.json"
        summary = {}
        if summary_path.exists():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                summary = {}
        return {
            "ok": bool(result.get("ok")),
            "summary": summary,
            "summary_path": str(summary_path),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "return_code": result.get("return_code"),
        }

    def _load_article_html(self, article: Dict) -> str:
        direct_content = _safe_text(article.get("content"))
        if direct_content:
            return self._normalize_cached_article_html(direct_content)
        cache_output = _safe_text((article.get("content_cache") or {}).get("output"))
        if cache_output:
            path = Path(cache_output).expanduser()
            if not path.is_absolute():
                path = (self.state_dir / cache_output).resolve()
            if path.exists() and path.is_file():
                try:
                    return self._normalize_cached_article_html(path.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    return ""
            return self._normalize_cached_article_html(cache_output)
        return ""

    def get_article_preview(self, collector, mp_id: str, article_id: str) -> Dict:
        target_mp_id = _safe_text(mp_id)
        target_article_id = _safe_text(article_id)
        if not target_mp_id or not target_article_id:
            raise RuntimeError("mp_id and article_id are required")

        article = next(
            (item for item in self._iter_articles(mp_id=target_mp_id) if _safe_text(item.get("id")) == target_article_id),
            None,
        )
        if not article:
            raise RuntimeError("article not found")

        raw_html = self._load_article_html(article)
        content_html = ""
        content_text = ""
        if raw_html:
            wrapped_html = raw_html if "<body" in raw_html.lower() or "<article" in raw_html.lower() else f"<article>{raw_html}</article>"
            content_text, content_html = collector.extract_content_from_html(wrapped_html)
            if not content_html:
                content_html = collector.sanitize_content_html(raw_html)
                content_text = BeautifulSoup(content_html, "html.parser").get_text(separator="\n", strip=True)

        summary = self._summarize_article(article)
        summary.update({
            "content_html": content_html,
            "content_text": content_text,
        })
        return {"ok": True, "item": summary}

    def _extract_images_from_html(self, html: str) -> List[str]:
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = _safe_text(img.get("data-src") or img.get("src"))
            if src and src not in images:
                images.append(src)
        return images

    def sync_articles_to_inspirations(
        self,
        storage,
        collector,
        mp_id: str = "",
        limit: int = 20,
        skip_diagnostics: bool = False,
    ) -> Dict:
        if not skip_diagnostics:
            diagnostics = self.status().get("diagnostics") or {}
            if diagnostics.get("blockers"):
                raise RuntimeError(diagnostics.get("summary") or "运行环境异常，无法同步到素材库")
        existing_urls = {
            _safe_text(item.source_url)
            for item in storage.list_inspirations(account_id=self.account_id, limit=10000)
            if _safe_text(item.source_url)
        }
        state = self.load_state()
        mp_lookup = {
            _safe_text(item.get("id")): item
            for item in (state.get("mps") or [])
            if _safe_text(item.get("id"))
        }
        articles = self.list_articles(mp_id=mp_id, limit=max(1, int(limit) * 5), include_content=True).get("items", [])

        created = []
        skipped = 0
        for article in articles:
            source_url = _safe_text(article.get("url"))
            if not source_url or source_url in existing_urls:
                skipped += 1
                continue

            current_mp_id = _safe_text(mp_id) or _safe_text(article.get("mp_id"))
            mp_info = mp_lookup.get(current_mp_id, {})
            raw_html = self._load_article_html(article)
            content_html = collector.sanitize_content_html(raw_html) if raw_html else ""
            content_text = (
                BeautifulSoup(content_html, "html.parser").get_text(separator="\n", strip=True)
                if content_html
                else _safe_text(article.get("description"))
            )
            images = self._extract_images_from_html(content_html)
            cover = _safe_text(article.get("topic_image") or article.get("cover"))
            if cover and cover not in images:
                images.insert(0, cover)

            publish_time = article.get("publish_time")
            metadata = {
                "wechat_login_state": True,
                "wechat_mp_id": current_mp_id,
                "wechat_mp_name": _safe_text(mp_info.get("name")),
                "publish_time": publish_time,
                "cover": _safe_text(article.get("cover")),
                "topic_image": _safe_text(article.get("topic_image")),
                "content_cache": article.get("content_cache") or {},
            }

            record = InspirationRecord(
                id=str(uuid.uuid4()),
                source_url=source_url,
                source_type="wechat_login_state",
                source_account=_safe_text(mp_info.get("name")) or "公众号平台",
                title=_safe_text(article.get("title")) or "未命名文章",
                author=_safe_text(article.get("author")),
                summary=_safe_text(article.get("description")),
                content=content_text,
                content_html=content_html,
                images=images,
                status=InspirationStatus.COLLECTED,
                account_id=self.account_id,
                metadata=metadata,
                collected_at=datetime.fromtimestamp(int(publish_time)) if publish_time else datetime.now(),
            )
            storage.create_inspiration(record)
            existing_urls.add(source_url)
            created.append(record)
            if len(created) >= int(limit):
                break

        return {
            "ok": True,
            "inserted": len(created),
            "skipped": skipped,
            "records": [record.model_dump(mode="json") for record in created],
        }

    def full_flow(
        self,
        storage,
        collector,
        mp_id: str = "",
        keyword: str = "",
        pick: int = 1,
        pages: int = 1,
        mode: str = "api",
        with_content: bool = False,
        content_limit: int = 10,
        sync_limit: int = 20,
    ) -> Dict:
        diagnostics = self.status().get("diagnostics") or {}
        if diagnostics.get("blockers"):
            raise RuntimeError(diagnostics.get("summary") or "运行环境异常，无法执行全流程")
        target_mp_id = _safe_text(mp_id)
        added = {}
        if not target_mp_id and _safe_text(keyword):
            add_result = self.add_mp(keyword=keyword, pick=pick)
            added = add_result.get("added") or {}
            target_mp_id = _safe_text(added.get("id"))

        if not target_mp_id:
            target_mp_id = _safe_text(self.metadata.get("wechat_default_mp_id"))
        if not target_mp_id:
            raise RuntimeError("full-flow 需要 mp_id，或提供 keyword + pick")

        pull_result = self.pull_articles(mp_id=target_mp_id, pages=pages, mode=mode, with_content=with_content)
        batch_result = {}
        if with_content:
            batch_result = self.batch_fetch_content(
                mp_id=target_mp_id,
                limit=content_limit,
                skip_existing=True,
                continue_on_error=True,
                sleep_sec=0.8,
            )
        sync_result = self.sync_articles_to_inspirations(storage=storage, collector=collector, mp_id=target_mp_id, limit=sync_limit)
        return {
            "ok": True,
            "mp_id": target_mp_id,
            "added": added,
            "pull": pull_result,
            "batch_content": batch_result,
            "sync": sync_result,
        }
