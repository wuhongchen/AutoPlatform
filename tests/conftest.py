import os

import pytest

# 覆盖不合法环境变量，避免 bool 解析失败
os.environ["DEBUG"] = "false"

from app.api import server
from app.core.manager import AppManager
from app.services.storage import StorageService


class FakeCollectorService:
    def fetch_url(self, url: str, timeout: int = 30):
        return {
            "success": True,
            "title": f"Mock Title for {url}",
            "author": "Mock Author",
            "content": "Mock content for testing full pipeline end-to-end.",
            "content_html": "<p>Mock content for testing full pipeline end-to-end.</p>",
            "images": ["https://example.com/mock.jpg"],
            "url": url,
        }
    
    def download_images(self, image_urls, record_id, base_dir="data/images"):
        """Mock: 返回原始URL作为本地路径"""
        return image_urls, {}
    
    def rewrite_image_urls(self, html, url_map):
        """Mock: 直接返回原HTML"""
        return html


class FakeAIService:
    async def score_article(self, title: str, content: str, direction: str = ""):
        return {
            "score": 88,
            "reason": "mock-scored",
            "direction": "mock-direction",
            "insight": "mock-insight",
            "suggested_style": "tech_expert",
        }

    async def rewrite_with_context(
        self,
        content: str,
        style_preset: str = "tech_expert",
        inspiration_records=None,
        similarity_threshold: float = 0.7,
        custom_instructions: str = None,
    ):
        extra = f" [custom: {custom_instructions}]" if custom_instructions else ""
        return {
            "content": f"<h2>Mock Rewritten ({style_preset})</h2><p>{content}{extra}</p>",
            "style_preset": style_preset,
            "used_references": ["mock-reference"],
            "reference_count": 1,
        }


class FakeWechatService:
    def __init__(self, appid=None, secret=None):
        self.appid = appid or ""
        self.secret = secret or ""

    def render_with_template(
        self,
        title: str,
        content: str,
        template_name: str = "default",
        author: str = "",
        cover_image: str = "",
        full_html: bool = False,
        **kwargs,
    ):
        return (
            f"<article data-template='{template_name}'>"
            f"<h1>{title}</h1><div>{content}</div><p>{author}</p></article>"
        )

    def create_draft(self, title: str, content: str, author: str = "", thumb_media_id: str = "", digest: str = ""):
        return "mock_draft_id_001"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "autoplatform_test.db"

    monkeypatch.setattr("app.core.manager.StorageService", lambda: StorageService(db_path=str(db_path)))
    monkeypatch.setattr("app.core.manager.AIService", FakeAIService)
    monkeypatch.setattr("app.core.manager.CollectorService", FakeCollectorService)
    monkeypatch.setattr("app.core.manager.WechatService", FakeWechatService)

    test_manager = AppManager()
    monkeypatch.setattr(server, "manager", test_manager)

    # 重置任务执行器单例，确保每个测试有干净的线程池
    from app.core.executor import TaskExecutor
    TaskExecutor._instance = None
    executor = TaskExecutor()
    executor.set_manager(test_manager)

    server.app.config.update(TESTING=True)
    with server.app.test_client() as test_client:
        yield test_client
    
    # 清理：关闭任务执行器
    try:
        executor.shutdown(wait=True)
    except Exception:
        pass
    TaskExecutor._instance = None
