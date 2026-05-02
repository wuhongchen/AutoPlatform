import importlib.util
import io
import time
from pathlib import Path

from app.api import server


def _create_account(client, account_id: str, name: str = "Test Account", **extra):
    payload = {
        "name": name,
        "account_id": account_id,
        "wechat_appid": "wx_test_appid",
        "wechat_secret": "wx_test_secret",
        "wechat_author": "Test Author",
    }
    payload.update(extra)
    resp = client.post("/api/accounts", json=payload)
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def _poll_task(client, task_id: str, timeout: float = 5.0):
    """轮询异步任务直到完成或失败"""
    for _ in range(int(timeout * 10)):
        resp = client.get(f"/api/tasks/{task_id}")
        if resp.status_code == 200:
            task = resp.get_json()
            if task["status"] in ("completed", "failed"):
                return task
        time.sleep(0.1)
    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


def _collect_and_approve(client, account_id: str, seed: str):
    # 1. 创建采集任务
    collect_resp = client.post(
        "/api/inspirations",
        json={"url": f"https://example.com/{seed}", "account_id": account_id},
    )
    assert collect_resp.status_code == 202, collect_resp.get_json()
    task_info = collect_resp.get_json()

    # 2. 轮询任务完成
    task_result = _poll_task(client, task_info["task_id"])
    assert task_result["status"] == "completed", task_result

    # 3. 获取刚创建的灵感记录
    insp_list = client.get(f"/api/inspirations?account_id={account_id}").get_json()
    assert len(insp_list) > 0
    target_url = f"https://example.com/{seed}"
    inspiration = next(item for item in insp_list if item["source_url"] == target_url)

    # 4. 采纳
    approve_resp = client.post(f"/api/inspirations/{inspiration['id']}/approve")
    assert approve_resp.status_code == 200, approve_resp.get_json()
    return inspiration, approve_resp.get_json()


def test_health_and_admin_redirect(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.get_json()["status"] == "ok"

    admin = client.get("/admin", follow_redirects=False)
    assert admin.status_code in (301, 302, 308)
    assert admin.headers["Location"].endswith("/")


def test_accounts_crud_stats_and_global_stats(client):
    created_a = _create_account(
        client,
        "acc_a",
        "Account A",
        ad_header_html="<p>顶部广告</p>",
        ad_footer_html="<p>底部广告</p>",
    )
    created_b = _create_account(client, "acc_b", "Account B")
    assert created_a["account_id"] == "acc_a"
    assert created_b["account_id"] == "acc_b"
    assert created_a["ad_header_html"] == "<p>顶部广告</p>"
    assert created_a["ad_footer_html"] == "<p>底部广告</p>"

    list_resp = client.get("/api/accounts")
    assert list_resp.status_code == 200
    accounts = list_resp.get_json()
    assert len(accounts) == 2

    get_resp = client.get("/api/accounts/acc_a")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["name"] == "Account A"

    update_resp = client.put(
        "/api/accounts/acc_a",
        json={
            "name": "Account A Updated",
            "pipeline_batch_size": 5,
            "wechat_author": "Updated Author",
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.get_json()["name"] == "Account A Updated"
    assert update_resp.get_json()["wechat_author"] == "Updated Author"

    stats_resp = client.get("/api/accounts/acc_a/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.get_json()
    assert set(stats.keys()) == {"articles", "tasks", "inspiration"}

    global_stats_resp = client.get("/api/stats")
    assert global_stats_resp.status_code == 200
    global_stats = global_stats_resp.get_json()
    assert set(global_stats.keys()) == {"articles", "tasks", "inspiration"}

    scoped_stats_resp = client.get("/api/stats?account_id=acc_a")
    assert scoped_stats_resp.status_code == 200
    scoped_stats = scoped_stats_resp.get_json()
    assert set(scoped_stats.keys()) == {"articles", "tasks", "inspiration"}

    delete_resp = client.delete("/api/accounts/acc_b")
    assert delete_resp.status_code == 200
    assert delete_resp.get_json()["success"] is True

    list_after_delete = client.get("/api/accounts").get_json()
    assert len(list_after_delete) == 1
    assert list_after_delete[0]["account_id"] == "acc_a"


def test_styles_list_create_get_update_toggle_delete(client):
    list_resp = client.get("/api/styles")
    assert list_resp.status_code == 200
    presets = list_resp.get_json()
    assert len(presets) > 0

    create_resp = client.post(
        "/api/styles",
        json={
            "id": "my_custom_style",
            "name": "My Custom Style",
            "description": "Custom style for testing",
            "system_prompt": "Write clearly and directly.",
            "tone": "professional",
            "style": "analytical",
            "temperature": 0.4,
            "max_tokens": 1200,
        },
    )
    assert create_resp.status_code == 201, create_resp.get_json()
    created = create_resp.get_json()
    preset_id = created["id"]
    assert preset_id == "my_custom_style"

    get_resp = client.get(f"/api/styles/{preset_id}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["name"] == "My Custom Style"

    update_resp = client.put(
        f"/api/styles/{preset_id}",
        json={"description": "Updated description", "temperature": 0.6},
    )
    assert update_resp.status_code == 200
    assert update_resp.get_json()["success"] is True

    get_after_update = client.get(f"/api/styles/{preset_id}").get_json()
    assert get_after_update["description"] == "Updated description"
    assert get_after_update["temperature"] == 0.6

    toggle_resp = client.post(f"/api/styles/{preset_id}/toggle")
    assert toggle_resp.status_code == 200
    assert toggle_resp.get_json()["success"] is True

    list_inactive = client.get("/api/styles?include_inactive=true")
    assert list_inactive.status_code == 200
    inactive_map = {item["id"]: item for item in list_inactive.get_json()}
    assert inactive_map[preset_id]["is_active"] is False

    delete_resp = client.delete(f"/api/styles/{preset_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.get_json()["success"] is True

    get_after_delete = client.get(f"/api/styles/{preset_id}")
    assert get_after_delete.status_code == 404


def test_image_asset_upload_generate_list_delete_and_article_cover(client):
    _create_account(client, "acc_img", "Image Account")

    upload_resp = client.post(
        "/api/image-assets/upload",
        data={
            "account_id": "acc_img",
            "title": "Uploaded Cover",
            "file": (io.BytesIO(b"fake-image-bytes"), "cover.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert upload_resp.status_code == 201, upload_resp.get_json()
    uploaded_asset = upload_resp.get_json()
    assert uploaded_asset["account_id"] == "acc_img"
    assert uploaded_asset["source_type"] == "upload"
    assert uploaded_asset["image_url"].startswith("/local_images/")

    generate_resp = client.post(
        "/api/image-assets/generate",
        json={
            "account_id": "acc_img",
            "title": "AI Cover",
            "prompt": "Blue tech hero image for article cover",
        },
    )
    assert generate_resp.status_code == 201, generate_resp.get_json()
    generated_asset = generate_resp.get_json()
    assert generated_asset["source_type"] == "ai"
    assert generated_asset["prompt"] == "Blue tech hero image for article cover"

    list_resp = client.get("/api/image-assets?account_id=acc_img")
    assert list_resp.status_code == 200
    assets = list_resp.get_json()
    assert len(assets) == 2

    create_article_resp = client.post(
        "/api/articles",
        json={
            "account_id": "acc_img",
            "source_title": "Image Cover Article",
            "source_author": "Image Team",
            "cover_image": generated_asset["image_url"],
            "content": "This is the article body.",
            "publish_ready": True,
        },
    )
    assert create_article_resp.status_code == 201, create_article_resp.get_json()
    article = create_article_resp.get_json()
    assert article["cover_image"] == generated_asset["image_url"]

    preview_resp = client.post(
        "/api/templates/default/preview",
        json={
            "title": "Preview With Cover",
            "content": "<p>Preview Body</p>",
            "author": "Tester",
            "cover_image": generated_asset["image_url"],
        },
    )
    assert preview_resp.status_code == 200
    assert generated_asset["image_url"] in preview_resp.get_json()["html"]

    delete_resp = client.delete(f"/api/image-assets/{uploaded_asset['id']}")
    assert delete_resp.status_code == 200
    assert delete_resp.get_json()["success"] is True


def test_rewrite_preserves_reusable_original_images(client):
    _create_account(client, "acc_rewrite_img", "Rewrite Image Account")

    create_article_resp = client.post(
        "/api/articles",
        json={
            "account_id": "acc_rewrite_img",
            "source_title": "带图原文",
            "source_author": "图文作者",
            "content": "<p>第一段</p><p>第二段</p><p>第三段</p>",
            "publish_ready": False,
        },
    )
    assert create_article_resp.status_code == 201, create_article_resp.get_json()
    article = create_article_resp.get_json()
    article_id = article["id"]

    server.manager.storage.update_article(
        article_id,
        {
            "original_html": (
                "<p>第一段</p>"
                "<img src=\"/local_images/rewrite-img/img_001.jpg\" alt=\"示意图一\">"
                "<p>第二段</p>"
                "<img src=\"/local_images/rewrite-img/img_002.jpg\" alt=\"示意图二\">"
                "<p>第三段</p>"
            ),
            "images": [
                "/local_images/rewrite-img/img_001.jpg",
                "/local_images/rewrite-img/img_002.jpg",
            ],
        },
    )

    rewrite_resp = client.post(
        f"/api/articles/{article_id}/rewrite",
        json={"style": "tech_expert", "use_references": False},
    )
    assert rewrite_resp.status_code == 202, rewrite_resp.get_json()
    rewrite_task = _poll_task(client, rewrite_resp.get_json()["task_id"])
    assert rewrite_task["status"] == "completed"

    rewritten_resp = client.get(f"/api/articles/{article_id}")
    assert rewritten_resp.status_code == 200
    rewritten = rewritten_resp.get_json()
    assert rewritten["status"] == "rewritten"
    assert "Mock Rewritten" in rewritten["rewritten_html"]
    assert rewritten["rewritten_html"].count("<img") == 2
    assert "/local_images/rewrite-img/img_001.jpg" in rewritten["rewritten_html"]
    assert "/local_images/rewrite-img/img_002.jpg" in rewritten["rewritten_html"]


def test_inspiration_article_templates_publish_and_pipeline(client):
    _create_account(client, "acc_flow", "Flow Account")

    inspiration, article = _collect_and_approve(client, "acc_flow", "first")
    article_id = article["id"]

    insp_list_resp = client.get("/api/inspirations?account_id=acc_flow")
    assert insp_list_resp.status_code == 200
    inspirations = insp_list_resp.get_json()
    assert len(inspirations) == 1
    assert inspirations[0]["id"] == inspiration["id"]

    insp_get_resp = client.get(f"/api/inspirations/{inspiration['id']}")
    assert insp_get_resp.status_code == 200
    assert insp_get_resp.get_json()["id"] == inspiration["id"]

    articles_resp = client.get("/api/articles?account_id=acc_flow")
    assert articles_resp.status_code == 200
    assert len(articles_resp.get_json()) == 1
    assert articles_resp.get_json()[0]["id"] == article_id

    article_get_resp = client.get(f"/api/articles/{article_id}")
    assert article_get_resp.status_code == 200
    assert article_get_resp.get_json()["status"] == "pending"

    # 改写改为异步任务
    rewrite_resp = client.post(
        f"/api/articles/{article_id}/rewrite",
        json={"style": "tech_expert", "use_references": True},
    )
    assert rewrite_resp.status_code == 202, rewrite_resp.get_json()
    rewrite_task = _poll_task(client, rewrite_resp.get_json()["task_id"])
    assert rewrite_task["status"] == "completed"
    assert rewrite_task["account_id"] == "acc_flow"

    # 验证文章已改写
    rewritten_resp = client.get(f"/api/articles/{article_id}")
    assert rewritten_resp.status_code == 200
    rewritten = rewritten_resp.get_json()
    assert rewritten["status"] == "rewritten"
    assert rewritten["rewrite_style"] == "tech_expert"
    assert "Mock Rewritten" in rewritten["rewritten_html"]

    # 发布改为异步任务
    publish_resp = client.post(
        f"/api/articles/{article_id}/publish",
        json={"template": "default"},
    )
    assert publish_resp.status_code == 202, publish_resp.get_json()
    publish_task = _poll_task(client, publish_resp.get_json()["task_id"])
    assert publish_task["status"] == "completed"
    assert publish_task["account_id"] == "acc_flow"

    # 验证文章已发布
    published_resp = client.get(f"/api/articles/{article_id}")
    assert published_resp.status_code == 200
    published = published_resp.get_json()
    assert published["status"] == "published"
    assert published["wechat_draft_id"] == "mock_draft_id_001"

    templates_resp = client.get("/api/templates")
    assert templates_resp.status_code == 200
    templates = templates_resp.get_json()
    assert "default" in templates

    preview_resp = client.post(
        "/api/templates/default/preview",
        json={"title": "Preview Title", "content": "<p>Preview Body</p>", "author": "Tester"},
    )
    assert preview_resp.status_code == 200
    assert "html" in preview_resp.get_json()
    assert "Preview Title" in preview_resp.get_json()["html"]

    _, pending_article = _collect_and_approve(client, "acc_flow", "second")
    pending_article_id = pending_article["id"]

    # 流水线改为异步批量任务
    pipeline_resp = client.post(
        "/api/pipeline/process",
        json={"account_id": "acc_flow", "batch_size": 10},
    )
    assert pipeline_resp.status_code == 202
    pipeline_task = _poll_task(client, pipeline_resp.get_json()["task_id"])
    assert pipeline_task["status"] == "completed"

    processed_article_resp = client.get(f"/api/articles/{pending_article_id}")
    assert processed_article_resp.status_code == 200
    processed = processed_article_resp.get_json()
    assert processed["status"] == "published"
    assert processed["wechat_draft_id"] == "mock_draft_id_001"

    scoped_stats_resp = client.get("/api/stats?account_id=acc_flow")
    assert scoped_stats_resp.status_code == 200
    scoped_stats = scoped_stats_resp.get_json()
    assert scoped_stats["articles"].get("published", 0) >= 2

    # 任务看板 API 验证
    tasks_resp = client.get("/api/tasks", query_string={"account_id": "acc_flow"})
    assert tasks_resp.status_code == 200
    tasks = tasks_resp.get_json()
    assert len(tasks) >= 3  # collect + rewrite + publish + batch + collect (异步线程可能还在执行中)
    task_names = {task["name"] for task in tasks}
    assert {"collect", "rewrite", "publish", "batch"} <= task_names


def test_collected_inspiration_hidden_styles_are_sanitized(client):
    _create_account(client, "acc_hidden", "Hidden Html Account")

    def fake_hidden_fetch(url: str, timeout: int = 30):
        return {
            "success": True,
            "title": "Hidden Styled Inspiration",
            "author": "Tester",
            "content": "Visible body text.",
            "content_html": (
                '<div id="js_content" style="visibility: hidden; opacity: 0;">'
                '<p>Visible body text.</p>'
                '</div>'
            ),
            "images": [],
            "url": url,
        }

    server.manager.collector.fetch_url = fake_hidden_fetch

    collect_resp = client.post(
        "/api/inspirations",
        json={"url": "https://example.com/hidden", "account_id": "acc_hidden"},
    )
    assert collect_resp.status_code == 202, collect_resp.get_json()
    collect_task = _poll_task(client, collect_resp.get_json()["task_id"])
    assert collect_task["status"] == "completed"

    inspirations = client.get("/api/inspirations?account_id=acc_hidden").get_json()
    inspiration = next(item for item in inspirations if item["source_url"] == "https://example.com/hidden")
    assert "visibility: hidden" not in inspiration["content_html"]
    assert "opacity: 0" not in inspiration["content_html"]
    assert "<p>Visible body text.</p>" in inspiration["content_html"]

    article_resp = client.post(f"/api/inspirations/{inspiration['id']}/create-article")
    assert article_resp.status_code == 200, article_resp.get_json()
    article = article_resp.get_json()
    assert "visibility: hidden" not in article["original_html"]
    assert "opacity: 0" not in article["original_html"]


def test_collected_inspiration_images_are_relinked_to_local_paths(client):
    _create_account(client, "acc_images", "Image Relink Account")

    def fake_image_fetch(url: str, timeout: int = 30):
        remote = "https://example.com/cover.png?foo=1&bar=2"
        return {
            "success": True,
            "title": "Image Relink Inspiration",
            "author": "Tester",
            "content": "Image body text.",
            "content_html": f'<div id="js_content"><p>Image body text.</p><img data-src="{remote}" /></div>',
            "images": [remote],
            "url": url,
        }

    def fake_download_images(image_urls, record_id, base_dir="data/images"):
        return [f"/local_images/{record_id}/img_000.png"], {
            image_urls[0]: f"/local_images/{record_id}/img_000.png"
        }

    server.manager.collector.fetch_url = fake_image_fetch
    server.manager.collector.download_images = fake_download_images

    collect_resp = client.post(
        "/api/inspirations",
        json={"url": "https://example.com/with-image", "account_id": "acc_images"},
    )
    assert collect_resp.status_code == 202, collect_resp.get_json()
    collect_task = _poll_task(client, collect_resp.get_json()["task_id"])
    assert collect_task["status"] == "completed"

    inspirations = client.get("/api/inspirations?account_id=acc_images").get_json()
    inspiration = next(item for item in inspirations if item["source_url"] == "https://example.com/with-image")
    assert '/local_images/' in inspiration["content_html"]
    assert 'data-src="/local_images/' in inspiration["content_html"]
    assert 'src="/local_images/' in inspiration["content_html"]


def test_manual_article_crud_and_template_preview_with_ads(client):
    _create_account(
        client,
        "acc_manual",
        "Manual Account",
        ad_header_html="<p>头部广告</p>",
        ad_footer_html="<p>底部广告</p>",
    )

    create_resp = client.post(
        "/api/articles",
        json={
            "account_id": "acc_manual",
            "source_title": "Manual Article",
            "source_author": "Editor",
            "content": "第一段\n\n第二段",
            "publish_ready": True,
        },
    )
    assert create_resp.status_code == 201, create_resp.get_json()
    created = create_resp.get_json()
    assert created["status"] == "rewritten"
    assert created["metadata"]["manual_created"] is True
    assert "<p>第一段</p>" in created["original_html"]
    assert created["rewritten_html"] == created["original_html"]

    update_resp = client.put(
        f"/api/articles/{created['id']}",
        json={
            "source_title": "Manual Article Updated",
            "source_author": "Editor Updated",
            "content": "<p>已更新内容</p>",
            "publish_ready": False,
        },
    )
    assert update_resp.status_code == 200, update_resp.get_json()
    updated = update_resp.get_json()
    assert updated["status"] == "pending"
    assert updated["source_title"] == "Manual Article Updated"
    assert updated["source_author"] == "Editor Updated"
    assert updated["rewritten_html"] == ""

    preview_resp = client.post(
        "/api/templates/default/preview",
        json={
            "title": "Preview Title",
            "content": "<p>Preview Body</p>",
            "author": "Tester",
            "ad_header_html": "<p>Header Ad</p>",
            "ad_footer_html": "<p>Footer Ad</p>",
        },
    )
    assert preview_resp.status_code == 200
    html = preview_resp.get_json()["html"]
    assert "Header Ad" in html
    assert "Footer Ad" in html


def test_non_retryable_task_failure_is_marked_failed(client):
    task_resp = client.post(
        "/api/tasks",
        json={
            "name": "rewrite",
            "payload": {"article_id": "missing-article-id"},
            "target_id": "missing-article-id",
        },
    )
    assert task_resp.status_code == 202, task_resp.get_json()

    task = _poll_task(client, task_resp.get_json()["task_id"])
    assert task["status"] == "failed"
    assert "文章不存在" in task["error_message"]


def test_wechat_ingest_api_flow_syncs_into_inspirations(client):
    _create_account(client, "acc_wechat_ingest", "Wechat Ingest Account")

    status_resp = client.get("/api/wechat-ingest/status", query_string={"account_id": "acc_wechat_ingest"})
    assert status_resp.status_code == 200, status_resp.get_json()
    assert status_resp.get_json()["state"]["mp_count"] == 0

    login_resp = client.post("/api/wechat-ingest/login", json={"account_id": "acc_wechat_ingest", "wait": False})
    assert login_resp.status_code == 200, login_resp.get_json()
    assert login_resp.get_json()["runtime"]["login_status"] is True

    search_resp = client.post(
        "/api/wechat-ingest/search-mp",
        json={"account_id": "acc_wechat_ingest", "keyword": "DeepSeek", "limit": 5},
    )
    assert search_resp.status_code == 200, search_resp.get_json()
    assert search_resp.get_json()["count"] == 1

    add_resp = client.post(
        "/api/wechat-ingest/add-mp",
        json={"account_id": "acc_wechat_ingest", "keyword": "DeepSeek", "pick": 1},
    )
    assert add_resp.status_code == 200, add_resp.get_json()
    assert add_resp.get_json()["added"]["id"] == "mp_deepseek"

    mps_resp = client.get("/api/wechat-ingest/mps", query_string={"account_id": "acc_wechat_ingest"})
    assert mps_resp.status_code == 200, mps_resp.get_json()
    assert mps_resp.get_json()["count"] == 1

    pull_resp = client.post(
        "/api/wechat-ingest/pull-articles",
        json={
            "account_id": "acc_wechat_ingest",
            "mp_id": "mp_deepseek",
            "pages": 1,
            "with_content": True,
        },
    )
    assert pull_resp.status_code == 200, pull_resp.get_json()
    assert pull_resp.get_json()["count"] == 1

    articles_resp = client.get(
        "/api/wechat-ingest/articles",
        query_string={"account_id": "acc_wechat_ingest", "mp_id": "mp_deepseek", "limit": 20},
    )
    assert articles_resp.status_code == 200, articles_resp.get_json()
    assert articles_resp.get_json()["items"][0]["title"] == "mp_deepseek Article 1"
    assert articles_resp.get_json()["items"][0]["has_content"] is True

    preview_resp = client.get(
        "/api/wechat-ingest/article-preview",
        query_string={
            "account_id": "acc_wechat_ingest",
            "mp_id": "mp_deepseek",
            "article_id": "mp_deepseek_a1",
        },
    )
    assert preview_resp.status_code == 200, preview_resp.get_json()
    assert "Mock wechat content" in preview_resp.get_json()["item"]["content_html"]

    sync_resp = client.post(
        "/api/wechat-ingest/sync-inspirations",
        json={"account_id": "acc_wechat_ingest", "mp_id": "mp_deepseek", "limit": 10},
    )
    assert sync_resp.status_code == 200, sync_resp.get_json()
    assert sync_resp.get_json()["inserted"] == 1

    inspirations = client.get("/api/inspirations?account_id=acc_wechat_ingest").get_json()
    assert len(inspirations) == 1
    assert inspirations[0]["source_type"] == "wechat_login_state"
    assert inspirations[0]["source_url"] == "https://mp.weixin.qq.com/s/mp_deepseek-article-1"


def test_wechat_cached_articles_are_auto_merged_into_inspirations(client):
    _create_account(client, "acc_wechat_merge", "Wechat Merge Account")

    client.post("/api/wechat-ingest/login", json={"account_id": "acc_wechat_merge", "wait": False})
    client.post(
        "/api/wechat-ingest/add-mp",
        json={"account_id": "acc_wechat_merge", "keyword": "DeepSeek", "pick": 1},
    )
    pull_resp = client.post(
        "/api/wechat-ingest/pull-articles",
        json={
            "account_id": "acc_wechat_merge",
            "mp_id": "mp_deepseek",
            "pages": 1,
            "with_content": True,
        },
    )
    assert pull_resp.status_code == 200, pull_resp.get_json()

    inspirations_resp = client.get("/api/inspirations?account_id=acc_wechat_merge&merge_wechat_cache=1")
    assert inspirations_resp.status_code == 200, inspirations_resp.get_json()
    inspirations = inspirations_resp.get_json()
    assert len(inspirations) == 1
    assert inspirations[0]["source_type"] == "wechat_login_state"
    assert inspirations[0]["title"] == "mp_deepseek Article 1"

    inspirations_again = client.get("/api/inspirations?account_id=acc_wechat_merge&merge_wechat_cache=1").get_json()
    assert len(inspirations_again) == 1


def test_wechat_ingest_status_preserves_existing_qr_when_daemon_is_running(monkeypatch, tmp_path):
    service_path = Path(__file__).resolve().parents[1] / "app" / "services" / "wechat_login_state.py"
    spec = importlib.util.spec_from_file_location("wechat_login_state_test", service_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    class TestSettings:
        def __init__(self, root: Path):
            self.project_root = root
            self.output_dir = root / "data" / "output"

    monkeypatch.setattr(module, "get_settings", lambda: TestSettings(tmp_path))

    service = module.WechatLoginStateService({"account_id": "acc_qr_status"})
    qr_path = service.runtime_cwd / "static" / "wx_qrcode.png"
    qr_path.parent.mkdir(parents=True, exist_ok=True)
    qr_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00x\x00\x00\x00x"
        b"\x08\x06\x00\x00\x00"
        + (b"\x00" * 1024)
    )
    qr_path.write_bytes(qr_bytes)
    service.login_daemon_pid_file.write_text("12345", encoding="utf-8")

    monkeypatch.setattr(service, "_pid_alive", lambda _pid: True)

    run_demo_called = {"count": 0}

    def _fail_run_demo(*_args, **_kwargs):
        run_demo_called["count"] += 1
        raise AssertionError("status() should not call runtime status while login daemon is active")

    monkeypatch.setattr(service, "_run_demo", _fail_run_demo)

    result = service.status()
    assert run_demo_called["count"] == 0
    assert result["runtime"]["qr_code"] is True
    assert result["state"]["qr_image_exists"] is True
    assert Path(result["state"]["qr_image_path"]).exists()


def test_wechat_ingest_local_token_detection_supports_yaml(monkeypatch, tmp_path):
    service_path = Path(__file__).resolve().parents[1] / "app" / "services" / "wechat_login_state.py"
    spec = importlib.util.spec_from_file_location("wechat_login_state_test_yaml", service_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    class TestSettings:
        def __init__(self, root: Path):
            self.project_root = root
            self.output_dir = root / "data" / "output"

    monkeypatch.setattr(module, "get_settings", lambda: TestSettings(tmp_path))

    service = module.WechatLoginStateService({"account_id": "acc_yaml_token"})
    token_file = service.runtime_cwd / "data" / "wx.lic"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(
        "token_data:\n  token: 'abc123'\n  cookie: 'foo=bar; '\n",
        encoding="utf-8",
    )

    assert service._local_token_exists() is True


def test_wechat_ingest_status_marks_login_true_when_local_token_exists(monkeypatch, tmp_path):
    service_path = Path(__file__).resolve().parents[1] / "app" / "services" / "wechat_login_state.py"
    spec = importlib.util.spec_from_file_location("wechat_login_state_test_status", service_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    class TestSettings:
        def __init__(self, root: Path):
            self.project_root = root
            self.output_dir = root / "data" / "output"

    monkeypatch.setattr(module, "get_settings", lambda: TestSettings(tmp_path))

    service = module.WechatLoginStateService({"account_id": "acc_login_status"})
    token_file = service.runtime_cwd / "data" / "wx.lic"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(
        "token_data:\n  token: 'abc123'\n  cookie: 'foo=bar; '\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(service, "_run_demo", lambda *args, **kwargs: {
        "ok": True,
        "return_code": 0,
        "stdout": '{"login_status": false, "qr_code": false, "token_exists": false}',
        "stderr": "",
        "timeout": False,
    })

    result = service.status()
    assert result["runtime"]["token_exists"] is True
    assert result["runtime"]["login_status"] is True


def test_wechat_ingest_load_article_html_decodes_content_noencode(monkeypatch, tmp_path):
    service_path = Path(__file__).resolve().parents[1] / "app" / "services" / "wechat_login_state.py"
    spec = importlib.util.spec_from_file_location("wechat_login_state_test_content", service_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    class TestSettings:
        def __init__(self, root: Path):
            self.project_root = root
            self.output_dir = root / "data" / "output"

    monkeypatch.setattr(module, "get_settings", lambda: TestSettings(tmp_path))

    service = module.WechatLoginStateService({"account_id": "acc_content_decode"})
    article = {
        "content": "var msg = {content_noencode: JsDecode('\\x3cp\\x3eHello\\x3c/p\\x3e')};",
    }

    assert service._load_article_html(article) == "<p>Hello</p>"
