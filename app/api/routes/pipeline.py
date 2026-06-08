"""
批量处理流水线 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance

bp = Blueprint("pipeline", __name__, url_prefix="/api")

@bp.route("/pipeline/process", methods=["POST"])
def process_pipeline():
    data = request.json or {}
    try:
        task = get_manager_instance().create_task(
            name="batch",
            payload={
                "batch_size": data.get("batch_size", 3),
                "style": data.get("style"),
                "template": data.get("template", "default"),
            },
            account_id=data.get("account_id", "default"),
        )
        return jsonify({
            "task_id": task.id,
            "status": task.status.value,
            "message": "批量处理任务已创建",
        }), 202
    except Exception as e:
        return api_error(str(e), "TASK_CREATE_FAILED", 400)
