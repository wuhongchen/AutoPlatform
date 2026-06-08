"""
链接成稿（ContentFlow）相关 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance

bp = Blueprint("content_flow", __name__, url_prefix="/api")

@bp.route("/content-flow/run", methods=["POST"])
def run_content_flow():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return api_error("链接不能为空", "MISSING_FIELD", 400)
    try:
        task = get_manager_instance().create_task(
            name="content_flow",
            payload={
                "url": url,
                "style": data.get("style"),
                "template": data.get("template", "default"),
                "use_references": data.get("use_references", True),
                "custom_instructions": data.get("instructions") or data.get("custom_instructions"),
                "inspiration_ids": data.get("inspiration_ids"),
            },
            account_id=data.get("account_id", "default"),
            target_id=url,
        )
        return jsonify({
            "task_id": task.id,
            "status": task.status.value,
            "message": "链接成稿任务已创建",
        }), 202
    except Exception as e:
        return api_error(str(e), "TASK_CREATE_FAILED", 400)
