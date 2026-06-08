from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse
import urllib.error
import urllib.request
import struct

from config import Config
from modules.feishu import FeishuBitable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = PROJECT_ROOT / "scripts" / "internal" / "wechat_demo_wrapper.py"
FIXED_QR_FILENAME = "qr_login.png"


def _project_demo_cli_candidates(project_root: Path) -> List[str]:
    root = project_root.resolve()
    return [
        str((root / "demo_cli" / "wechat_demo_cli.py").resolve()),
        str((root / "third_party" / "we-mp-rss" / "demo_cli" / "wechat_demo_cli.py").resolve()),
        str((root / "release" / "wechat-demo-cli-package-2026-04-01-clean" / "demo_cli" / "wechat_demo_cli.py").resolve()),
        str((root / "third_party" / "wechat-demo-cli" / "demo_cli" / "wechat_demo_cli.py").resolve()),
        str((root / "tools" / "wechat-demo-cli" / "demo_cli" / "wechat_demo_cli.py").resolve()),
    ]


def _safe_text(value) -> str:
    return str(value or "").strip()


def _normalize_qr_display(value: str) -> str:
    raw = _safe_text(value).lower()
    # Disable terminal ASCII route globally: only keep image-oriented modes.
    if raw == "open":
        return "open"
    return "none"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _chunked(items: List[Dict], size: int) -> List[List[Dict]]:
    out = []
    for i in range(0, len(items), size):
        out.append(items[i : i + size])
    return out


def _read_png_size(path: Path) -> Optional[tuple]:
    try:
        with path.open("rb") as f:
            header = f.read(24)
        if len(header) < 24:
            return None
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width = struct.unpack(">I", header[16:20])[0]
        height = struct.unpack(">I", header[20:24])[0]
        return (int(width), int(height))
    except Exception:
        return None


def _try_upscale_small_qr(path: Path, min_side: int = 360) -> bool:
    dims = _read_png_size(path)
    if not dims:
        return False
    w, h = dims
    if w >= min_side and h >= min_side:
        return True
    try:
        from PIL import Image  # type: ignore
    except Exception:
        # macOS fallback without Pillow
        tmp_path = path.with_name(f"{path.stem}.upscaled{path.suffix}")
        try:
            subprocess.run(
                ["sips", "-Z", str(max(min_side, 600)), str(path), "--out", str(tmp_path)],
                capture_output=True,
                check=False,
                text=True,
            )
            if tmp_path.exists() and tmp_path.stat().st_size > 0:
                tmp_dims = _read_png_size(tmp_path)
                if tmp_dims and min(tmp_dims) >= min_side:
                    tmp_path.replace(path)
                    return True
        except Exception:
            pass
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
        return False
    try:
        scale = max(2, int((min_side + max(w, h) - 1) // max(w, h)))
        with Image.open(path) as img:
            resized = img.resize((w * scale, h * scale), Image.NEAREST)
            resized.save(path)
        return True
    except Exception:
        return False


def _is_plausible_qr_image(path: Path) -> bool:
    try:
        size = path.stat().st_size
    except Exception:
        return False
    if size < 500:
        return False
    dims = _read_png_size(path)
    if dims:
        w, h = dims
        if w < 80 or h < 80:
            return False
        # Some environments produce valid but tiny QR images (e.g. 122x123);
        # try to upscale once, but still allow the original image when Pillow is unavailable.
        if (w < 180 or h < 180) and size >= 1000:
            _try_upscale_small_qr(path)
            dims_after = _read_png_size(path)
            if dims_after:
                w, h = dims_after
        if w > 5000 or h > 5000:
            return False
    return True


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
    # Some invalid links include login_appid= (empty), which always returns blank.
    if "login_appid" in query and not _safe_text((query.get("login_appid") or [""])[0]):
        return ""
    has_uuid = bool(_safe_text((query.get("uuid") or [""])[0]))
    has_random = bool(_safe_text((query.get("random") or [""])[0]))
    if not (has_uuid or has_random):
        return ""
    return raw


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


class WechatIngestService:
    """Multi-account WeChat ingest service based on external wechat-demo CLI."""

    def __init__(
        self,
        account: Optional[Dict] = None,
        python_bin: str = "python3",
        project_root: Optional[str] = None,
    ):
        self.account = account or {}
        self.account_id = _safe_text(self.account.get("id")) or "default"
        self.account_name = _safe_text(self.account.get("name")) or self.account_id
        self.project_root = Path(project_root or PROJECT_ROOT).resolve()

        self.workspace_dir = self._resolve_workspace_dir()
        self.runtime_cwd = self._resolve_runtime_cwd()
        self.state_dir = self._resolve_state_dir()
        self.state_file = self.state_dir / "state.json"
        self.login_daemon_pid_file = self.state_dir / "login_daemon.pid"
        self.login_daemon_log_file = self.state_dir / "login_daemon.log"
        self.demo_cli_path = self._resolve_demo_cli_path()
        self.python_bin = self._resolve_python_bin(python_bin)

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_cwd.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._prepare_runtime_support_files()

    def _resolve_workspace_dir(self) -> Path:
        raw = _safe_text(self.account.get("wechat_workspace"))
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
        return (self.project_root / "output" / "wechat_accounts" / self.account_id).resolve()

    def _resolve_runtime_cwd(self) -> Path:
        raw = _safe_text(self.account.get("wechat_runtime_cwd"))
        if raw:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = self.workspace_dir / path
            return path.resolve()
        return (self.workspace_dir / "runtime").resolve()

    def _resolve_state_dir(self) -> Path:
        raw = _safe_text(self.account.get("wechat_state_dir"))
        if raw:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = self.workspace_dir / path
            return path.resolve()
        return (self.workspace_dir / "state").resolve()

    def _resolve_demo_cli_path(self) -> str:
        primary_candidates = [
            _safe_text(self.account.get("wechat_demo_cli")),
            _safe_text(os.getenv("OPENCLAW_WECHAT_DEMO_CLI")),
            _safe_text(Config.OPENCLAW_WECHAT_DEMO_CLI),
        ]
        candidates: List[str] = []
        for cand in primary_candidates:
            if not cand:
                continue
            p = Path(cand).expanduser()
            if not p.is_absolute():
                p = (self.project_root / p).resolve()
            candidates.append(str(p))
        candidates.extend(_project_demo_cli_candidates(self.project_root))

        seen = set()
        deduped: List[str] = []
        for cand in candidates:
            if cand in seen:
                continue
            seen.add(cand)
            deduped.append(cand)

        for cand in deduped:
            if not cand:
                continue
            p = Path(cand).expanduser()
            if p.exists() and p.is_file():
                return str(p.resolve())
        if primary_candidates:
            return _safe_text(primary_candidates[0])
        return ""

    def ensure_ready(self):
        if not WRAPPER_PATH.exists():
            raise RuntimeError(f"wechat wrapper missing: {WRAPPER_PATH}")
        cli = Path(self.demo_cli_path).expanduser()
        if not cli.exists() or not cli.is_file():
            raise RuntimeError(
                "wechat_demo_cli.py 不可用，请在账户配置或环境变量 OPENCLAW_WECHAT_DEMO_CLI 中提供有效绝对路径"
            )

    def _resolve_python_bin(self, preferred: str) -> str:
        picked = _safe_text(preferred) or _safe_text(os.getenv("OPENCLAW_WECHAT_DEMO_PYTHON")) or "python3"
        cli_path = Path(self.demo_cli_path).expanduser()
        demo_root = cli_path.parent.parent if cli_path.exists() else None
        if demo_root:
            venv_python = demo_root / ".venv" / "bin" / "python"
            if picked in {"python", "python3"} and venv_python.exists():
                return str(venv_python)
        return picked

    def _prepare_runtime_support_files(self):
        cli_path = Path(self.demo_cli_path).expanduser()
        if not cli_path.exists():
            return
        demo_root = cli_path.parent.parent
        if not demo_root.exists():
            return

        for name in ("config.yaml", "config.example.yaml"):
            src = demo_root / name
            dst = self.runtime_cwd / name
            if src.exists() and not dst.exists():
                try:
                    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                except Exception:
                    pass

    def _build_demo_cmd(self, args: List[str]) -> List[str]:
        self.ensure_ready()
        return [
            self.python_bin,
            str(WRAPPER_PATH),
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
        # Use chromium by default in our isolated runtime; firefox/webkit may not be installed.
        env.setdefault("BROWSER_TYPE", "chromium")
        return env

    def _run_demo(self, args: List[str], timeout: int = 600, check: bool = True) -> Dict:
        cmd = self._build_demo_cmd(args)

        env = self._demo_env()

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_root,
                env=env,
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
            combined = _safe_text((out.get("stderr") or out.get("stdout") or "").splitlines()[-1] if (out.get("stderr") or out.get("stdout")) else "")
            raise RuntimeError(combined or f"wechat demo command failed: code={out.get('return_code')}")
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
        if pid <= 0:
            return
        if not self._pid_alive(pid):
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
        lines = raw.splitlines()
        return "\n".join(lines[-max_lines:])

    def _start_login_daemon(
        self,
        timeout: int,
        token_wait_timeout: int,
        thread_join_timeout: int,
    ) -> Dict:
        # Ensure a single daemon per account and avoid stale QR cache.
        self._stop_login_daemon_if_running()
        fixed = self.fixed_qr_image_path()
        for p in [fixed, self.state_dir / "last_qr.png"]:
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        args = [
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
        ]
        cmd = self._build_demo_cmd(args)
        env = self._demo_env()

        self.login_daemon_log_file.parent.mkdir(parents=True, exist_ok=True)
        log_fp = self.login_daemon_log_file.open("w", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            log_fp.close()
        except Exception:
            pass
        self.login_daemon_pid_file.write_text(str(proc.pid), encoding="utf-8")

        # Wait briefly until QR image is produced.
        deadline = time.time() + 22
        qr_path = None
        while time.time() < deadline:
            qr_path = self.get_qr_image_path()
            if qr_path:
                break
            if proc.poll() is not None:
                break
            time.sleep(0.5)

        return {
            "pid": int(proc.pid),
            "running": self._pid_alive(proc.pid),
            "qr_image_path": str(qr_path) if qr_path else "",
            "log_tail": self._tail_daemon_log(),
        }

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

        now = time.time()
        if ts > 0 and now - ts > float(timeout_sec):
            try:
                lock_path.unlink()
            except Exception:
                pass
            return

        if pid <= 0:
            return

        alive = True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            alive = False
        except PermissionError:
            alive = True
        except Exception:
            alive = True

        if not alive:
            try:
                lock_path.unlink()
            except Exception:
                pass

    def _demo_root(self) -> Path:
        cli = Path(self.demo_cli_path).expanduser()
        return cli.parent.parent if cli.exists() else self.project_root

    def fixed_qr_image_path(self) -> Path:
        return (self.state_dir / FIXED_QR_FILENAME).resolve()

    def _qr_image_candidates(self, runtime: Optional[Dict] = None) -> List[Path]:
        runtime = runtime if isinstance(runtime, dict) else {}
        demo_root = self._demo_root()
        candidates: List[Path] = [
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
        fixed = self.fixed_qr_image_path()
        last_qr = (self.state_dir / "last_qr.png").resolve()
        if (not fixed.exists()) and last_qr.exists() and last_qr.is_file():
            try:
                fixed.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(last_qr), str(fixed))
            except Exception:
                pass

        latest = None
        latest_mtime = -1.0
        for path in self._qr_image_candidates(runtime):
            if not path.exists() or not path.is_file():
                continue
            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0
            # Ignore placeholder/invalid qr images.
            if not _is_plausible_qr_image(path):
                continue
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
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://mp.weixin.qq.com/",
            },
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
            if target.exists() and _is_plausible_qr_image(target):
                return target
            return None
        except Exception:
            return None

    def load_state(self) -> Dict:
        if not self.state_file.exists():
            return {"mps": [], "articles": {}, "meta": {}}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"mps": [], "articles": {}, "meta": {}}
            data.setdefault("mps", [])
            data.setdefault("articles", {})
            data.setdefault("meta", {})
            return data
        except Exception:
            return {"mps": [], "articles": {}, "meta": {}}

    def _save_state(self, state: Dict):
        base = {"mps": [], "articles": {}, "meta": {}}
        if isinstance(state, dict):
            base.update(state)
        base.setdefault("mps", [])
        base.setdefault("articles", {})
        base.setdefault("meta", {})
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")

    def _update_state_meta(self, **kwargs):
        state = self.load_state()
        meta = state.get("meta") or {}
        for k, v in kwargs.items():
            if v is None:
                continue
            meta[k] = v
        meta["updated_at"] = int(time.time())
        state["meta"] = meta
        self._save_state(state)

    def status(self) -> Dict:
        self._cleanup_dead_daemon_pid()
        daemon_pid = self._read_daemon_pid()
        result = self._run_demo(["status"], timeout=180, check=False)
        parsed = _extract_json_from_text(result.get("stdout", ""))
        runtime = parsed if isinstance(parsed, dict) else {}
        qr_path = self.get_qr_image_path(runtime=runtime)
        state = self.load_state()
        meta = state.get("meta") or {}
        qr_remote_url = _normalize_qr_remote_url(_safe_text(meta.get("qr_remote_url")))
        if not qr_remote_url:
            qr_remote_url = _extract_qr_remote_url(result.get("stdout", ""))
        qr_path = self.get_qr_image_path(runtime=runtime)
        if qr_path:
            qr_path = self._persist_qr_image(qr_path)
        elif qr_remote_url:
            qr_path = self._download_qr_image(qr_remote_url)
        fixed_qr_path = self.fixed_qr_image_path()
        return {
            "ok": bool(result.get("ok")),
            "runtime": runtime,
            "state": {
                "mp_count": len(state.get("mps") or []),
                "article_count": sum(len(v or []) for v in (state.get("articles") or {}).values()),
                "state_file": str(self.state_file),
                "workspace_dir": str(self.workspace_dir),
                "runtime_cwd": str(self.runtime_cwd),
                "demo_cli_path": self.demo_cli_path,
                "qr_image_exists": bool(qr_path),
                "qr_image_path": str(qr_path) if qr_path else "",
                "qr_image_fixed_path": str(fixed_qr_path),
                "qr_remote_url": qr_remote_url,
                "login_daemon_pid": daemon_pid or 0,
                "login_daemon_running": bool(daemon_pid and self._pid_alive(daemon_pid)),
            },
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
        # Prevent stale lock files from causing long "already running" waits.
        self._cleanup_stale_login_lock()
        if not wait:
            daemon = self._start_login_daemon(
                timeout=max(120, int(timeout)),
                token_wait_timeout=max(20, int(token_wait_timeout)),
                thread_join_timeout=max(10, int(thread_join_timeout)),
            )
            summary = self.status()
            qr_path = self.get_qr_image_path(runtime=summary.get("runtime"))
            summary["login_ok"] = bool(daemon.get("running"))
            summary["login_mode"] = "daemon"
            summary["login_daemon_pid"] = int(daemon.get("pid") or 0)
            summary["login_timeout"] = False
            summary["login_return_code"] = 0
            summary["qr_display_used"] = "none"
            summary["qr_image_exists"] = bool(qr_path)
            summary["qr_image_path"] = str(qr_path) if qr_path else ""
            summary["qr_image_fixed_path"] = str(self.fixed_qr_image_path())
            summary["login_stdout"] = _safe_text(daemon.get("log_tail"))
            summary["login_stderr"] = ""
            summary["login_note"] = "已启动后台登录进程，请在二维码弹窗中扫码并确认。"
            self._update_state_meta(
                qr_generated_at=_now_ms(),
                qr_image_path=(str(qr_path) if qr_path else ""),
                qr_image_fixed_path=str(self.fixed_qr_image_path()),
            )
            return summary

        picked_qr_display = _normalize_qr_display(qr_display)
        args = ["login"]
        args.append("--wait" if wait else "--no-wait")
        args += [
            "--qr-display",
            picked_qr_display,
            "--timeout",
            str(max(30, int(timeout))),
            "--token-wait-timeout",
            str(max(10, int(token_wait_timeout))),
            "--thread-join-timeout",
            str(max(5, int(thread_join_timeout))),
        ]
        if wait:
            run_timeout = max(180, int(timeout) + int(token_wait_timeout) + int(thread_join_timeout))
        else:
            run_timeout = max(70, min(180, int(timeout) + int(token_wait_timeout) + int(thread_join_timeout)))
        result = self._run_demo(args, timeout=run_timeout, check=False)
        summary = self.status()
        summary["login_ok"] = bool(result.get("ok"))
        summary["login_stdout"] = result.get("stdout", "")
        summary["login_stderr"] = result.get("stderr", "")
        summary["login_return_code"] = result.get("return_code")
        summary["login_timeout"] = bool(result.get("timeout"))
        summary["qr_display_used"] = picked_qr_display
        qr_remote_url = _extract_qr_remote_url(result.get("stdout", ""))
        qr_path = self.get_qr_image_path(runtime=summary.get("runtime"))
        if qr_path:
            qr_path = self._persist_qr_image(qr_path)
        elif qr_remote_url:
            qr_path = self._download_qr_image(qr_remote_url)
        summary["qr_image_exists"] = bool(qr_path)
        summary["qr_image_path"] = str(qr_path) if qr_path else ""
        summary["qr_image_fixed_path"] = str(self.fixed_qr_image_path())
        summary["qr_remote_url"] = qr_remote_url
        self._update_state_meta(
            qr_remote_url=qr_remote_url,
            qr_generated_at=_now_ms(),
            qr_image_path=(str(qr_path) if qr_path else ""),
            qr_image_fixed_path=str(self.fixed_qr_image_path()),
        )
        return summary

    def search_mp(self, keyword: str, limit: int = 10, offset: int = 0) -> Dict:
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
        return {
            "ok": True,
            "keyword": kw,
            "items": items,
            "count": len(items),
        }

    def list_mps(self) -> Dict:
        state = self.load_state()
        items = state.get("mps") or []
        return {
            "ok": True,
            "items": items,
            "count": len(items),
        }

    def add_mp(self, keyword: str, pick: int = 1, limit: int = 10, offset: int = 0) -> Dict:
        kw = _safe_text(keyword)
        if not kw:
            raise RuntimeError("keyword is required")

        before = self.list_mps().get("items") or []
        before_ids = {str(x.get("id") or "").strip() for x in before}

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
        added = None
        for item in after:
            item_id = str(item.get("id") or "").strip()
            if item_id and item_id not in before_ids:
                added = item
                break
        if not added and after:
            added = after[-1]

        return {
            "ok": True,
            "added": added or {},
            "items": after,
            "count": len(after),
        }

    def pull_articles(self, mp_id: str, pages: int = 1, mode: str = "api", with_content: bool = False) -> Dict:
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
        listed = self.list_articles(mp_id=target_mp_id)

        return {
            "ok": True,
            "mp_id": target_mp_id,
            "count": listed.get("count", 0),
            "items": listed.get("items", []),
            "stdout": result.get("stdout", ""),
        }

    def list_articles(self, mp_id: str = "", limit: int = 50) -> Dict:
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
        safe_limit = max(1, int(limit)) if int(limit) != 0 else 0
        if safe_limit > 0:
            items = items[:safe_limit]

        return {
            "ok": True,
            "mp_id": target,
            "count": len(items),
            "items": items,
        }

    def batch_fetch_content(
        self,
        mp_id: str = "",
        limit: int = 10,
        skip_existing: bool = True,
        continue_on_error: bool = True,
        sleep_sec: float = 0.8,
    ) -> Dict:
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

    def _feishu_client(self) -> FeishuBitable:
        app_id = _safe_text(self.account.get("feishu_app_id")) or _safe_text(Config.FEISHU_APP_ID)
        app_secret = _safe_text(self.account.get("feishu_app_secret")) or _safe_text(Config.FEISHU_APP_SECRET)
        app_token = _safe_text(self.account.get("feishu_app_token")) or _safe_text(Config.FEISHU_APP_TOKEN)
        return FeishuBitable(app_id, app_secret, app_token)

    def _find_table_id(self, feishu: FeishuBitable, preferred_name: str, fallback_names: List[str]) -> Optional[str]:
        table_id = feishu.get_table_id_by_name(preferred_name)
        if table_id:
            return table_id
        tables = feishu.list_tables()
        for item in tables:
            name = _safe_text(item.get("name"))
            if any(x in name for x in fallback_names):
                return item.get("table_id")
        return None

    def sync_articles_to_inspiration(self, mp_id: str = "", limit: int = 20) -> Dict:
        feishu = self._feishu_client()
        if not feishu._get_token():
            raise RuntimeError("飞书鉴权失败，请检查当前账户 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_APP_TOKEN")

        preferred_name = _safe_text(self.account.get("feishu_inspiration_table")) or _safe_text(Config.FEISHU_INSPIRATION_TABLE)
        table_id = self._find_table_id(feishu, preferred_name, ["内容灵感库"])
        if not table_id:
            raise RuntimeError("找不到灵感库表，请检查 FEISHU_INSPIRATION_TABLE")

        columns = set(feishu.get_table_columns(table_id) or [])
        records_data = feishu.list_records(table_id)
        existing_urls = set()
        for item in records_data.get("items", []):
            url = _safe_text(item.get("fields", {}).get("文章 URL"))
            if url:
                existing_urls.add(url)

        articles = self.list_articles(mp_id=mp_id, limit=max(1, int(limit) * 5)).get("items", [])
        selected = []
        for art in articles:
            url = _safe_text(art.get("url"))
            if not url or url in existing_urls:
                continue
            selected.append(art)
            existing_urls.add(url)
            if len(selected) >= int(limit):
                break

        if not selected:
            return {
                "ok": True,
                "inserted": 0,
                "skipped": len(articles),
                "table_id": table_id,
                "table_name": preferred_name,
                "records": [],
            }

        now_ts = _now_ms()
        rows = []
        for art in selected:
            title = _safe_text(art.get("title")) or "未命名文章"
            row = {
                "标题": title,
                "原始标题": title,
                "文章 URL": _safe_text(art.get("url")),
                "处理状态": "待分析",
                "AI 推荐理由": f"来源: 微信登录态采集 ({_safe_text(mp_id) or 'all'})",
                "所属领域": "微信公众号",
                "同步时间": now_ts,
            }
            if columns:
                row = {k: v for k, v in row.items() if k in columns}
            rows.append(row)

        created = []
        for batch in _chunked(rows, 100):
            result = feishu.add_records_with_result(table_id, batch)
            if not result.get("ok"):
                raise RuntimeError(f"写入灵感库失败: {result.get('raw')}")
            created.extend(result.get("records") or [])

        return {
            "ok": True,
            "inserted": len(created),
            "selected": len(selected),
            "table_id": table_id,
            "table_name": preferred_name,
            "records": created,
        }

    def full_flow(
        self,
        mp_id: str = "",
        keyword: str = "",
        pick: int = 1,
        pages: int = 1,
        mode: str = "api",
        with_content: bool = False,
        content_limit: int = 10,
        sync_limit: int = 20,
    ) -> Dict:
        target_mp_id = _safe_text(mp_id)

        added = {}
        if not target_mp_id and _safe_text(keyword):
            add_result = self.add_mp(keyword=keyword, pick=pick)
            added = add_result.get("added") or {}
            target_mp_id = _safe_text(added.get("id"))

        if not target_mp_id:
            target_mp_id = _safe_text(self.account.get("wechat_default_mp_id"))
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
        sync_result = self.sync_articles_to_inspiration(mp_id=target_mp_id, limit=sync_limit)

        return {
            "ok": True,
            "mp_id": target_mp_id,
            "added": added,
            "pull": pull_result,
            "batch_content": batch_result,
            "sync": sync_result,
        }
