"""
文章相关 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance

bp = Blueprint("articles", __name__, url_prefix="/api")

@bp.route("/articles", methods=["GET"])
def list_articles():
    account_id = request.args.get("account_id")
    status = request.args.get("status")
    articles = get_manager_instance().storage.list_articles(account_id=account_id, status=status)
    return jsonify([a.model_dump() for a in articles])

@bp.route("/articles", methods=["POST"])
def create_article():
    data = request.json or {}
    try:
        article = get_manager_instance().create_manual_article(data)
        return jsonify(article.model_dump()), 201
    except Exception as e:
        return api_error(str(e), "CREATE_FAILED", 400)

@bp.route("/articles/<article_id>", methods=["GET"])
def get_article(article_id):
    article = get_manager_instance().storage.get_article(article_id)
    if not article:
        return api_error("Article not found", "NOT_FOUND", 404)
    return jsonify(article.model_dump())

@bp.route("/articles/<article_id>", methods=["PUT"])
def update_article(article_id):
    data = request.json or {}
    try:
        article = get_manager_instance().update_article_content(article_id, data)
        return jsonify(article.model_dump())
    except Exception as e:
        return api_error(str(e), "UPDATE_FAILED", 400)

@bp.route("/articles/<article_id>/rewrite", methods=["POST"])
def rewrite_article(article_id):
    data = request.json or {}
    try:
        task = get_manager_instance().create_task(
            name="rewrite",
            payload={
                "article_id": article_id,
                "style": data.get("style"),
                "use_references": data.get("use_references", True),
                "custom_instructions": data.get("instructions"),
                "inspiration_ids": data.get("inspiration_ids"),
            },
            target_id=article_id,
        )
        return jsonify({
            "task_id": task.id,
            "status": task.status.value,
            "message": "改写任务已创建",
        }), 202
    except Exception as e:
        return api_error(str(e), "TASK_CREATE_FAILED", 400)

@bp.route("/articles/<article_id>/publish", methods=["POST"])
def publish_article(article_id):
    data = request.json or {}
    try:
        task = get_manager_instance().create_task(
            name="publish",
            payload={
                "article_id": article_id,
                "template": data.get("template", "default"),
            },
            target_id=article_id,
        )
        return jsonify({
            "task_id": task.id,
            "status": task.status.value,
            "message": "发布任务已创建",
        }), 202
    except Exception as e:
        return api_error(str(e), "TASK_CREATE_FAILED", 400)

@bp.route("/articles/<article_id>/wechat-copy", methods=["GET", "POST"])
def get_article_wechat_copy(article_id):
    data = request.get_json(silent=True) or {}
    template = data.get("template") or request.args.get("template") or "default"
    full_html_raw = data.get("full_html")
    if full_html_raw is None:
        full_html_raw = request.args.get("full_html", "")
    full_html = str(full_html_raw).lower() in {"1", "true", "yes", "on"}
    try:
        result = get_manager_instance().render_article_for_wechat_copy(
            article_id, template=template, full_html=full_html,
        )
        return jsonify(result)
    except Exception as e:
        return api_error(str(e), "RENDER_FAILED", 400)
