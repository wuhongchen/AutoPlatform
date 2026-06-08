#!/usr/bin/env python3
"""Run external wechat_demo_cli.py with account-isolated state directory."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
import types
from pathlib import Path


def _load_module(cli_path: Path):
    spec = importlib.util.spec_from_file_location("wechat_demo_cli_runtime", str(cli_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load cli module: {cli_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["wechat_demo_cli_runtime"] = module
    spec.loader.exec_module(module)
    return module


def _install_runtime_shims():
    # Vendored runtime expects jobs.notice.sys_notice in success callback flow.
    # AutoPlatform does not ship that module, and the import happens before
    # token persistence, so provide a no-op shim.
    jobs_module = sys.modules.get("jobs")
    if jobs_module is None:
        jobs_module = types.ModuleType("jobs")
        jobs_module.__path__ = []  # mark as package-like for submodule import
        sys.modules["jobs"] = jobs_module

    notice_module = sys.modules.get("jobs.notice")
    if notice_module is None:
        notice_module = types.ModuleType("jobs.notice")

        def _noop_sys_notice(*_args, **_kwargs):
            return None

        notice_module.sys_notice = _noop_sys_notice
        sys.modules["jobs.notice"] = notice_module
        setattr(jobs_module, "notice", notice_module)


def _patch_runtime_for_qr(state_dir: Path):
    fixed_qr_path = (state_dir / "qr_login.png").resolve()
    # 0) Fix demo cli QR path resolver: use current runtime cwd instead of project ROOT.
    try:
        import pathlib

        def _patched_resolve_qr_path_from_result(qr_result):
            code_path = str((qr_result or {}).get("code") or "").split("?")[0].strip()
            if code_path and not code_path.startswith("http"):
                path = pathlib.Path(code_path)
                if path.is_absolute():
                    if str(path).startswith("/static/"):
                        path = pathlib.Path.cwd() / code_path.lstrip("/")
                else:
                    path = pathlib.Path.cwd() / code_path.lstrip("/")
                return path.resolve()
            return (pathlib.Path.cwd() / "static" / "wx_qrcode.png").resolve()

        import wechat_demo_cli_runtime as demo_runtime

        if hasattr(demo_runtime, "_resolve_qr_path_from_result"):
            demo_runtime._resolve_qr_path_from_result = _patched_resolve_qr_path_from_result
    except Exception:
        pass

    # 1) Ensure QR image is not blocked during login (upstream defaults dis_image=True).
    try:
        from driver.playwright_driver import PlaywrightController

        _orig_start_browser = PlaywrightController.start_browser

        def _patched_start_browser(self, *args, **kwargs):
            kwargs["dis_image"] = False
            kwargs["anti_crawler"] = False
            kwargs["browser_name"] = "chromium"
            return _orig_start_browser(self, *args, **kwargs)

        PlaywrightController.start_browser = _patched_start_browser
    except Exception:
        pass

    # 2) Persist latest QR image before upstream cleanup removes it.
    try:
        from driver import wx as wx_module

        # Always write QR image to fixed path for account runtime.
        try:
            wx_module.Wx.wx_login_url = str(fixed_qr_path)
        except Exception:
            pass
        try:
            if hasattr(wx_module, "WX_API") and wx_module.WX_API is not None:
                wx_module.WX_API.wx_login_url = str(fixed_qr_path)
        except Exception:
            pass

        _orig_clean = wx_module.Wx.Clean

        def _patched_clean(self, *args, **kwargs):
            keep_fixed_qr = False
            try:
                src = Path(str(getattr(self, "wx_login_url", "static/wx_qrcode.png"))).expanduser()
                if src.exists() and src.is_file():
                    dst = state_dir / "last_qr.png"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(src), str(dst))
                try:
                    keep_fixed_qr = src.resolve() == fixed_qr_path
                except Exception:
                    keep_fixed_qr = False
            except Exception:
                pass

            # Keep the fixed QR image on disk for external viewers/UI.
            # Upstream Clean() deletes self.wx_login_url by design.
            if keep_fixed_qr:
                return True
            return _orig_clean(self, *args, **kwargs)

        wx_module.Wx.Clean = _patched_clean
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="wechat demo account wrapper")
    parser.add_argument("--cli-path", required=True, help="Absolute path to wechat_demo_cli.py")
    parser.add_argument("--state-dir", required=True, help="Per-account state directory")
    parser.add_argument("--cwd", default="", help="Optional working directory for runtime artifacts")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to wechat demo cli")
    ns = parser.parse_args()

    cli_path = Path(ns.cli_path).expanduser().resolve()
    if not cli_path.exists() or not cli_path.is_file():
        raise RuntimeError(f"wechat demo cli not found: {cli_path}")

    state_dir = Path(ns.state_dir).expanduser().resolve()
    state_dir.mkdir(parents=True, exist_ok=True)

    runtime_cwd = (Path(ns.cwd).expanduser().resolve() if ns.cwd else None)
    if runtime_cwd:
        runtime_cwd.mkdir(parents=True, exist_ok=True)
        os.chdir(runtime_cwd)

    passthrough_args = list(ns.args or [])
    if passthrough_args and passthrough_args[0] == "--":
        passthrough_args = passthrough_args[1:]
    if not passthrough_args:
        raise RuntimeError("missing passthrough command args")

    _install_runtime_shims()
    module = _load_module(cli_path)
    _patch_runtime_for_qr(state_dir)
    module.STATE_DIR = state_dir
    module.STATE_FILE = state_dir / "state.json"

    if hasattr(module, "_ensure_state_file"):
        module._ensure_state_file()

    sys.argv = [str(cli_path)] + passthrough_args
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
