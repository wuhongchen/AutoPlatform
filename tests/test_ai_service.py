import asyncio

import httpx
import openai

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
    assert "参考文章：" in calls[0]["user"]
    assert "参考文章：" not in calls[1]["user"]


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
