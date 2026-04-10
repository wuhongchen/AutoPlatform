#!/usr/bin/env python3
"""
为已采集但未评分的记录进行 AI 评分
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.workflow_store import WorkflowStore
from modules.inspiration.analyzer import InspirationAnalyzer
from modules.article_state import ArticleState

DB_PATH = PROJECT_ROOT / "output" / "workflow.db"
store = WorkflowStore(str(DB_PATH))
analyzer = InspirationAnalyzer()


def score_record(record_id, account_id, title):
    """为单条记录评分"""
    print(f"\n{'='*60}")
    print(f"评分: {title or '未命名'} ({record_id})")

    # 获取文章内容
    content = store.get_article_content(record_id, account_id)
    if not content:
        print(f"❌ 无内容，跳过")
        return False

    # 构建 article 数据
    article = {
        'title': content.get('original_data', {}).get('title', title or '未命名'),
        'content_raw': content.get('original_text', ''),
        'content_html': content.get('original_html', ''),
    }

    # 更新为评分中
    store.upsert_inspiration({
        "record_id": record_id,
        "account_id": account_id,
        "status": ArticleState.SCORING,
        "remark": "AI 评分中...",
    })

    # AI 评分
    print(f"🧠 AI 评分中...")
    try:
        analysis = analyzer.analyze(article)
    except Exception as e:
        print(f"❌ 评分失败: {e}")
        store.upsert_inspiration({
            "record_id": record_id,
            "account_id": account_id,
            "status": ArticleState.COLLECTED,
            "remark": f"评分失败: {str(e)[:50]}",
        })
        return False

    print(f"✅ 评分完成: {analysis['score']}分")
    print(f"   理由: {analysis['reason'][:100]}...")

    # 保存评分结果
    extra_data = {
        "ai_score": analysis.get("score"),
        "ai_reason": analysis.get("reason"),
        "topics": analysis.get("topics", []),
        "article_type": analysis.get("article_type", ""),
    }

    # 根据评分决定状态
    if analysis['score'] >= 5:
        store.upsert_inspiration({
            "record_id": record_id,
            "account_id": account_id,
            "status": ArticleState.PENDING_REWRITE,
            "remark": f"评分{analysis['score']}分，等待改写",
            "extra": extra_data,
        })
        print(f"📤 评分达标，进入待改写状态")
    else:
        store.upsert_inspiration({
            "record_id": record_id,
            "account_id": account_id,
            "status": ArticleState.SKIPPED,
            "remark": f"评分{analysis['score']}分，已跳过",
            "extra": extra_data,
        })
        print(f"📉 评分较低，已跳过")

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="为已采集记录评分")
    parser.add_argument("--account-id", default="default", help="账户ID")
    parser.add_argument("--limit", type=int, default=10, help="限制处理数量")
    args = parser.parse_args()

    # 获取所有采集完成但未评分的记录
    items = store.list_inspiration(args.account_id, status=ArticleState.COLLECTED, limit=args.limit)
    print(f"找到 {len(items)} 条采集完成但未评分的记录")

    if not items:
        print("没有待处理的任务")
        return

    success = 0
    failed = 0

    for i, item in enumerate(items, 1):
        print(f"\n[{i}/{len(items)}]", end="")
        result = score_record(
            item["record_id"],
            item["account_id"],
            item.get("title", "")
        )
        if result:
            success += 1
        else:
            failed += 1

    print(f"\n\n{'='*60}")
    print(f"完成! 成功: {success}, 失败: {failed}")


if __name__ == "__main__":
    main()
