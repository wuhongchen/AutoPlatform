#!/usr/bin/env python3
"""测试改写功能"""
import os
import sys
sys.path.insert(0, '.')

from config import Config
from modules.workflow_store import WorkflowStore
from modules.ai_caller import UnifiedAICaller

print("=" * 50)
print("测试AI改写功能")
print("=" * 50)

workflow = WorkflowStore(Config.WORKFLOW_DB)
content = workflow.get_article_content('ins_d3661c070b35', 'default')

if not content:
    print("❌ 内容不存在")
    sys.exit(1)

original_data = content.get("original_data", {})
title = original_data.get("title", "")
content_text = content.get("original_text", "")

print(f"标题: {title}")
print(f"内容长度: {len(content_text)}")
print()

article_data = {
    "title": title,
    "content_raw": content_text,
    "content_html": content.get("original_html", ""),
    "images": original_data.get("images", [])
}

print("初始化AI调用器...")
ai = UnifiedAICaller()

print("开始改写（最多180秒）...")
import signal

def timeout_handler(signum, frame):
    print("\n❌ 超时！")
    sys.exit(1)

try:
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(180)  # 3分钟超时
except Exception:
    pass

try:
    result = ai.rewrite(article_data, role_key="tech_expert", preferred_model=None)
    signal.alarm(0)
    print("\n✅ 改写成功！")
    print(f"结果类型: {type(result)}")
    if isinstance(result, dict):
        print(f"标题: {result.get('title', 'N/A')}")
        print(f"内容长度: {len(result.get('content', ''))}")
    else:
        print(f"内容: {str(result)[:200]}...")
except Exception as e:
    signal.alarm(0)
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
