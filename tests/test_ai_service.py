import asyncio
from types import SimpleNamespace

import httpx
import openai

from app.core.executor import TaskExecutor
from app.services.ai import AIService


def _timeout_error():
    return openai.APITimeoutError(
        request=httpx.Request("POST", "https://example.com/rewrite")
    )


def test_rewrite_with_context_retries_without_references_on_timeout(monkeypatch):
    service = AIService()
    calls = []

    async def fake_call(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4000, task_name="llm_call"):
        calls.append({"system": system_prompt, "user": user_prompt})
        if len(calls) == 1:
            raise _timeout_error()
        return "<p>retry-ok</p>"

    monkeypatch.setattr(AIService, "_call_llm", fake_call)

    result = asyncio.run(
        service.rewrite_with_context(
            content=("这是一个较短的测试内容，里面包含参考内容和案例拆解。" * 20),
            style_preset="tech_expert",
            inspiration_records=[
                {"title": "参考一", "content": "参考内容" * 80},
                {"title": "参考二", "content": "补充信息" * 60},
            ],
            similarity_threshold=0.0,
        )
    )

    assert result["content"] == "<p>retry-ok</p>"
    assert len(calls) == 2
    assert "参考素材" in calls[0]["user"]
    assert "参考素材" not in calls[1]["user"]


def test_rewrite_with_context_falls_back_to_chunked_mode_on_long_content_timeout(monkeypatch):
    service = AIService()
    calls = []
    long_content = "\n\n".join(
        f"第{i}段：" + ("用于验证长文分段改写。" * 120)
        for i in range(1, 6)
    )

    async def fake_call(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4000, task_name="llm_call"):
        calls.append({"system": system_prompt, "user": user_prompt})
        if len(calls) == 1:
            raise _timeout_error()
        return f"<p>chunk-{len(calls) - 1}</p>"

    monkeypatch.setattr(AIService, "_call_llm", fake_call)

    result = asyncio.run(
        service.rewrite_with_context(
            content=long_content,
            style_preset="tech_expert",
            inspiration_records=[
                {"title": "长文参考", "content": "参考内容" * 120},
            ],
        )
    )

    assert result["content"].count("<p>chunk-") >= 2
    assert len(calls) >= 3
    assert "当前为长文分段改写，第1/" in calls[1]["system"]


def test_rewrite_prompt_includes_image_contexts(monkeypatch):
    service = AIService()
    calls = []

    async def fake_call(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4000, task_name="llm_call"):
        calls.append({"system": system_prompt, "user": user_prompt, "task_name": task_name})
        return "<p>ok</p>"

    monkeypatch.setattr(AIService, "_call_llm", fake_call)

    result = asyncio.run(
        service.rewrite_article(
            content="这是一篇测试文章，正文里有一张图。",
            style_preset="tech_expert",
            title="测试标题",
            image_contexts=[
                {"index": 1, "alt": "产品界面截图", "context": "这一段在解释产品首页的核心交互"},
            ],
        )
    )

    assert result == "<p>ok</p>"
    assert len(calls) == 1
    assert "图片线索" in calls[0]["user"]
    assert "产品界面截图" in calls[0]["user"]
    assert "核心交互" in calls[0]["user"]


def test_rewrite_article_retries_when_overlap_is_too_high(monkeypatch):
    service = AIService()
    calls = []
    content = "这是一个较长的原文内容。" + ("为了验证重写重合度检查，需要提供更多文本。" * 80)

    async def fake_call(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4000, task_name="llm_call"):
        calls.append({"system": system_prompt, "user": user_prompt, "task_name": task_name})
        if len(calls) == 1:
            return f"<p>{content}</p>"
        return "<h2>重写完成</h2><p>这是彻底重构后的成稿。</p>"

    monkeypatch.setattr(AIService, "_call_llm", fake_call)

    result = asyncio.run(
        service.rewrite_article(
            content=content,
            style_preset="tech_expert",
            title="高重合测试",
        )
    )

    assert result == "<h2>重写完成</h2><p>这是彻底重构后的成稿。</p>"
    assert len(calls) == 2
    assert calls[1]["task_name"] == "rewrite_overlap_retry"
    assert "初稿" in calls[1]["user"]


def test_invalid_subscription_error_is_not_retryable():
    executor = TaskExecutor()
    task = SimpleNamespace(retry_count=0, max_retries=3)

    assert executor._should_retry(
        task,
        "Error code: 400 - {'error': {'code': 'InvalidSubscription', "
        "'message': 'CodingPlan subscription has expired'}}",
    ) is False
    assert executor._should_retry(task, "Invalid Authentication") is False
    assert executor._should_retry(task, "access_terminated_error: only available for Coding Agents") is False


def test_ai_provider_invalid_subscription_error_is_actionable():
    service = AIService()
    message = service._normalize_provider_error(
        RuntimeError("InvalidSubscription: CodingPlan subscription has expired")
    )

    assert "CodingPlan" in message
    assert ".env" in message

    auth_message = service._normalize_provider_error(RuntimeError("Invalid Authentication"))
    assert "API Key" in auth_message

    kimi_message = service._normalize_provider_error(
        RuntimeError("access_terminated_error: only available for Coding Agents")
    )
    assert "Kimi" in kimi_message
    assert "通用 API Key" in kimi_message


def test_ark_response_text_extraction_supports_responses_shape():
    service = AIService()
    response = SimpleNamespace(
        error=None,
        status="completed",
        output=[
            SimpleNamespace(type="reasoning", summary=[]),
            SimpleNamespace(
                type="message",
                content=[
                    SimpleNamespace(type="output_text", text=" <p>ok</p> "),
                ],
            ),
        ],
    )

    assert service._extract_ark_response_text(response) == "<p>ok</p>"
    assert service._get_usage_value(
        SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15),
        "prompt_tokens",
        "input_tokens",
    ) == 10


def test_rewrite_prompt_cleans_promotion_and_enforces_deep_rewrite(monkeypatch):
    service = AIService()
    calls = []

    async def fake_call(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4000, task_name="llm_call"):
        calls.append({"system": system_prompt, "user": user_prompt})
        return "<p>这是一段重新组织后的正文。</p><p>扫码关注公众号</p>"

    monkeypatch.setattr(AIService, "_call_llm", fake_call)

    result = asyncio.run(
        service.rewrite_article(
            content="原文第一段保留事实。\n扫码关注公众号领取福利。\n我之前也写过这个工具。\n原文第二段继续说明。",
            style_preset="tech_expert",
            title="测试标题",
        )
    )

    assert "扫码关注" not in calls[0]["user"]
    assert "连续 10 个中文字符" in calls[0]["user"]
    assert "默认使用第三方编辑视角" in calls[0]["system"]
    assert "扫码关注" not in result


def test_near_duplicate_reference_is_skipped(monkeypatch):
    service = AIService()
    calls = []
    content = "这是一段用于验证重复参考过滤的正文。" * 40

    async def fake_call(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4000, task_name="llm_call"):
        calls.append({"user": user_prompt})
        return "<p>这是完全重新组织后的正文。</p>"

    monkeypatch.setattr(AIService, "_call_llm", fake_call)

    result = asyncio.run(
        service.rewrite_with_context(
            content=content,
            style_preset="tech_expert",
            inspiration_records=[{"title": "同源素材", "content": content}],
            similarity_threshold=0.0,
        )
    )

    assert result["reference_count"] == 0
    assert result["used_references"] == []
    assert "参考素材" not in calls[0]["user"]
