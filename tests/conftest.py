import os
import uuid
from pathlib import Path
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

# 覆盖不合法环境变量，避免 bool 解析失败
os.environ["DEBUG"] = "false"

from app.api import server
from app.core.manager import AppManager
from app.models import InspirationRecord, InspirationStatus
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
        fragment = BeautifulSoup(html or "", "html.parser")
        for img in fragment.find_all("img"):
            source = img.get("data-src") or img.get("src", "")
            if source in url_map:
                img["src"] = url_map[source]
                img["data-src"] = url_map[source]
        return str(fragment)

    def sanitize_content_html(self, html):
        fragment = BeautifulSoup(html or "", "html.parser")
        for tag in fragment.find_all(True):
            tag.attrs = {
                key: value
                for key, value in tag.attrs.items()
                if key in {"src", "data-src", "href", "alt"}
            }
        return str(fragment)

    def relink_local_images(self, html, local_images):
        fragment = BeautifulSoup(html or "", "html.parser")
        img_tags = fragment.find_all("img")
        for img, local in zip(img_tags, local_images or []):
            if local.startswith("/local_images/"):
                img["src"] = local
                img["data-src"] = local
        return str(fragment)


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
        title: str = None,
        image_contexts=None,
    ):
        extra = f" [custom: {custom_instructions}]" if custom_instructions else ""
        image_hint = ""
        if image_contexts:
            image_hint = f" [images: {len(image_contexts)}]"
        return {
            "content": f"<h2>Mock Rewritten ({style_preset})</h2><p>{content}{extra}{image_hint}</p>",
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


class FakeImageService:
    def generate(self, prompt: str, size: str = ""):
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
            b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return {
            "bytes": png_bytes,
            "mime_type": "image/png",
            "revised_prompt": prompt,
        }


class FakeWechatLoginStateService:
    state_by_account = {}

    def __init__(self, account=None):
        if hasattr(account, "model_dump"):
            account_data = account.model_dump()
        elif isinstance(account, dict):
            account_data = dict(account)
        else:
            account_data = {}
        self.account_id = account_data.get("account_id", "default")
        self.account_name = account_data.get("name", self.account_id)
        self.state = self.state_by_account.setdefault(
            self.account_id,
            {
                "login_status": False,
                "mps": [],
                "articles": {},
            },
        )

    def status(self):
        article_count = sum(len(rows) for rows in self.state["articles"].values())
        return {
            "ok": True,
            "runtime": {"login_status": self.state["login_status"]},
            "state": {
                "mp_count": len(self.state["mps"]),
                "article_count": article_count,
                "qr_image_exists": False,
                "qr_image_path": "",
            },
        }

    def login(self, **kwargs):
        self.state["login_status"] = True
        result = self.status()
        result.update({"login_ok": True, "login_mode": "fake"})
        return result

    def search_mp(self, keyword: str, limit: int = 10, offset: int = 0):
        return {
            "ok": True,
            "keyword": keyword,
            "items": [
                {
                    "id": f"mp_{keyword.lower()}",
                    "name": f"{keyword} 公众号",
                    "nickname": f"{keyword} 公众号",
                    "signature": "mock mp signature",
                }
            ][:limit],
            "count": 1,
        }

    def list_mps(self):
        return {"ok": True, "items": list(self.state["mps"]), "count": len(self.state["mps"])}

    def add_mp(self, keyword: str, pick: int = 1, limit: int = 10, offset: int = 0):
        mp = {
            "id": f"mp_{keyword.lower()}",
            "name": f"{keyword} 公众号",
        }
        if not any(item["id"] == mp["id"] for item in self.state["mps"]):
            self.state["mps"].append(mp)
        return {"ok": True, "added": mp, "items": list(self.state["mps"]), "count": len(self.state["mps"])}

    def pull_articles(self, mp_id: str, pages: int = 1, mode: str = "api", with_content: bool = False):
        article = {
            "id": f"{mp_id}_a1",
            "title": f"{mp_id} Article 1",
            "url": f"https://mp.weixin.qq.com/s/{mp_id}-article-1",
            "publish_time": 1710000000,
            "publish_time_str": "2026-04-26 10:00",
            "content": "<p>Mock wechat content</p>" if with_content else "",
            "content_cache": {"output": "<p>Mock wechat content</p>"},
            "cover": "https://example.com/wechat-cover.jpg",
        }
        self.state["articles"][mp_id] = [article]
        return {"ok": True, "mp_id": mp_id, "items": [article], "count": 1}

    def list_articles(self, mp_id: str = "", limit: int = 50):
        if mp_id:
            items = list(self.state["articles"].get(mp_id, []))
        else:
            items = []
            for rows in self.state["articles"].values():
                items.extend(rows)
        summarized = []
        for item in items[:limit]:
            summarized.append({
                "id": item["id"],
                "mp_id": mp_id or item.get("mp_id", ""),
                "title": item["title"],
                "url": item["url"],
                "publish_time": item["publish_time"],
                "publish_time_str": item.get("publish_time_str", ""),
                "cover": item.get("cover", ""),
                "has_content": bool(item.get("content") or item.get("content_cache", {}).get("output")),
            })
        return {"ok": True, "mp_id": mp_id, "items": summarized, "count": min(len(items), limit)}

    def get_article_preview(self, collector, mp_id: str, article_id: str):
        article = next((item for item in self.state["articles"].get(mp_id, []) if item["id"] == article_id), None)
        if not article:
            raise RuntimeError("article not found")
        content_html = article.get("content") or article.get("content_cache", {}).get("output", "")
        content_text = BeautifulSoup(content_html, "html.parser").get_text("\n", strip=True)
        return {
            "ok": True,
            "item": {
                "id": article["id"],
                "mp_id": mp_id,
                "title": article["title"],
                "url": article["url"],
                "publish_time": article["publish_time"],
                "publish_time_str": article.get("publish_time_str", ""),
                "content_html": content_html,
                "content_text": content_text,
                "has_content": bool(content_html),
            },
        }

    def batch_fetch_content(self, **kwargs):
        return {"ok": True, "fetched": 1}

    def sync_articles_to_inspirations(self, storage, collector, mp_id: str = "", limit: int = 20):
        rows = list(self.state["articles"].get(mp_id, []))[:limit]
        inserted = 0
        existing_urls = {item.source_url for item in storage.list_inspirations(account_id=self.account_id, limit=500)}
        for row in rows:
            if row["url"] in existing_urls:
                continue
            record = InspirationRecord(
                id=str(uuid.uuid4()),
                source_url=row["url"],
                source_type="wechat_login_state",
                source_account=self.account_name,
                title=row["title"],
                author=self.account_name,
                summary="mock synced summary",
                content="Mock wechat content",
                content_html=row.get("content") or row.get("content_cache", {}).get("output", ""),
                images=[row.get("cover")] if row.get("cover") else [],
                status=InspirationStatus.COLLECTED,
                account_id=self.account_id,
                collected_at=datetime.now(),
                metadata={"wechat_mp_id": mp_id or "mock_mp"},
            )
            storage.create_inspiration(record)
            inserted += 1
        return {"ok": True, "inserted": inserted, "count": len(rows)}

    def full_flow(self, storage, collector, mp_id: str = "", keyword: str = "", pick: int = 1, pages: int = 1, mode: str = "api", with_content: bool = False, content_limit: int = 10, sync_limit: int = 20):
        target_mp_id = mp_id
        if keyword and not target_mp_id:
            added = self.add_mp(keyword=keyword, pick=pick)
            target_mp_id = added["added"]["id"]
        pull = self.pull_articles(mp_id=target_mp_id, pages=pages, mode=mode, with_content=with_content)
        sync = self.sync_articles_to_inspirations(storage=storage, collector=collector, mp_id=target_mp_id, limit=sync_limit)
        return {"ok": True, "pull": pull, "sync": sync}


@pytest.fixture()
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "autoplatform_test.db"
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)

    class TestSettings:
        def __init__(self, data_dir: Path):
            self.data_dir = data_dir

    monkeypatch.setattr("app.core.manager.get_settings", lambda: TestSettings(test_data_dir))

    monkeypatch.setattr("app.core.manager.StorageService", lambda: StorageService(db_path=str(db_path)))
    monkeypatch.setattr("app.core.manager.AIService", FakeAIService)
    monkeypatch.setattr("app.core.manager.CollectorService", FakeCollectorService)
    monkeypatch.setattr("app.core.manager.WechatService", FakeWechatService)
    monkeypatch.setattr("app.core.manager.WechatLoginStateService", FakeWechatLoginStateService)
    monkeypatch.setattr("app.core.manager.ImageService", FakeImageService)
    FakeWechatLoginStateService.state_by_account = {}

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
