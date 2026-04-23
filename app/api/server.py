"""
API服务
"""
import os
import time
from flask import Flask, jsonify, request, send_from_directory, redirect
from werkzeug.exceptions import HTTPException
from app.core import AppManager
from app.core.logger import get_logger
from app.config import get_settings

logger = get_logger("api")

# 获取项目路径
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Vue 构建输出目录
vue_dist_dir = os.path.join(app_dir, "static", "dist")
vue_assets_dir = os.path.join(vue_dist_dir, "assets")

app = Flask(__name__, 
            static_folder=vue_assets_dir if os.path.exists(vue_assets_dir) else os.path.join(app_dir, 'static'),
            static_url_path='/assets')

manager = AppManager()

@app.before_request
def log_request():
    request._start_time = time.time()


@app.after_request
def log_response(response):
    duration = int((time.time() - getattr(request, "_start_time", time.time())) * 1000)
    logger.info(
        f"{request.method} {request.path} | status={response.status_code} | {duration}ms"
    )
    return response


@app.errorhandler(Exception)
def handle_error(e):
    # HTTPException（如 404 NotFound）交给 Flask 正常处理，不转为 500
    if isinstance(e, HTTPException):
        return e
    logger.error(f"Unhandled exception: {type(e).__name__}: {e}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


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

@app.route("/api/accounts/<account_id>", methods=["PUT"])
def update_account(account_id):
    data = request.json or {}
    success = manager.storage.update_account(account_id, data)
    if not success:
        return jsonify({"error": "Update failed or account not found"}), 400
    account = manager.get_account(account_id)
    return jsonify(account.model_dump() if account else {"success": True})

@app.route("/api/accounts/<account_id>", methods=["DELETE"])
def delete_account(account_id):
    success = manager.storage.delete_account(account_id)
    if not success:
        return jsonify({"error": "Delete failed or account not found"}), 400
    return jsonify({"success": True})

@app.route("/api/accounts/<account_id>/stats", methods=["GET"])
def get_stats(account_id):
    stats = manager.get_stats(account_id)
    return jsonify(stats)

@app.route("/api/stats", methods=["GET"])
def get_global_stats():
    account_id = request.args.get("account_id")
    stats = manager.get_stats(account_id if account_id else None)
    return jsonify(stats)

@app.route("/api/inspirations", methods=["POST"])
def collect_inspiration():
    """创建采集任务（异步执行）"""
    data = request.json
    task = manager.create_task(
        name="collect",
        payload={"url": data["url"]},
        account_id=data.get("account_id", "default"),
    )
    return jsonify({
        "task_id": task.id,
        "status": task.status.value,
        "message": "采集任务已创建"
    }), 202

@app.route("/api/inspirations", methods=["GET"])
def list_inspirations():
    account_id = request.args.get("account_id")
    records = manager.storage.list_inspirations(account_id=account_id)
    return jsonify([r.model_dump() for r in records])

@app.route("/api/inspirations/<record_id>", methods=["GET"])
def get_inspiration(record_id):
    record = manager.storage.get_inspiration(record_id)
    if not record:
        return jsonify({"error": "Inspiration not found"}), 404
    return jsonify(record.model_dump())

@app.route("/api/inspirations/<record_id>", methods=["DELETE"])
def delete_inspiration(record_id):
    success = manager.storage.delete_inspiration(record_id)
    if not success:
        return jsonify({"error": "Delete failed or inspiration not found"}), 400
    return jsonify({"success": True})

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
    """创建改写任务（异步执行）"""
    data = request.json or {}
    task = manager.create_task(
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
        "message": "改写任务已创建"
    }), 202

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
    """创建发布任务（异步执行）"""
    data = request.json or {}
    task = manager.create_task(
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
        "message": "发布任务已创建"
    }), 202

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

@app.route("/api/tasks", methods=["POST"])
def create_task():
    """通用任务创建接口"""
    data = request.json
    task = manager.create_task(
        name=data["name"],
        payload=data.get("payload", {}),
        account_id=data.get("account_id", ""),
        target_id=data.get("target_id", ""),
    )
    return jsonify({
        "task_id": task.id,
        "status": task.status.value,
    }), 202


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    """获取任务列表"""
    account_id = request.args.get("account_id")
    status = request.args.get("status")
    name = request.args.get("name")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    tasks = manager.storage.list_tasks(
        account_id=account_id,
        status=status,
        name=name,
        limit=limit,
        offset=offset,
    )
    return jsonify([t.model_dump() for t in tasks])


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """获取单个任务"""
    task = manager.storage.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.model_dump())


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    """删除/取消任务"""
    task = manager.storage.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    # 运行中的任务不允许删除
    from app.models import TaskStatus
    if task.status == TaskStatus.RUNNING:
        return jsonify({"error": "Cannot delete a running task"}), 400
    success = manager.storage.delete_task(task_id)
    return jsonify({"success": success})


@app.route("/api/pipeline/process", methods=["POST"])
def process_pipeline():
    """批量处理任务（异步执行）"""
    data = request.json
    task = manager.create_task(
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
        "message": "批量处理任务已创建"
    }), 202

# ============ Vue 前端静态文件服务 ============

@app.route("/admin", defaults={"subpath": ""})
@app.route("/admin/<path:subpath>")
def legacy_admin(subpath):
    """兼容历史后台入口 /admin"""
    return redirect("/")

@app.route("/favicon.ico")
def favicon():
    """返回空 favicon，避免 404"""
    return "", 204


@app.route("/local_images/<path:subpath>")
def local_images(subpath):
    """提供采集的本地图片"""
    from app.config import get_settings
    import os
    from flask import send_from_directory
    
    settings = get_settings()
    image_dir = str(settings.data_dir / "images")
    file_path = os.path.join(image_dir, subpath)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename)
    
    return jsonify({"error": "Image not found"}), 404


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_vue(path):
    """服务 Vue 前端文件"""
    # API 请求不走这里
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404

    # 检查是否存在构建的 Vue 文件
    dist_dir = vue_dist_dir

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
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoPlatform API Server")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8701, help="监听端口 (默认: 8701)")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    
    args = parser.parse_args()
    
    logger.info(f"AutoPlatform API Server starting at http://{args.host}:{args.port} (debug={args.debug})")
    
    run_server(host=args.host, port=args.port, debug=args.debug)
