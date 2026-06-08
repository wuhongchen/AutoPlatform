"""
任务相关 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance
from app.models import TaskStatus

bp = Blueprint("tasks", __name__, url_prefix="/api")

@bp.route("/tasks", methods=["POST"])
def create_task():
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return api_error("任务名称不能为空", "MISSING_FIELD", 400)
    try:
        task = get_manager_instance().create_task(
            name=name,
            payload=data.get("payload", {}),
            account_id=data.get("account_id", ""),
            target_id=data.get("target_id", ""),
        )
        return jsonify({"task_id": task.id, "status": task.status.value}), 202
    except Exception as e:
        return api_error(str(e), "TASK_CREATE_FAILED", 400)

@bp.route("/tasks", methods=["GET"])
def list_tasks():
    account_id = request.args.get("account_id")
    status = request.args.get("status")
    name = request.args.get("name")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    tasks = get_manager_instance().storage.list_tasks(
        account_id=account_id, status=status, name=name, limit=limit, offset=offset,
    )
    return jsonify([t.model_dump() for t in tasks])

@bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    task = get_manager_instance().storage.get_task(task_id)
    if not task:
        return api_error("Task not found", "NOT_FOUND", 404)
    return jsonify(task.model_dump())

@bp.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    storage = get_manager_instance().storage
    task = storage.get_task(task_id)
    if not task:
        return api_error("Task not found", "NOT_FOUND", 404)
    if task.status == TaskStatus.RUNNING:
        return api_error("Cannot delete a running task", "TASK_RUNNING", 400)
    success = storage.delete_task(task_id)
    return jsonify({"success": success})
