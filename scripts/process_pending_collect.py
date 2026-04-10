#!/usr/bin/env python3
"""
批量处理待采集的记录
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.workflow_store import WorkflowStore
from modules.collector import ContentCollector
from modules.inspiration.analyzer import InspirationAnalyzer
from modules.article_state import ArticleState

DB_PATH = PROJECT_ROOT / "output" / "workflow.db"
store = WorkflowStore(str(DB_PATH))
collector = ContentCollector()
analyzer = InspirationAnalyzer()


def process_record(record_id, account_id, url, title):
    """处理单条记录"""
    print(f"\n{'='*60}")
    print(f"处理: {title or '未命名'} ({record_id})")
    print(f"URL: {url}")

    # 更新为采集中
    store.upsert_inspiration({
        "record_id": record_id,
        "account_id": account_id,
        "status": ArticleState.COLLECTING,
        "remark": "正在采集内容...",
    })

    # 采集内容
    article = collector.fetch(url, article_id=record_id)

    if not article:
        print(f"❌ 采集失败")
        store.upsert_inspiration({
            "record_id": record_id,
            "account_id": account_id,
            "status": ArticleState.COLLECT_FAILED,
            "remark": "页面抓取失败",
        })
        return False

    print(f"✅ 采集成功: {article.get('title', '未命名')}")
    print(f"   字数: {len(article.get('content_raw', ''))}")
    print(f"   图片: {len(article.get('images', []))}")

    # 保存内容
    store.save_article_content(
        record_id=record_id,
        account_id=account_id,
        original_html=article.get("content_html", ""),
        original_text=article.get("content_raw", ""),
        original_data={
            "title": article.get("title", title or "未命名"),
            "author": article.get("author", ""),
            "url": url,
            "images": article.get("images", []),
        },
        images=article.get("images", []),
        files_dir=article.get("files_dir", ""),
    )

    # 更新为采集完成
    store.upsert_inspiration({
        "record_id": record_id,
        "account_id": account_id,
        "status": ArticleState.COLLECTED,
        "title": article.get("title", title or "未命名"),
        "remark": f"采集完成，{len(article.get('images', []))}张图片",
    })

    # AI 评分
    print(f"🧠 AI 评分中...")
    store.upsert_inspiration({
        "record_id": record_id,
        "account_id": account_id,
        "status": ArticleState.SCORING,
        "remark": "AI 评分中...",
    })

    if not article.get('title'):
        article['title'] = "未命名文章"
    analysis = analyzer.analyze(article)

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
    parser = argparse.ArgumentParser(description="批量处理待采集记录")
    parser.add_argument("--account-id", default="default", help="账户ID")
    parser.add_argument("--limit", type=int, default=10, help="限制处理数量")
    parser.add_argument("--record-id", help="只处理指定记录")
    args = parser.parse_args()

    if args.record_id:
        item = store.get_inspiration(args.record_id, args.account_id)
        if item:
            process_record(
                item["record_id"],
                item["account_id"],
                item.get("url", ""),
                item.get("title", "")
            )
        else:
            print(f"记录不存在: {args.record_id}")
        return

    # 获取所有待采集记录
    items = store.list_inspiration(args.account_id, status=ArticleState.PENDING_COLLECT, limit=args.limit)
    print(f"找到 {len(items)} 条待采集记录")

    if not items:
        print("没有待处理的任务")
        return

    success = 0
    failed = 0

    for i, item in enumerate(items, 1):
        print(f"\n[{i}/{len(items)}]", end="")
        result = process_record(
            item["record_id"],
            item["account_id"],
            item.get("url", ""),
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
