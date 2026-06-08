#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin_accounts import AccountStore
from modules.wechat_ingest_service import WechatIngestService


def _safe_text(value) -> str:
    return str(value or "").strip()


def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _pick_account(store: AccountStore, account_id: str):
    aid = _safe_text(account_id)
    if aid:
        item = store.get(aid)
        if item:
            return item
    return store.get_active()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wechat-ingest",
        description="Multi-account WeChat ingest CLI for login, follow list, article list and inspiration sync.",
    )
    parser.add_argument("--account-id", default="", help="Target account id, default active account")
    parser.add_argument("--python-bin", default=os.getenv("OPENCLAW_WECHAT_DEMO_PYTHON", "python3"))

    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Show login/runtime status")
    p_status.set_defaults(func=cmd_status)

    p_login = sub.add_parser("login", help="Run QR login")
    p_login.add_argument("--wait", dest="wait", action="store_true", help="Wait until login success")
    p_login.add_argument("--no-wait", dest="wait", action="store_false", help="Only generate QR and return")
    p_login.set_defaults(wait=True)
    p_login.add_argument("--qr-display", default="none", choices=["none", "terminal", "open", "both"])
    p_login.add_argument("--timeout", type=int, default=40)
    p_login.add_argument("--token-wait-timeout", type=int, default=60)
    p_login.add_argument("--thread-join-timeout", type=int, default=20)
    p_login.set_defaults(func=cmd_login)

    p_search = sub.add_parser("search-mp", help="Search mp account by keyword")
    p_search.add_argument("keyword")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--offset", type=int, default=0)
    p_search.set_defaults(func=cmd_search_mp)

    p_add = sub.add_parser("add-mp", help="Add mp account by search keyword")
    p_add.add_argument("--keyword", required=True)
    p_add.add_argument("--pick", type=int, default=1)
    p_add.add_argument("--limit", type=int, default=10)
    p_add.add_argument("--offset", type=int, default=0)
    p_add.set_defaults(func=cmd_add_mp)

    p_list_mp = sub.add_parser("list-mp", help="List followed mp accounts in account workspace")
    p_list_mp.set_defaults(func=cmd_list_mp)

    p_pull = sub.add_parser("pull-articles", help="Pull article list for one mp")
    p_pull.add_argument("--mp-id", required=True)
    p_pull.add_argument("--pages", type=int, default=1)
    p_pull.add_argument("--mode", default="api", choices=["api", "web", "app"])
    p_pull.add_argument("--with-content", action="store_true")
    p_pull.set_defaults(func=cmd_pull_articles)

    p_list_art = sub.add_parser("list-articles", help="List cached articles")
    p_list_art.add_argument("--mp-id", default="")
    p_list_art.add_argument("--limit", type=int, default=50)
    p_list_art.set_defaults(func=cmd_list_articles)

    p_sync = sub.add_parser("sync-inspiration", help="Sync cached articles into inspiration table")
    p_sync.add_argument("--mp-id", default="")
    p_sync.add_argument("--limit", type=int, default=20)
    p_sync.set_defaults(func=cmd_sync_inspiration)

    p_full = sub.add_parser("full-flow", help="Run full flow: add/search mp -> pull articles -> sync inspiration")
    p_full.add_argument("--mp-id", default="")
    p_full.add_argument("--keyword", default="")
    p_full.add_argument("--pick", type=int, default=1)
    p_full.add_argument("--pages", type=int, default=1)
    p_full.add_argument("--mode", default="api", choices=["api", "web", "app"])
    p_full.add_argument("--with-content", action="store_true")
    p_full.add_argument("--content-limit", type=int, default=10)
    p_full.add_argument("--sync-limit", type=int, default=20)
    p_full.set_defaults(func=cmd_full_flow)

    return parser


def _service_from_args(args) -> WechatIngestService:
    store = AccountStore()
    account = _pick_account(store, args.account_id)
    return WechatIngestService(account=account, python_bin=args.python_bin, project_root=str(PROJECT_ROOT))


def cmd_status(args):
    svc = _service_from_args(args)
    _print_json(svc.status())


def cmd_login(args):
    if sys.stdout.isatty():
        print("正在触发微信登录流程（首次可能等待 10-60 秒）...", flush=True)
    svc = _service_from_args(args)
    result = svc.login(
        wait=bool(args.wait),
        qr_display=_safe_text(args.qr_display) or "none",
        timeout=args.timeout,
        token_wait_timeout=args.token_wait_timeout,
        thread_join_timeout=args.thread_join_timeout,
    )
    _print_json(result)


def cmd_search_mp(args):
    svc = _service_from_args(args)
    _print_json(svc.search_mp(args.keyword, limit=args.limit, offset=args.offset))


def cmd_add_mp(args):
    svc = _service_from_args(args)
    _print_json(svc.add_mp(keyword=args.keyword, pick=args.pick, limit=args.limit, offset=args.offset))


def cmd_list_mp(args):
    svc = _service_from_args(args)
    _print_json(svc.list_mps())


def cmd_pull_articles(args):
    svc = _service_from_args(args)
    _print_json(svc.pull_articles(mp_id=args.mp_id, pages=args.pages, mode=args.mode, with_content=bool(args.with_content)))


def cmd_list_articles(args):
    svc = _service_from_args(args)
    _print_json(svc.list_articles(mp_id=args.mp_id, limit=args.limit))


def cmd_sync_inspiration(args):
    svc = _service_from_args(args)
    _print_json(svc.sync_articles_to_inspiration(mp_id=args.mp_id, limit=args.limit))


def cmd_full_flow(args):
    svc = _service_from_args(args)
    _print_json(
        svc.full_flow(
            mp_id=args.mp_id,
            keyword=args.keyword,
            pick=args.pick,
            pages=args.pages,
            mode=args.mode,
            with_content=bool(args.with_content),
            content_limit=args.content_limit,
            sync_limit=args.sync_limit,
        )
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        _print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
