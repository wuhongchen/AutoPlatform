"""
账户相关 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance

bp = Blueprint("accounts", __name__, url_prefix="/api")


@bp.route("/accounts", methods=["GET"])
def list_accounts():
    accounts = get_manager_instance().list_accounts()
    return jsonify([a.model_dump() for a in accounts])


@bp.route("/accounts", methods=["POST"])
def create_account():
    data = request.json or {}
    try:
        account = get_manager_instance().create_account(
            name=data["name"],
            account_id=data["account_id"],
            wechat_appid=data.get("wechat_appid", ""),
            wechat_secret=data.get("wechat_secret", ""),
            wechat_author=data.get("wechat_author", ""),
            ad_header_html=data.get("ad_header_html", ""),
            ad_footer_html=data.get("ad_footer_html", ""),
            pipeline_role=data.get("pipeline_role", "tech_expert"),
            pipeline_batch_size=data.get("pipeline_batch_size", 3),
            content_direction=data.get("content_direction", ""),
            prompt_direction=data.get("prompt_direction", ""),
            wechat_prompt_direction=data.get("wechat_prompt_direction", ""),
        )
        return jsonify(account.model_dump()), 200
    except KeyError as e:
        return api_error(f"缺少必填字段: {e}", "MISSING_FIELD", 400)
    except Exception as e:
        return api_error(str(e), "CREATE_FAILED", 400)


@bp.route("/accounts/<account_id>", methods=["GET"])
def get_account(account_id):
    account = get_manager_instance().get_account(account_id)
    if not account:
        return api_error("Account not found", "NOT_FOUND", 404)
    return jsonify(account.model_dump())


@bp.route("/accounts/<account_id>", methods=["PUT"])
def update_account(account_id):
    data = request.json or {}
    manager = get_manager_instance()
    success = manager.storage.update_account(account_id, data)
    if not success:
        return api_error("Update failed or account not found", "UPDATE_FAILED", 400)
    account = manager.get_account(account_id)
    return jsonify(account.model_dump() if account else {"success": True})


@bp.route("/accounts/<account_id>", methods=["DELETE"])
def delete_account(account_id):
    success = get_manager_instance().storage.delete_account(account_id)
    if not success:
        return api_error("Delete failed or account not found", "DELETE_FAILED", 400)
    return jsonify({"success": True})


@bp.route("/accounts/<account_id>/stats", methods=["GET"])
def get_account_stats(account_id):
    stats = get_manager_instance().get_stats(account_id)
    return jsonify(stats)


@bp.route("/stats", methods=["GET"])
def get_global_stats():
    account_id = request.args.get("account_id")
    stats = get_manager_instance().get_stats(account_id if account_id else None)
    return jsonify(stats)
