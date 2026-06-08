"""
图片素材相关 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance

bp = Blueprint("images", __name__, url_prefix="/api")

@bp.route("/image-assets", methods=["GET"])
def list_image_assets():
    account_id = request.args.get("account_id")
    assets = get_manager_instance().list_image_assets(account_id=account_id)
    return jsonify([asset.model_dump() for asset in assets])

@bp.route("/image-assets/upload", methods=["POST"])
def upload_image_asset():
    try:
        image_file = request.files.get("file")
        account_id = request.form.get("account_id", "")
        title = request.form.get("title", "")
        asset = get_manager_instance().upload_image_asset(image_file, account_id=account_id, title=title)
        return jsonify(asset.model_dump()), 201
    except Exception as e:
        return api_error(str(e), "UPLOAD_FAILED", 400)

@bp.route("/image-assets/generate", methods=["POST"])
def generate_image_asset():
    data = request.json or {}
    try:
        asset = get_manager_instance().generate_image_asset(
            prompt=data.get("prompt", ""),
            account_id=data.get("account_id", ""),
            title=data.get("title", ""),
            size=data.get("size", ""),
        )
        return jsonify(asset.model_dump()), 201
    except Exception as e:
        return api_error(str(e), "GENERATE_FAILED", 400)

@bp.route("/image-assets/<asset_id>", methods=["DELETE"])
def delete_image_asset(asset_id):
    success = get_manager_instance().delete_image_asset(asset_id)
    if not success:
        return api_error("Image asset not found", "NOT_FOUND", 404)
    return jsonify({"success": True})
