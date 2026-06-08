"""
API服务
基于 Flask Blueprint 的模块化路由
"""
import os
import time
from flask import Flask, jsonify, request, send_file, send_from_directory, redirect
from werkzeug.exceptions import HTTPException
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

# 全局 manager 实例（测试可通过 monkeypatch 替换）
from app.core import AppManager
manager = AppManager()

# 注入到路由模块（blueprints 通过 get_manager_instance() 访问）
from app.api.routes import set_manager_instance
set_manager_instance(manager)

# ========== 注册 Blueprint ==========
from app.api.routes import accounts, articles, inspirations, tasks
from app.api.routes import styles, templates, images, wechat
from app.api.routes import content_flow, pipeline

blueprints = [
    accounts.bp,
    articles.bp,
    inspirations.bp,
    tasks.bp,
    styles.bp,
    templates.bp,
    images.bp,
    wechat.bp,
    content_flow.bp,
    pipeline.bp,
]

for bp in blueprints:
    app.register_blueprint(bp)


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
    return jsonify({"success": False, "error": "Internal server error", "code": "INTERNAL_ERROR"}), 500


# ========== 核心路由（保留在 server.py）==========

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "success": True})


@app.route("/local_images/<path:subpath>")
def local_images(subpath):
    """提供采集的本地图片（带路径遍历防护）"""
    settings = get_settings()
    image_dir = os.path.normpath(str(settings.data_dir / "images"))
    requested_path = os.path.normpath(os.path.join(image_dir, subpath))

    # 路径遍历防护：确保请求路径在允许目录内
    if not requested_path.startswith(image_dir + os.sep) and requested_path != image_dir:
        logger.warning(f"[local_images] path traversal blocked: {subpath}")
        return jsonify({"success": False, "error": "Invalid path", "code": "FORBIDDEN"}), 403

    if os.path.exists(requested_path) and os.path.isfile(requested_path):
        directory = os.path.dirname(requested_path)
        filename = os.path.basename(requested_path)
        return send_from_directory(directory, filename)

    return jsonify({"success": False, "error": "Image not found", "code": "NOT_FOUND"}), 404


# ============ AI 模型配置管理 ============

@app.route("/api/ai-configs", methods=["GET"])
def list_ai_configs():
    configs = manager.list_ai_configs()
    return jsonify(configs)


@app.route("/api/ai-configs", methods=["POST"])
def create_ai_config():
    data = request.json or {}
    if not data.get("id"):
        return jsonify({"error": "配置 ID 不能为空"}), 400
    try:
        config = manager.create_ai_config(data)
        return jsonify(config), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/ai-configs/<config_id>", methods=["GET"])
def get_ai_config(config_id):
    config = manager.get_ai_config(config_id)
    if not config:
        return jsonify({"error": "配置不存在"}), 404
    return jsonify(config)


@app.route("/api/ai-configs/<config_id>", methods=["PUT"])
def update_ai_config(config_id):
    data = request.json or {}
    success = manager.update_ai_config(config_id, data)
    if not success:
        return jsonify({"error": "更新失败或配置不存在"}), 400
    return jsonify({"success": True})


@app.route("/api/ai-configs/<config_id>", methods=["DELETE"])
def delete_ai_config(config_id):
    success = manager.delete_ai_config(config_id)
    if not success:
        return jsonify({"error": "删除失败或配置不存在"}), 400
    return jsonify({"success": True})


@app.route("/api/ai-configs/<config_id>/set-default", methods=["POST"])
def set_default_ai_config(config_id):
    success = manager.set_default_ai_config(config_id)
    if not success:
        return jsonify({"error": "设置失败或配置不存在"}), 400
    return jsonify({"success": True})


@app.route("/api/ai-configs/<config_id>/test", methods=["POST"])
def test_ai_config(config_id):
    import asyncio
    try:
        result = asyncio.run(manager.test_ai_config(config_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})



# ============ RSS 信息源管理 ============

@app.route("/api/feeds", methods=["GET"])
def list_feeds():
    account_id = request.args.get("account_id")
    feeds = manager.list_feed_sources(account_id=account_id if account_id else None)
    return jsonify(feeds)

@app.route("/api/feeds", methods=["POST"])
def create_feed():
    data = request.json or {}
    if not data.get("url"):
        return jsonify({"error": "RSS 地址不能为空"}), 400
    try:
        feed = manager.create_feed_source(data)
        return jsonify(feed), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/feeds/<feed_id>", methods=["GET"])
def get_feed(feed_id):
    feed = manager.get_feed_source(feed_id)
    if not feed:
        return jsonify({"error": "信息源不存在"}), 404
    return jsonify(feed)

@app.route("/api/feeds/<feed_id>", methods=["PUT"])
def update_feed(feed_id):
    data = request.json or {}
    success = manager.update_feed_source(feed_id, data)
    if not success:
        return jsonify({"error": "更新失败"}), 400
    return jsonify({"success": True})

@app.route("/api/feeds/<feed_id>", methods=["DELETE"])
def delete_feed(feed_id):
    success = manager.delete_feed_source(feed_id)
    if not success:
        return jsonify({"error": "删除失败"}), 400
    return jsonify({"success": True})

@app.route("/api/feeds/<feed_id>/fetch", methods=["POST"])
def fetch_feed(feed_id):
    try:
        result = manager.fetch_feed(feed_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/feeds/<feed_id>/toggle", methods=["POST"])
def toggle_feed(feed_id):
    success = manager.toggle_feed_source(feed_id)
    if not success:
        return jsonify({"error": "操作失败"}), 400
    return jsonify({"success": True})


@app.route("/api/articles/sync-published", methods=["POST"])
def sync_published_articles():
    """从微信同步已发布文章"""
    data = request.json or {}
    account_id = data.get("account_id", "default")
    try:
        result = manager.sync_published_articles(account_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/articles/<article_id>/generate-images", methods=["POST"])
def generate_article_images(article_id):
    """为文章批量生成配图"""
    data = request.json or {}
    slides = data.get("slides", [])
    insert_into_article = data.get("insert_into_article", False)
    if not slides:
        return jsonify({"error": "slides 不能为空"}), 400
    try:
        result = manager.generate_article_images(article_id, slides, insert_into_article)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ============ 图片托管 ============

@app.route("/api/image-hosting/upload", methods=["POST"])
def image_hosting_upload():
    from app.services.image_hosting import ImageHostingService
    try:
        result = ImageHostingService.upload(request)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/image-hosting/<path:filename>", methods=["GET"])
def image_hosting_serve(filename):
    from app.services.image_hosting import ImageHostingService
    try:
        return ImageHostingService.serve(filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# ============ 科技信息源 ============

@app.route("/api/tech-sources/presets", methods=["GET"])
def tech_source_presets():
    presets = manager.list_tech_source_presets()
    return jsonify(presets)


@app.route("/api/tech-sources/fetch", methods=["POST"])
def tech_source_fetch():
    data = request.json or {}
    try:
        result = manager.fetch_tech_source(
            source_type=data.get("source_type", ""),
            config=data.get("config", {}),
            account_id=data.get("account_id", "default"),
            limit=data.get("limit", 20),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/tech-sources/fetch-all", methods=["POST"])
def tech_source_fetch_all():
    data = request.json or {}
    try:
        result = manager.fetch_all_tech_sources(data.get("account_id", "default"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400



# ============ 贴图 ============

@app.route("/api/stickers/create", methods=["POST"])
def create_sticker():
    """创建贴图"""
    data = request.json or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    account_id = data.get("account_id", "default")
    images = data.get("images", [])
    publish = data.get("publish", False)
    cover_image = data.get("cover_image", "")
    source_url = data.get("source_url", "")
    tags = data.get("tags", [])
    if not title:
        return jsonify({"error": "标题不能为空"}), 400
    if not images:
        return jsonify({"error": "至少需要一张图片"}), 400
    try:
        result = manager.create_sticker_post(title, description, account_id, images,
                                             publish, cover_image, source_url, tags)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/inspirations/score-unrated", methods=["POST"])
def score_unrated_inspirations():
    """对未评分的灵感进行 AI 评分"""
    import asyncio
    data = request.json or {}
    account_id = data.get("account_id", "")
    try:
        scored = asyncio.run(manager._score_recent_inspirations(account_id or "", limit=20))
        return jsonify({"scored": scored})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_vue(path):
    """服务 Vue 前端文件"""
    # API 请求不走这里
    if path.startswith("api/"):
        return jsonify({"success": False, "error": "Not found", "code": "NOT_FOUND"}), 404

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
