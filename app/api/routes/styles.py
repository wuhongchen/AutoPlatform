"""
改写风格相关 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance

bp = Blueprint("styles", __name__, url_prefix="/api")

@bp.route("/styles", methods=["GET"])
def list_styles():
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    presets = get_manager_instance().storage.list_style_presets(include_inactive=include_inactive)
    return jsonify([p.model_dump() for p in presets])

@bp.route("/styles", methods=["POST"])
def create_style():
    data = request.json or {}
    try:
        preset = get_manager_instance().create_style_preset(data)
        return jsonify(preset.model_dump()), 201
    except Exception as e:
        return api_error(str(e), "CREATE_FAILED", 400)

@bp.route("/styles/<preset_id>", methods=["GET"])
def get_style(preset_id):
    preset = get_manager_instance().get_style_preset(preset_id)
    if not preset:
        return api_error("Style preset not found", "NOT_FOUND", 404)
    return jsonify(preset.model_dump())

@bp.route("/styles/<preset_id>", methods=["PUT"])
def update_style(preset_id):
    data = request.json or {}
    success = get_manager_instance().update_style_preset(preset_id, data)
    if not success:
        return api_error("Update failed or preset is built-in", "UPDATE_FAILED", 400)
    return jsonify({"success": True})

@bp.route("/styles/<preset_id>", methods=["DELETE"])
def delete_style(preset_id):
    success = get_manager_instance().delete_style_preset(preset_id)
    if not success:
        return api_error("Delete failed or preset is built-in", "DELETE_FAILED", 400)
    return jsonify({"success": True})

@bp.route("/styles/<preset_id>/toggle", methods=["POST"])
def toggle_style(preset_id):
    success = get_manager_instance().toggle_style_preset(preset_id)
    if not success:
        return api_error("Toggle failed", "TOGGLE_FAILED", 400)
    return jsonify({"success": True})
