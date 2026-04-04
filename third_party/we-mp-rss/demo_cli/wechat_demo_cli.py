#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WX_API = None
Success = None
get_token_value = None
WXArticleFetcher = None


WECHAT_BASE = "https://mp.weixin.qq.com"
STATE_DIR = Path(__file__).resolve().parent / "data"
STATE_FILE = STATE_DIR / "state.json"
DEFAULT_TIMEOUT = 180
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


@dataclass
class MpRecord:
    id: str
    name: str
    fakeid: str
    alias: str = ""
    avatar: str = ""
    intro: str = ""


def _install_colorama_fallback() -> None:
    try:
        import colorama  # noqa: F401
        return
    except Exception:
        pass

    class _DummyColor:
        def __getattr__(self, _name: str) -> str:
            return ""

    class _DummyColoramaModule:
        Fore = _DummyColor()
        Back = _DummyColor()
        Style = _DummyColor()

        @staticmethod
        def init(*_args: Any, **_kwargs: Any) -> None:
            return None

    sys.modules["colorama"] = _DummyColoramaModule()


def _ensure_config_file() -> None:
    config_path = ROOT / "config.yaml"
    example_path = ROOT / "config.example.yaml"
    if config_path.exists():
        return
    if example_path.exists():
        shutil.copyfile(example_path, config_path)


def _load_token_runtime() -> None:
    global get_token_value
    if get_token_value is not None:
        return
    _install_colorama_fallback()
    _ensure_config_file()

    try:
        from driver.token import get as _get_token_value
    except Exception as exc:
        raise RuntimeError(
            f"failed to import token runtime: {exc}. "
            "Try: pip install -r requirements.txt"
        ) from exc

    get_token_value = _get_token_value


def _load_wx_runtime() -> None:
    global WX_API, Success
    if WX_API is not None and Success is not None:
        return
    _install_colorama_fallback()
    _ensure_config_file()

    try:
        from driver.base import WX_API as _WX_API
        from driver.success import Success as _Success
    except Exception as exc:
        raise RuntimeError(
            f"failed to import wx runtime: {exc}. "
            "Try: pip install -r requirements.txt"
        ) from exc

    WX_API = _WX_API
    Success = _Success


def _load_fetcher_runtime() -> None:
    global WXArticleFetcher
    if WXArticleFetcher is not None:
        return
    _install_colorama_fallback()
    _ensure_config_file()

    try:
        from driver.wxarticle import WXArticleFetcher as _WXArticleFetcher
    except Exception as exc:
        raise RuntimeError(
            f"failed to import article fetcher runtime: {exc}. "
            "Try: pip install -r requirements.txt"
        ) from exc

    WXArticleFetcher = _WXArticleFetcher


def _now_ts() -> int:
    return int(time.time())


def _ensure_state_file() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        initial = {
            "mps": [],
            "articles": {},
            "meta": {"created_at": _now_ts(), "updated_at": _now_ts()},
        }
        STATE_FILE.write_text(json.dumps(initial, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_state() -> Dict[str, Any]:
    _ensure_state_file()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "mps": [],
            "articles": {},
            "meta": {"created_at": _now_ts(), "updated_at": _now_ts()},
        }


def _save_state(state: Dict[str, Any]) -> None:
    state.setdefault("meta", {})
    state["meta"]["updated_at"] = _now_ts()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_token_cookie() -> Tuple[str, str]:
    _load_token_runtime()
    token = str(get_token_value("token", "") or "").strip()
    cookie = str(get_token_value("cookie", "") or "").strip()
    return token, cookie


def _auth_headers(referer: str, cookie: str) -> Dict[str, str]:
    return {
        "Cookie": cookie,
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": referer,
        "Accept": "application/json,text/plain,*/*",
        "X-Requested-With": "XMLHttpRequest",
    }


def _raise_if_invalid_session(msg: Dict[str, Any]) -> None:
    ret = int(msg.get("base_resp", {}).get("ret", 0))
    if ret == 0:
        return
    if ret == 200003:
        raise RuntimeError("Invalid Session: please run login first.")
    if ret == 200013:
        raise RuntimeError("Frequency control triggered by WeChat.")
    err = msg.get("base_resp", {}).get("err_msg", "unknown")
    raise RuntimeError(f"WeChat API error: ret={ret}, err={err}")


def _safe_decode_fakeid(fakeid: str) -> str:
    raw = str(fakeid or "").strip()
    if not raw:
        return ""
    try:
        padded = raw + ("=" * ((4 - len(raw) % 4) % 4))
        decoded = base64.b64decode(padded).decode("utf-8").strip()
        if decoded:
            return f"MP_WXS_{decoded}"
    except Exception:
        pass
    return f"MP_WXS_{raw}"


def _encode_fakeid_from_mp_id(mp_id: str) -> str:
    raw = str(mp_id or "").strip()
    if raw.startswith("MP_WXS_"):
        raw = raw[len("MP_WXS_") :]
    raw = raw.strip()
    if not raw:
        return ""
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")


def _normalize_mp(item: Dict[str, Any]) -> MpRecord:
    fakeid = str(item.get("fakeid", "") or "").strip()
    return MpRecord(
        id=_safe_decode_fakeid(fakeid),
        name=str(item.get("nickname") or item.get("name") or item.get("alias") or "unknown").strip(),
        fakeid=fakeid,
        alias=str(item.get("alias") or "").strip(),
        avatar=str(item.get("round_head_img") or item.get("head_img") or item.get("avatar") or "").strip(),
        intro=str(item.get("signature") or item.get("description") or "").strip(),
    )


def _search_mp(keyword: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    token, cookie = _get_token_cookie()
    if not token or not cookie:
        raise RuntimeError("Missing token/cookie. Run login first.")

    url = f"{WECHAT_BASE}/cgi-bin/searchbiz"
    params = {
        "action": "search_biz",
        "begin": offset,
        "count": limit,
        "query": keyword,
        "token": token,
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }
    resp = requests.get(url, params=params, headers=_auth_headers(url, cookie), timeout=20)
    resp.raise_for_status()
    msg = resp.json()
    _raise_if_invalid_session(msg)
    return list(msg.get("list") or [])


def _fetch_articles_api(fakeid: str, pages: int, with_content: bool) -> List[Dict[str, Any]]:
    _load_token_runtime()
    token, cookie = _get_token_cookie()
    if not token or not cookie:
        raise RuntimeError("Missing token/cookie. Run login first.")

    url = f"{WECHAT_BASE}/cgi-bin/appmsg"
    count = 5
    out: List[Dict[str, Any]] = []

    fetcher: Optional[WXArticleFetcher] = None
    if with_content:
        _load_fetcher_runtime()
        fetcher = WXArticleFetcher()

    try:
        for page in range(max(1, pages)):
            params = {
                "action": "list_ex",
                "begin": page * count,
                "count": count,
                "fakeid": fakeid,
                "type": "9",
                "token": token,
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
            }
            resp = requests.get(url, params=params, headers=_auth_headers(url, cookie), timeout=20)
            resp.raise_for_status()
            msg = resp.json()
            _raise_if_invalid_session(msg)

            rows = msg.get("app_msg_list") or []
            if not rows:
                break

            for item in rows:
                article = {
                    "id": str(item.get("aid") or item.get("appmsgid") or ""),
                    "title": str(item.get("title") or ""),
                    "url": str(item.get("link") or ""),
                    "description": str(item.get("digest") or ""),
                    "cover": str(item.get("cover") or ""),
                    "publish_time": int(item.get("update_time") or item.get("create_time") or 0),
                }
                if with_content and article["url"] and fetcher is not None:
                    detail = fetcher.get_article_content(article["url"])
                    article["content"] = detail.get("content") or ""
                    article["author"] = detail.get("author") or ""
                    article["topic_image"] = detail.get("topic_image") or ""
                out.append(article)
            time.sleep(1)
    finally:
        if fetcher is not None:
            try:
                fetcher.Close()
            except Exception:
                pass

    return out


def _fetch_articles_web(fakeid: str, pages: int, with_content: bool) -> List[Dict[str, Any]]:
    _load_token_runtime()
    token, cookie = _get_token_cookie()
    if not token or not cookie:
        raise RuntimeError("Missing token/cookie. Run login first.")

    url = f"{WECHAT_BASE}/cgi-bin/appmsgpublish"
    count = 5
    out: List[Dict[str, Any]] = []

    fetcher: Optional[WXArticleFetcher] = None
    if with_content:
        _load_fetcher_runtime()
        fetcher = WXArticleFetcher()

    try:
        for page in range(max(1, pages)):
            params = {
                "sub": "list",
                "sub_action": "list_ex",
                "begin": page * count,
                "count": count,
                "fakeid": fakeid,
                "token": token,
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
            }
            resp = requests.get(url, params=params, headers=_auth_headers(url, cookie), timeout=20)
            resp.raise_for_status()
            msg = resp.json()
            _raise_if_invalid_session(msg)

            publish_page_raw = msg.get("publish_page")
            if not publish_page_raw:
                break

            publish_page = publish_page_raw
            if isinstance(publish_page_raw, str):
                publish_page = json.loads(publish_page_raw)

            publish_list = list((publish_page or {}).get("publish_list") or [])
            if not publish_list:
                break

            for row in publish_list:
                publish_info = row.get("publish_info")
                if isinstance(publish_info, str):
                    publish_info = json.loads(publish_info)
                appmsgex = list((publish_info or {}).get("appmsgex") or [])
                for item in appmsgex:
                    article = {
                        "id": str(item.get("aid") or item.get("id") or ""),
                        "title": str(item.get("title") or ""),
                        "url": str(item.get("link") or ""),
                        "description": str(item.get("digest") or ""),
                        "cover": str(item.get("cover") or item.get("pic_url") or ""),
                        "publish_time": int(item.get("update_time") or item.get("create_time") or 0),
                    }
                    if with_content and article["url"] and fetcher is not None:
                        detail = fetcher.get_article_content(article["url"])
                        article["content"] = detail.get("content") or ""
                        article["author"] = detail.get("author") or ""
                        article["topic_image"] = detail.get("topic_image") or ""
                    out.append(article)
            time.sleep(1)
    finally:
        if fetcher is not None:
            try:
                fetcher.Close()
            except Exception:
                pass

    return out


def _find_mp(state: Dict[str, Any], mp_id: str) -> Optional[Dict[str, Any]]:
    for item in state.get("mps", []):
        if str(item.get("id")) == mp_id:
            return item
    return None


def _print_mps(items: List[Dict[str, Any]]) -> None:
    if not items:
        print("No mp records.")
        return
    print("# | mp_id | name | fakeid | alias")
    for idx, item in enumerate(items, start=1):
        print(
            f"{idx} | {item.get('id','')} | {item.get('name','')} | "
            f"{item.get('fakeid','')} | {item.get('alias','')}"
        )


def _print_articles(items: List[Dict[str, Any]], limit: int = 20) -> None:
    if not items:
        print("No articles.")
        return
    print("# | article_id | publish_time | title | url")
    for idx, item in enumerate(items[:limit], start=1):
        print(
            f"{idx} | {item.get('id','')} | {item.get('publish_time','')} | "
            f"{item.get('title','')} | {item.get('url','')}"
        )


def _resolve_qr_path_from_result(qr_result: Dict[str, Any]) -> Path:
    code_path = str((qr_result or {}).get("code") or "").split("?")[0].strip()
    if code_path and not code_path.startswith("http"):
        path = Path(code_path)
        if path.is_absolute():
            # Some runtime returns "/static/wx_qrcode.png", which is project-relative.
            if str(path).startswith("/static/"):
                path = ROOT / code_path.lstrip("/")
        else:
            path = ROOT / code_path.lstrip("/")
        return path.resolve()
    return (ROOT / "static" / "wx_qrcode.png").resolve()


def _wait_qr_file_ready(path: Path, timeout: int = 15) -> bool:
    end = time.time() + max(1, timeout)
    while time.time() < end:
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            return True
        time.sleep(0.3)
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _print_qr_terminal(path: Path) -> None:
    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError(f"Pillow is required for terminal QR render: {exc}") from exc

    img = Image.open(path).convert("L")
    max_w = 60
    w, h = img.size
    if w > max_w:
        scale = max_w / float(w)
        img = img.resize((max_w, max(1, int(h * scale))), Image.NEAREST)

    bw = img.point(lambda p: 0 if p < 128 else 255, mode="1")
    w, h = bw.size

    print("\nScan this QR in terminal:\n")
    for y in range(h):
        row = []
        for x in range(w):
            pixel = bw.getpixel((x, y))
            row.append("██" if pixel == 0 else "  ")
        print("".join(row))
    print("")


def _open_qr_image(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return
    if sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", str(path)], check=False)
        return
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    webbrowser.open(path.as_uri())


def _wait_token_ready(timeout: int = 20, interval: float = 1.0) -> Tuple[str, str]:
    end = time.time() + max(1, timeout)
    last_token = ""
    last_cookie = ""
    while time.time() < end:
        try:
            token, cookie = _get_token_cookie()
            last_token, last_cookie = token, cookie
            if token:
                return token, cookie
        except Exception:
            pass
        time.sleep(max(0.2, interval))
    return last_token, last_cookie


def _join_wx_login_thread(timeout: int = 10) -> bool:
    try:
        thread = getattr(WX_API, "thread", None)
        if thread is None:
            return True
        if not hasattr(thread, "is_alive"):
            return True
        if not thread.is_alive():
            return True
        thread.join(max(0, timeout))
        return not thread.is_alive()
    except Exception:
        return False


def cmd_login(args: argparse.Namespace) -> None:
    _load_wx_runtime()
    if hasattr(WX_API, "GetCode"):
        qr_result = WX_API.GetCode(Success)
    elif hasattr(WX_API, "get_qr_code"):
        qr_result = WX_API.get_qr_code(Success)
    else:
        raise RuntimeError("Current WX_API object has no QR login method.")

    print("QR login started.")
    print(json.dumps(qr_result or {}, ensure_ascii=False, indent=2))

    qr_path = _resolve_qr_path_from_result(qr_result or {})
    print(f"QR image path: {qr_path}")
    qr_ready = _wait_qr_file_ready(qr_path, timeout=args.qr_file_timeout)
    if not qr_ready:
        print(f"[warn] QR image file not ready within {args.qr_file_timeout}s: {qr_path}")
    else:
        if args.qr_display in {"terminal", "both"}:
            try:
                _print_qr_terminal(qr_path)
            except Exception as exc:
                print(f"[warn] terminal QR render failed: {exc}")
        if args.qr_display in {"open", "both"}:
            try:
                _open_qr_image(qr_path)
                print("Opened QR image in system viewer.")
            except Exception as exc:
                print(f"[warn] open QR image failed: {exc}")

    if not args.wait:
        return

    end = time.time() + args.timeout
    print("Waiting for scan/login ...")
    while time.time() < end:
        status_data = cmd_status(return_only=True)
        login_ok = bool(status_data.get("login_status", False))
        qr_exists = bool(status_data.get("qr_code", False))
        print(f"status: login={login_ok}, qr_exists={qr_exists}")
        if login_ok:
            print("Login status is true. Waiting token/session to be persisted ...")
            token, _cookie = _wait_token_ready(timeout=args.token_wait_timeout, interval=1.0)
            print("Login success.")
            print(f"Token exists: {bool(token)}")
            joined = _join_wx_login_thread(timeout=args.thread_join_timeout)
            if not joined:
                print(
                    f"[warn] login worker thread still running after {args.thread_join_timeout}s. "
                    "You may see shutdown noise; wait a moment before next command."
                )
            return
        time.sleep(3)

    raise RuntimeError("Login timeout. Please retry.")


def cmd_status(return_only: bool = False) -> Dict[str, Any]:
    data: Dict[str, Any] = {"login_status": False, "qr_code": False}
    try:
        _load_wx_runtime()
        if hasattr(WX_API, "QrStatus"):
            data = WX_API.QrStatus() or data
        elif hasattr(WX_API, "HasLogin"):
            data = {"login_status": bool(WX_API.HasLogin()), "qr_code": False}
    except Exception as exc:
        data["wx_runtime_error"] = str(exc)

    try:
        token, _cookie = _get_token_cookie()
        data["token_exists"] = bool(token)
    except Exception as exc:
        data["token_runtime_error"] = str(exc)
        data["token_exists"] = False

    if not return_only:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def cmd_search_mp(args: argparse.Namespace) -> None:
    rows = _search_mp(args.keyword, args.limit, args.offset)
    if args.raw:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    norm = [_normalize_mp(row) for row in rows]
    printable = [mp.__dict__ for mp in norm]
    _print_mps(printable)


def cmd_add_mp(args: argparse.Namespace) -> None:
    state = _load_state()

    if args.keyword:
        rows = _search_mp(args.keyword, args.limit, args.offset)
        if not rows:
            raise RuntimeError("No mp found with this keyword.")
        idx = args.pick - 1
        if idx < 0 or idx >= len(rows):
            raise RuntimeError(f"pick out of range: 1..{len(rows)}")
        picked = _normalize_mp(rows[idx])
    else:
        if not args.name or not args.fakeid:
            raise RuntimeError("manual add requires --name and --fakeid")
        picked = MpRecord(
            id=_safe_decode_fakeid(args.fakeid),
            name=args.name,
            fakeid=args.fakeid,
            alias=args.alias or "",
            avatar=args.avatar or "",
            intro=args.intro or "",
        )

    exists = _find_mp(state, picked.id)
    payload = picked.__dict__.copy()
    payload["added_at"] = _now_ts()

    if exists:
        exists.update(payload)
        action = "updated"
    else:
        state.setdefault("mps", []).append(payload)
        action = "added"

    _save_state(state)
    print(f"MP {action}: {picked.id} | {picked.name}")


def cmd_list_mp(_args: argparse.Namespace) -> None:
    state = _load_state()
    _print_mps(state.get("mps", []))


def cmd_pull_articles(args: argparse.Namespace) -> None:
    state = _load_state()

    fakeid = ""
    mp_id = args.mp_id or ""
    if mp_id:
        mp = _find_mp(state, mp_id)
        if not mp:
            inferred_fakeid = _encode_fakeid_from_mp_id(mp_id)
            if not inferred_fakeid:
                raise RuntimeError(f"mp not found in state and cannot infer fakeid: {mp_id}")
            fakeid = inferred_fakeid
            print(f"[warn] mp not found in state: {mp_id}")
            print(f"[info] inferred fakeid from mp-id: {fakeid}")
        else:
            fakeid = str(mp.get("fakeid") or "").strip()
    else:
        fakeid = str(args.fakeid or "").strip()
        mp_id = _safe_decode_fakeid(fakeid)

    if not fakeid:
        raise RuntimeError("Missing fakeid. Use --mp-id or --fakeid.")

    mode = args.mode.lower().strip()
    if mode == "api":
        articles = _fetch_articles_api(fakeid=fakeid, pages=args.pages, with_content=args.with_content)
    elif mode in {"web", "app"}:
        articles = _fetch_articles_web(fakeid=fakeid, pages=args.pages, with_content=args.with_content)
    else:
        raise RuntimeError("mode must be one of: api, web, app")

    for article in articles:
        article["mp_id"] = mp_id
        article["fetched_at"] = _now_ts()

    state.setdefault("articles", {})
    state["articles"][mp_id] = articles
    _save_state(state)

    print(f"Fetched {len(articles)} articles for {mp_id} (mode={mode}).")
    _print_articles(articles, limit=args.show)


def cmd_list_articles(args: argparse.Namespace) -> None:
    state = _load_state()
    article_map = state.get("articles", {})

    if args.mp_id:
        items = list(article_map.get(args.mp_id, []))
    else:
        items = []
        for values in article_map.values():
            items.extend(values)
        items.sort(key=lambda x: int(x.get("publish_time") or 0), reverse=True)

    _print_articles(items, limit=args.show)


def _find_article_url(state: Dict[str, Any], article_id: str, mp_id: str = "") -> str:
    article_map = state.get("articles", {})
    if mp_id:
        for item in article_map.get(mp_id, []):
            if str(item.get("id")) == article_id:
                return str(item.get("url") or "").strip()
        return ""

    for values in article_map.values():
        for item in values:
            if str(item.get("id")) == article_id:
                return str(item.get("url") or "").strip()
    return ""


def _safe_filename(text: str, max_len: int = 80) -> str:
    value = re.sub(r"[\\/:*?\"<>|\s]+", "_", str(text or "").strip())
    value = value.strip("._")
    if not value:
        value = "article"
    return value[:max_len]


def _iter_articles_for_batch(state: Dict[str, Any], mp_id: str = "") -> List[Dict[str, Any]]:
    article_map = state.get("articles", {})
    if mp_id:
        return list(article_map.get(mp_id, []))

    merged: List[Dict[str, Any]] = []
    for _k, values in article_map.items():
        merged.extend(values)
    merged.sort(key=lambda x: int(x.get("publish_time") or 0), reverse=True)
    return merged


def cmd_fetch_content(args: argparse.Namespace) -> None:
    _load_fetcher_runtime()
    state = _load_state()

    url = str(args.url or "").strip()
    if not url:
        if not args.article_id:
            raise RuntimeError("Need --url or --article-id")
        url = _find_article_url(state, args.article_id, args.mp_id or "")
        if not url:
            raise RuntimeError("Cannot find article url in local state.")

    fetcher = WXArticleFetcher()
    try:
        info = fetcher.get_article_content(url)
    finally:
        try:
            fetcher.Close()
        except Exception:
            pass

    print(json.dumps({
        "id": info.get("id"),
        "title": info.get("title"),
        "author": info.get("author"),
        "publish_time": info.get("publish_time"),
        "description": info.get("description"),
        "topic_image": info.get("topic_image"),
        "fetch_error": info.get("fetch_error"),
        "content_len": len(str(info.get("content") or "")),
    }, ensure_ascii=False, indent=2))

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(str(info.get("content") or ""), encoding="utf-8")
        print(f"content saved: {out_path}")


def cmd_batch_fetch_content(args: argparse.Namespace) -> None:
    _load_fetcher_runtime()
    state = _load_state()
    items = _iter_articles_for_batch(state, args.mp_id or "")
    if not items:
        raise RuntimeError("No articles in local state. Run pull-articles first.")

    if args.limit > 0:
        items = items[: args.limit]

    target_name = args.mp_id if args.mp_id else "all_mps"
    output_dir = Path(args.output_dir or (STATE_DIR / "contents" / target_name)).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    fetcher = WXArticleFetcher()
    ok_count = 0
    fail_count = 0
    skip_count = 0
    results: List[Dict[str, Any]] = []

    try:
        total = len(items)
        for idx, item in enumerate(items, start=1):
            article_id = str(item.get("id") or "").strip()
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not url:
                fail_count += 1
                results.append(
                    {
                        "ok": False,
                        "article_id": article_id,
                        "title": title,
                        "url": "",
                        "error": "missing url",
                    }
                )
                if not args.continue_on_error:
                    break
                continue

            slug = _safe_filename(f"{idx:04d}_{article_id}_{title}")
            output_path = output_dir / f"{slug}.html"

            if args.skip_existing and output_path.exists():
                skip_count += 1
                results.append(
                    {
                        "ok": True,
                        "article_id": article_id,
                        "title": title,
                        "url": url,
                        "output": str(output_path),
                        "skipped": True,
                    }
                )
                print(f"[{idx}/{total}] skip existing: {article_id} | {title}")
                continue

            print(f"[{idx}/{total}] fetch content: {article_id} | {title}")
            try:
                info = fetcher.get_article_content(url)
                content = str(info.get("content") or "")
                output_path.write_text(content, encoding="utf-8")
                ok_count += 1

                cache_meta = {
                    "output": str(output_path),
                    "saved_at": _now_ts(),
                    "content_len": len(content),
                    "author": info.get("author") or "",
                    "fetch_error": info.get("fetch_error") or "",
                }
                item["content_cache"] = cache_meta
                results.append(
                    {
                        "ok": True,
                        "article_id": article_id,
                        "title": title,
                        "url": url,
                        "output": str(output_path),
                        "content_len": len(content),
                        "author": info.get("author") or "",
                        "fetch_error": info.get("fetch_error") or "",
                    }
                )
            except Exception as exc:
                fail_count += 1
                item["content_cache"] = {
                    "output": str(output_path),
                    "saved_at": _now_ts(),
                    "content_len": 0,
                    "author": "",
                    "fetch_error": str(exc),
                }
                results.append(
                    {
                        "ok": False,
                        "article_id": article_id,
                        "title": title,
                        "url": url,
                        "error": str(exc),
                    }
                )
                print(f"[warn] fetch failed: {article_id} | {exc}")
                if not args.continue_on_error:
                    break
            time.sleep(max(0.0, args.sleep))
    finally:
        try:
            fetcher.Close()
        except Exception:
            pass

    _save_state(state)

    summary = {
        "mp_id": args.mp_id or "",
        "total_selected": len(items),
        "ok": ok_count,
        "failed": fail_count,
        "skipped": skip_count,
        "output_dir": str(output_dir),
        "generated_at": _now_ts(),
        "results": results,
    }
    summary_path = output_dir / "_batch_result.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"Batch finished: total={len(items)}, ok={ok_count}, failed={fail_count}, "
        f"skipped={skip_count}, output_dir={output_dir}"
    )
    print(f"summary saved: {summary_path}")


def cmd_switch_account(args: argparse.Namespace) -> None:
    _load_wx_runtime()
    if not hasattr(WX_API, "switch_account"):
        raise RuntimeError("Current WX_API object does not support switch_account.")

    result = WX_API.switch_account(args.username or "")
    if result is None:
        print("Switch account triggered. Check terminal/browser logs for result.")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wechat-demo",
        description="Independent CLI demo for QR login, mp management, article list, content fetch, batch content fetch, account switch.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_login = sub.add_parser("login", help="Start QR login")
    p_login.add_argument("--wait", dest="wait", action="store_true", help="Wait until login success")
    p_login.add_argument("--no-wait", dest="wait", action="store_false", help="Return immediately after QR generated")
    p_login.set_defaults(wait=True)
    p_login.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Wait timeout seconds")
    p_login.add_argument(
        "--qr-display",
        type=str,
        choices=["none", "terminal", "open", "both"],
        default="both",
        help="How to display QR image after generation",
    )
    p_login.add_argument(
        "--qr-file-timeout",
        type=int,
        default=15,
        help="Seconds to wait for QR image file ready",
    )
    p_login.add_argument(
        "--token-wait-timeout",
        type=int,
        default=30,
        help="Seconds to wait for token after login status turns true",
    )
    p_login.add_argument(
        "--thread-join-timeout",
        type=int,
        default=12,
        help="Seconds to wait for login background thread to finish before exit",
    )
    p_login.set_defaults(func=cmd_login)

    p_status = sub.add_parser("status", help="Show login status")
    p_status.set_defaults(func=lambda _args: cmd_status(return_only=False))

    p_search = sub.add_parser("search-mp", help="Search mp by keyword")
    p_search.add_argument("keyword", type=str)
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--offset", type=int, default=0)
    p_search.add_argument("--raw", action="store_true", help="Print raw json")
    p_search.set_defaults(func=cmd_search_mp)

    p_add = sub.add_parser("add-mp", help="Add mp to local demo state")
    p_add.add_argument("--keyword", type=str, default="", help="Search keyword then pick one")
    p_add.add_argument("--pick", type=int, default=1, help="Pick index from search result (1-based)")
    p_add.add_argument("--limit", type=int, default=10)
    p_add.add_argument("--offset", type=int, default=0)
    p_add.add_argument("--name", type=str, default="", help="Manual add: mp name")
    p_add.add_argument("--fakeid", type=str, default="", help="Manual add: fakeid")
    p_add.add_argument("--alias", type=str, default="")
    p_add.add_argument("--avatar", type=str, default="")
    p_add.add_argument("--intro", type=str, default="")
    p_add.set_defaults(func=cmd_add_mp)

    p_list_mp = sub.add_parser("list-mp", help="List local mp records")
    p_list_mp.set_defaults(func=cmd_list_mp)

    p_pull = sub.add_parser("pull-articles", help="Fetch article list by mp")
    p_pull.add_argument("--mp-id", type=str, default="", help="mp id in local state")
    p_pull.add_argument("--fakeid", type=str, default="", help="direct fakeid when mp not in state")
    p_pull.add_argument("--pages", type=int, default=1)
    p_pull.add_argument("--mode", type=str, default="api", choices=["api", "web", "app"])
    p_pull.add_argument("--with-content", action="store_true", help="Also fetch article content")
    p_pull.add_argument("--show", type=int, default=20, help="How many rows to print")
    p_pull.set_defaults(func=cmd_pull_articles)

    p_list_articles = sub.add_parser("list-articles", help="List fetched articles in local state")
    p_list_articles.add_argument("--mp-id", type=str, default="")
    p_list_articles.add_argument("--show", type=int, default=20)
    p_list_articles.set_defaults(func=cmd_list_articles)

    p_fetch = sub.add_parser("fetch-content", help="Fetch article content by url or article-id")
    p_fetch.add_argument("--url", type=str, default="")
    p_fetch.add_argument("--article-id", type=str, default="")
    p_fetch.add_argument("--mp-id", type=str, default="")
    p_fetch.add_argument("--output", type=str, default="", help="Save html content to file")
    p_fetch.set_defaults(func=cmd_fetch_content)

    p_batch_fetch = sub.add_parser(
        "batch-fetch-content",
        help="Batch fetch article content from local article list and save html files",
    )
    p_batch_fetch.add_argument("--mp-id", type=str, default="", help="Only fetch this mp-id from local state")
    p_batch_fetch.add_argument("--limit", type=int, default=0, help="Max number of articles to fetch, 0 means all")
    p_batch_fetch.add_argument(
        "--output-dir",
        type=str,
        default="",
        help="Directory for html files and summary json (default: demo_cli/data/contents/<mp-id|all_mps>)",
    )
    p_batch_fetch.add_argument("--skip-existing", action="store_true", help="Skip html file if already exists")
    p_batch_fetch.add_argument(
        "--continue-on-error",
        dest="continue_on_error",
        action="store_true",
        help="Continue batch even if one article fails",
    )
    p_batch_fetch.add_argument(
        "--stop-on-error",
        dest="continue_on_error",
        action="store_false",
        help="Stop immediately on first failed article",
    )
    p_batch_fetch.set_defaults(continue_on_error=True)
    p_batch_fetch.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between each fetch")
    p_batch_fetch.set_defaults(func=cmd_batch_fetch_content)

    p_switch = sub.add_parser("switch-account", help="Switch wx account")
    p_switch.add_argument("--username", type=str, default="", help="target account username (optional)")
    p_switch.set_defaults(func=cmd_switch_account)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"[error] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
