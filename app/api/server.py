"""
API服务
"""
from flask import Flask, jsonify, request, send_from_directory
from app.core import AppManager
from app.config import get_settings

import os

# 获取项目路径
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(app_dir)

# Vue 构建输出目录
vue_dist_dir = os.path.join(project_root, 'frontend', 'dist')

app = Flask(__name__, 
            static_folder=vue_dist_dir if os.path.exists(vue_dist_dir) else os.path.join(app_dir, 'static'),
            static_url_path='')

manager = AppManager()

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/accounts", methods=["GET"])
def list_accounts():
    accounts = manager.list_accounts()
    return jsonify([a.model_dump() for a in accounts])

@app.route("/api/accounts", methods=["POST"])
def create_account():
    data = request.json
    account = manager.create_account(
        name=data["name"],
        account_id=data["account_id"],
        wechat_appid=data.get("wechat_appid", ""),
        wechat_secret=data.get("wechat_secret", "")
    )
    return jsonify(account.model_dump())

@app.route("/api/accounts/<account_id>", methods=["GET"])
def get_account(account_id):
    account = manager.get_account(account_id)
    if not account:
        return jsonify({"error": "Not found"}), 404
    return jsonify(account.model_dump())

@app.route("/api/accounts/<account_id>/stats", methods=["GET"])
def get_stats(account_id):
    stats = manager.get_stats(account_id)
    return jsonify(stats)

@app.route("/api/inspirations", methods=["POST"])
def collect_inspiration():
    data = request.json
    import asyncio
    record = asyncio.run(manager.collect_inspiration(
        url=data["url"],
        account_id=data["account_id"]
    ))
    return jsonify(record.model_dump())

@app.route("/api/inspirations", methods=["GET"])
def list_inspirations():
    account_id = request.args.get("account_id")
    records = manager.storage.list_inspirations(account_id=account_id)
    return jsonify([r.model_dump() for r in records])

@app.route("/api/inspirations/<record_id>/approve", methods=["POST"])
def approve_inspiration(record_id):
    """采纳灵感并创建文章"""
    try:
        article = manager.approve_inspiration(record_id)
        return jsonify(article.model_dump())
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/articles", methods=["GET"])
def list_articles():
    account_id = request.args.get("account_id")
    articles = manager.storage.list_articles(account_id=account_id)
    return jsonify([a.model_dump() for a in articles])

@app.route("/api/articles/<article_id>", methods=["GET"])
def get_article(article_id):
    """获取单篇文章详情"""
    article = manager.storage.get_article(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404
    return jsonify(article.model_dump())

@app.route("/api/articles/<article_id>/rewrite", methods=["POST"])
def rewrite_article(article_id):
    import asyncio
    data = request.json or {}
    style = data.get("style")
    use_references = data.get("use_references", True)
    custom_instructions = data.get("instructions")
    inspiration_ids = data.get("inspiration_ids")  # 指定参考的灵感ID列表
    
    article = asyncio.run(manager.rewrite_article(
        article_id,
        style=style,
        use_references=use_references,
        custom_instructions=custom_instructions,
        inspiration_ids=inspiration_ids
    ))
    return jsonify(article.model_dump())

@app.route("/api/styles", methods=["GET"])
def list_styles():
    """获取改写风格预设列表"""
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    presets = manager.storage.list_style_presets(include_inactive=include_inactive)
    return jsonify([p.model_dump() for p in presets])

@app.route("/api/styles", methods=["POST"])
def create_style():
    """创建自定义风格预设"""
    data = request.json
    try:
        preset = manager.create_style_preset(data)
        return jsonify(preset.model_dump()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/styles/<preset_id>", methods=["GET"])
def get_style(preset_id):
    """获取单个风格预设详情"""
    preset = manager.get_style_preset(preset_id)
    if not preset:
        return jsonify({"error": "Style preset not found"}), 404
    return jsonify(preset.model_dump())

@app.route("/api/styles/<preset_id>", methods=["PUT"])
def update_style(preset_id):
    """更新风格预设"""
    data = request.json
    success = manager.update_style_preset(preset_id, data)
    if not success:
        return jsonify({"error": "Update failed or preset is built-in"}), 400
    return jsonify({"success": True})

@app.route("/api/styles/<preset_id>", methods=["DELETE"])
def delete_style(preset_id):
    """删除风格预设"""
    success = manager.delete_style_preset(preset_id)
    if not success:
        return jsonify({"error": "Delete failed or preset is built-in"}), 400
    return jsonify({"success": True})

@app.route("/api/styles/<preset_id>/toggle", methods=["POST"])
def toggle_style(preset_id):
    """启用/禁用风格预设"""
    success = manager.toggle_style_preset(preset_id)
    if not success:
        return jsonify({"error": "Toggle failed"}), 400
    return jsonify({"success": True})

@app.route("/api/articles/<article_id>/publish", methods=["POST"])
def publish_article(article_id):
    import asyncio
    data = request.json or {}
    template = data.get("template", "default")
    article = asyncio.run(manager.publish_article(article_id, template=template))
    return jsonify(article.model_dump())

@app.route("/api/templates", methods=["GET"])
def list_templates():
    """获取可用模板列表"""
    templates = manager.get_templates()
    return jsonify({
        name: {
            "name": config.name,
            "description": config.description,
            "version": config.version
        }
        for name, config in templates.items()
    })

@app.route("/api/templates/<template_name>/preview", methods=["POST"])
def preview_template(template_name):
    """预览模板效果"""
    from app.templates import TemplateRegistry
    
    data = request.json or {}
    title = data.get("title", "示例标题")
    content = data.get("content", "<p>这是一段示例内容</p>")
    author = data.get("author", "作者")
    
    template = TemplateRegistry.create_instance(template_name)
    if not template:
        return jsonify({"error": "Template not found"}), 404
    
    html = template.render(title=title, content=content, author=author)
    return jsonify({"html": html})

@app.route("/api/pipeline/process", methods=["POST"])
def process_pipeline():
    data = request.json
    import asyncio
    asyncio.run(manager.process_pipeline(
        account_id=data.get("account_id", "default"),
        batch_size=data.get("batch_size", 3)
    ))
    return jsonify({"status": "ok"})

# ============ Vue 前端静态文件服务 ============

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_vue(path):
    """服务 Vue 前端文件"""
    # API 请求不走这里
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404
    
    # 检查是否存在构建的 Vue 文件
    dist_dir = os.path.join(project_root, 'frontend', 'dist')
    
    if os.path.exists(dist_dir):
        # 开发模式：如果文件存在则返回，否则返回 index.html
        file_path = os.path.join(dist_dir, path)
        if path and os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(dist_dir, path)
        return send_from_directory(dist_dir, "index.html")
    
    # 如果没有构建的 Vue 文件，返回提示
    return """
    <h1>AutoPlatform API Server</h1>
    <p>前端未构建。请运行：</p>
    <pre>
cd frontend
npm install
npm run build
    </pre>
    <p>或者开发模式：</p>
    <pre>
cd frontend
npm install
npm run dev
    </pre>
    """, 200

def run_server(host="127.0.0.1", port=8701, debug=False):
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_server()
