import time


def _create_account(client, account_id: str, name: str = "Test Account"):
    payload = {
        "name": name,
        "account_id": account_id,
        "wechat_appid": "wx_test_appid",
        "wechat_secret": "wx_test_secret",
    }
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
    inspiration = insp_list[0]

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
    created_a = _create_account(client, "acc_a", "Account A")
    created_b = _create_account(client, "acc_b", "Account B")
    assert created_a["account_id"] == "acc_a"
    assert created_b["account_id"] == "acc_b"

    list_resp = client.get("/api/accounts")
    assert list_resp.status_code == 200
    accounts = list_resp.get_json()
    assert len(accounts) == 2

    get_resp = client.get("/api/accounts/acc_a")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["name"] == "Account A"

    update_resp = client.put(
        "/api/accounts/acc_a",
        json={"name": "Account A Updated", "pipeline_batch_size": 5},
    )
    assert update_resp.status_code == 200
    assert update_resp.get_json()["name"] == "Account A Updated"

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
