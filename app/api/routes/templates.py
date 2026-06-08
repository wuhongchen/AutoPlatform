"""
模板相关 API
"""
from flask import Blueprint, jsonify, request
from app.api.routes import api_error, get_manager_instance

bp = Blueprint("templates", __name__, url_prefix="/api")

@bp.route("/templates", methods=["GET"])
def list_templates():
    templates = get_manager_instance().get_templates()
    return jsonify({
        name: {"name": config.name, "description": config.description, "version": config.version}
        for name, config in templates.items()
    })

@bp.route("/templates/<template_name>/preview", methods=["POST"])
def preview_template(template_name):
    from app.templates import TemplateRegistry
    data = request.json or {}
    template = TemplateRegistry.create_instance(template_name)
    if not template:
        return api_error("Template not found", "NOT_FOUND", 404)
    html = template.render(
        title=data.get("title", "示例标题"),
        content=data.get("content", "<p>这是一段示例内容</p>"),
        author=data.get("author", "作者"),
        cover_image=data.get("cover_image", ""),
        ad_header_html=data.get("ad_header_html", ""),
        ad_footer_html=data.get("ad_footer_html", ""),
    )
    return jsonify({"html": html})
