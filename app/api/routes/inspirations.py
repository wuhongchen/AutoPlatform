"""
灵感库相关 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance

bp = Blueprint("inspirations", __name__, url_prefix="/api")

@bp.route("/inspirations", methods=["POST"])
def collect_inspiration():
    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return api_error("URL 不能为空", "MISSING_FIELD", 400)
    try:
        task = get_manager_instance().create_task(
            name="collect",
            payload={"url": url},
            account_id=data.get("account_id", "default"),
        )
        return jsonify({
            "task_id": task.id,
            "status": task.status.value,
            "message": "采集任务已创建",
        }), 202
    except Exception as e:
        return api_error(str(e), "TASK_CREATE_FAILED", 400)

@bp.route("/inspirations", methods=["GET"])
def list_inspirations():
    account_id = request.args.get("account_id")
    merge_wechat_cache = request.args.get("merge_wechat_cache", "").lower() in {"1", "true", "yes", "on"}
    manager = get_manager_instance()
    if account_id and merge_wechat_cache:
        manager.merge_wechat_cached_articles_into_inspirations(account_id=account_id)
    records = manager.storage.list_inspirations(account_id=account_id)
    return jsonify([r.model_dump() for r in records])

@bp.route("/inspirations/<record_id>", methods=["GET"])
def get_inspiration(record_id):
    record = get_manager_instance().storage.get_inspiration(record_id)
    if not record:
        return api_error("Inspiration not found", "NOT_FOUND", 404)
    return jsonify(record.model_dump())

@bp.route("/inspirations/<record_id>", methods=["DELETE"])
def delete_inspiration(record_id):
    success = get_manager_instance().storage.delete_inspiration(record_id)
    if not success:
        return api_error("Delete failed or inspiration not found", "DELETE_FAILED", 400)
    return jsonify({"success": True})

@bp.route("/inspirations/<record_id>/create-article", methods=["POST"])
@bp.route("/inspirations/<record_id>/approve", methods=["POST"])
def create_article_from_inspiration(record_id):
    try:
        article = get_manager_instance().create_article_from_inspiration(record_id)
        return jsonify(article.model_dump())
    except Exception as e:
        return api_error(str(e), "CREATE_FAILED", 400)
