"""
公众号雷达/采集相关 API
"""
from flask import Blueprint, jsonify, request, send_file
from app.api.routes import api_error, get_manager_instance
import os

bp = Blueprint("wechat", __name__, url_prefix="/api")

@bp.route("/wechat-ingest/status", methods=["GET"])
def wechat_ingest_status():
    account_id = request.args.get("account_id", "")
    try:
        return jsonify(get_manager_instance().wechat_ingest_status(account_id))
    except Exception as e:
        return api_error(str(e), "QUERY_FAILED", 400)

@bp.route("/wechat-ingest/qr-image", methods=["GET"])
def wechat_ingest_qr_image():
    account_id = request.args.get("account_id", "")
    try:
        status = get_manager_instance().wechat_ingest_status(account_id)
        qr_path = status.get("state", {}).get("qr_image_path") or status.get("qr_image_path") or ""
        if not qr_path or not os.path.isfile(qr_path):
            return api_error("QR image not found", "NOT_FOUND", 404)
        return send_file(qr_path, mimetype="image/png")
    except Exception as e:
        return api_error(str(e), "QUERY_FAILED", 400)

@bp.route("/wechat-ingest/mps", methods=["GET"])
def wechat_ingest_list_mps():
    account_id = request.args.get("account_id", "")
    try:
        return jsonify(get_manager_instance().wechat_ingest_list_mps(account_id))
    except Exception as e:
        return api_error(str(e), "QUERY_FAILED", 400)

@bp.route("/wechat-ingest/articles", methods=["GET"])
def wechat_ingest_list_articles():
    account_id = request.args.get("account_id", "")
    mp_id = request.args.get("mp_id", "")
    limit = request.args.get("limit", 50, type=int)
    try:
        return jsonify(get_manager_instance().wechat_ingest_list_articles(account_id, mp_id=mp_id, limit=limit))
    except Exception as e:
        return api_error(str(e), "QUERY_FAILED", 400)

@bp.route("/wechat-ingest/article-preview", methods=["GET"])
def wechat_ingest_article_preview():
    account_id = request.args.get("account_id", "")
    mp_id = request.args.get("mp_id", "")
    article_id = request.args.get("article_id", "")
    try:
        return jsonify(get_manager_instance().wechat_ingest_article_preview(account_id, mp_id=mp_id, article_id=article_id))
    except Exception as e:
        return api_error(str(e), "QUERY_FAILED", 400)

@bp.route("/wechat-ingest/login", methods=["POST"])
def wechat_ingest_login():
    data = request.json or {}
    try:
        return jsonify(get_manager_instance().wechat_ingest_login(
            data.get("account_id", ""),
            wait=bool(data.get("wait", False)),
            qr_display=data.get("qr_display", "none"),
            timeout=int(data.get("timeout", 60)),
            token_wait_timeout=int(data.get("token_wait_timeout", 20)),
            thread_join_timeout=int(data.get("thread_join_timeout", 8)),
        ))
    except Exception as e:
        return api_error(str(e), "LOGIN_FAILED", 400)

@bp.route("/wechat-ingest/search-mp", methods=["POST"])
def wechat_ingest_search_mp():
    data = request.json or {}
    try:
        return jsonify(get_manager_instance().wechat_ingest_search_mp(
            data.get("account_id", ""), keyword=data.get("keyword", ""),
            limit=int(data.get("limit", 10)), offset=int(data.get("offset", 0)),
        ))
    except Exception as e:
        return api_error(str(e), "SEARCH_FAILED", 400)

@bp.route("/wechat-ingest/add-mp", methods=["POST"])
def wechat_ingest_add_mp():
    data = request.json or {}
    try:
        return jsonify(get_manager_instance().wechat_ingest_add_mp(
            data.get("account_id", ""), keyword=data.get("keyword", ""),
            pick=int(data.get("pick", 1)), limit=int(data.get("limit", 10)),
            offset=int(data.get("offset", 0)),
        ))
    except Exception as e:
        return api_error(str(e), "ADD_FAILED", 400)

@bp.route("/wechat-ingest/pull-articles", methods=["POST"])
def wechat_ingest_pull_articles():
    data = request.json or {}
    try:
        return jsonify(get_manager_instance().wechat_ingest_pull_articles(
            data.get("account_id", ""), mp_id=data.get("mp_id", ""),
            pages=int(data.get("pages", 1)), mode=data.get("mode", "api"),
            with_content=bool(data.get("with_content", False)),
        ))
    except Exception as e:
        return api_error(str(e), "PULL_FAILED", 400)

@bp.route("/wechat-ingest/sync-inspirations", methods=["POST"])
def wechat_ingest_sync_inspirations():
    data = request.json or {}
    try:
        return jsonify(get_manager_instance().wechat_ingest_sync_inspirations(
            data.get("account_id", ""), mp_id=data.get("mp_id", ""),
            limit=int(data.get("limit", 20)),
        ))
    except Exception as e:
        return api_error(str(e), "SYNC_FAILED", 400)

@bp.route("/wechat-ingest/full-flow", methods=["POST"])
def wechat_ingest_full_flow():
    data = request.json or {}
    try:
        return jsonify(get_manager_instance().wechat_ingest_full_flow(
            data.get("account_id", ""), mp_id=data.get("mp_id", ""),
            keyword=data.get("keyword", ""), pick=int(data.get("pick", 1)),
            pages=int(data.get("pages", 1)), mode=data.get("mode", "api"),
            with_content=bool(data.get("with_content", False)),
            content_limit=int(data.get("content_limit", 10)),
            sync_limit=int(data.get("sync_limit", 20)),
        ))
    except Exception as e:
        return api_error(str(e), "FULL_FLOW_FAILED", 400)
