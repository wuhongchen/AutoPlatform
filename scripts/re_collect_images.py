#!/usr/bin/env python3
"""
重新采集文章并下载图片到本地
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.workflow_store import WorkflowStore
from modules.collector import ContentCollector

DB_PATH = PROJECT_ROOT / "output" / "workflow.db"
store = WorkflowStore(str(DB_PATH))
collector = ContentCollector()


def re_collect_with_images(record_id, account_id, url, title):
    """重新采集文章并下载图片"""
    print(f"\n📥 重新采集: {title[:40]}... ({record_id})")

    if not url:
        print(f"  ❌ 无URL，跳过")
        return False

    article = collector.fetch(url, article_id=record_id)

    if not article:
        print(f"  ❌ 采集失败")
        return False

    # 更新 article_contents 中的内容
    existing = store.get_article_content(record_id, account_id)
    if existing:
        # 保留原有的 rewritten 内容（如果有）
        store.save_article_content(
            record_id=record_id,
            account_id=account_id,
            original_html=article.get("content_html", ""),
            original_text=article.get("content_raw", ""),
            original_data={
                "title": article.get("title", title),
                "author": article.get("author", ""),
                "url": url,
                "images": article.get("images", []),
            },
            rewritten_html=existing.get("rewritten_html", ""),
            rewritten_text=existing.get("rewritten_text", ""),
            rewritten_data=existing.get("rewritten_data", {}),
            images=article.get("images", []),
            files_dir=article.get("files_dir", ""),
        )
    else:
        store.save_article_content(
            record_id=record_id,
            account_id=account_id,
            original_html=article.get("content_html", ""),
            original_text=article.get("content_raw", ""),
            original_data={
                "title": article.get("title", title),
                "author": article.get("author", ""),
                "url": url,
                "images": article.get("images", []),
            },
            images=article.get("images", []),
            files_dir=article.get("files_dir", ""),
        )

    print(f"  ✅ 完成，下载了 {len(article.get('images', []))} 张图片")
    print(f"  📁 保存位置: {article.get('files_dir', 'N/A')}")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="重新采集文章并下载图片")
    parser.add_argument("--account-id", default="default", help="账户ID")
    parser.add_argument("--limit", type=int, help="限制处理数量")
    parser.add_argument("--record-id", help="只处理指定记录")
    args = parser.parse_args()

    if args.record_id:
        # 处理单条记录
        item = store.get_inspiration(args.record_id, args.account_id)
        if item:
            re_collect_with_images(
                item["record_id"],
                item["account_id"],
                item.get("url", ""),
                item.get("title", "")
            )
        else:
            print(f"记录不存在: {args.record_id}")
        return

    # 获取所有记录
    items = store.list_inspiration(args.account_id, limit=args.limit or 1000)
    print(f"找到 {len(items)} 条记录")

    success = 0
    failed = 0

    for i, item in enumerate(items, 1):
        print(f"\n[{i}/{len(items)}]", end="")
        result = re_collect_with_images(
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
