#!/usr/bin/env python3
"""
数据迁移脚本：将现有灵感库数据重新采集并灌入新系统
- 采集原文内容保存到 article_contents
- 更新状态为新状态系统
- 可选：执行AI评分
"""
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.workflow_store import WorkflowStore
from modules.article_state import ArticleState, normalize_state
from modules.collector import ContentCollector
from modules.ai_caller import get_unified_caller

# 初始化
DB_PATH = PROJECT_ROOT / "output" / "workflow.db"
store = WorkflowStore(str(DB_PATH))
collector = ContentCollector()

# 统计
stats = {
    "total": 0,
    "success": 0,
    "failed": 0,
    "skipped": 0,
}


def log(msg):
    """打印日志"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def migrate_record(item, force_recollect=False):
    """迁移单条记录"""
    record_id = item.get("record_id")
    account_id = item.get("account_id", "default")
    url = item.get("url", "")
    title = item.get("title", "")
    current_status = item.get("status", "")

    log(f"处理: {title[:40]}... ({record_id})")

    # 1. 检查是否已有内容（除非强制重新采集）
    if not force_recollect:
        existing_content = store.get_article_content(record_id, account_id)
        if existing_content and existing_content.get("original_html"):
            log(f"  ⏭️  已存在内容，跳过")
            stats["skipped"] += 1
            return True

    # 2. 采集内容
    if not url:
        log(f"  ❌ 无URL，无法采集")
        stats["failed"] += 1
        return False

    log(f"  📥 正在采集: {url[:60]}...")
    article = collector.fetch(url)

    if not article:
        log(f"  ❌ 采集失败")
        # 更新状态为采集失败
        store.upsert_inspiration({
            "record_id": record_id,
            "account_id": account_id,
            "status": ArticleState.COLLECT_FAILED,
            "remark": f"采集失败: {url}",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        stats["failed"] += 1
        return False

    # 3. 保存内容到 article_contents
    log(f"  💾 保存内容...")
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

    # 4. 更新灵感库状态
    # 根据旧状态映射到新状态
    new_status = normalize_state(current_status)

    # 如果采集成功但之前是失败状态，更新为采集完成
    if new_status in [ArticleState.COLLECT_FAILED, ArticleState.PENDING_COLLECT]:
        new_status = ArticleState.COLLECTED

    # 构建extra字段
    extra = item.get("extra") or {}
    extra["migrated"] = True
    extra["migrated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra["original_status"] = current_status

    store.upsert_inspiration({
        "record_id": record_id,
        "account_id": account_id,
        "title": article.get("title", title) or title,
        "url": url,
        "status": new_status,
        "remark": f"已迁移并重新采集 | 原文长度: {len(article.get('content_raw', ''))}字",
        "extra": extra,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    log(f"  ✅ 成功，状态: {current_status} -> {new_status}")
    stats["success"] += 1
    return True


def run_migration(account_id=None, limit=None, force_recollect=False):
    """运行迁移"""
    log("=" * 60)
    log("开始数据迁移")
    log("=" * 60)

    # 获取所有灵感记录
    if account_id:
        items = store.list_inspiration(account_id, limit=limit or 10000)
        log(f"账户 {account_id}: 找到 {len(items)} 条记录")
    else:
        # 获取所有账户的记录
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.execute("SELECT DISTINCT account_id FROM inspiration_records")
        all_accounts = [row[0] for row in cursor.fetchall()]
        conn.close()

        items = []
        for acc in all_accounts:
            acc_items = store.list_inspiration(acc, limit=limit or 10000)
            items.extend(acc_items)
        log(f"所有账户: 找到 {len(items)} 条记录")

    stats["total"] = len(items)

    # 逐条处理
    for i, item in enumerate(items, 1):
        log(f"\n[{i}/{len(items)}]")
        try:
            migrate_record(item, force_recollect)
        except Exception as e:
            log(f"  ❌ 异常: {e}")
            stats["failed"] += 1

        # 每10条暂停一下，避免请求过快
        if i % 10 == 0:
            log(f"  ⏸️  暂停2秒...")
            time.sleep(2)

    # 输出统计
    log("\n" + "=" * 60)
    log("迁移完成")
    log("=" * 60)
    log(f"总计: {stats['total']}")
    log(f"成功: {stats['success']}")
    log(f"失败: {stats['failed']}")
    log(f"跳过: {stats['skipped']}")

    # 验证结果
    log("\n验证结果:")
    article_count = store._connect().execute(
        "SELECT COUNT(*) FROM article_contents"
    ).fetchone()[0]
    log(f"  article_contents: {article_count} 条")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="迁移灵感库数据到新系统")
    parser.add_argument("--account-id", help="指定账户ID")
    parser.add_argument("--limit", type=int, help="限制处理数量")
    parser.add_argument("--force", action="store_true", help="强制重新采集已存在的记录")
    args = parser.parse_args()

    run_migration(
        account_id=args.account_id,
        limit=args.limit,
        force_recollect=args.force
    )


if __name__ == "__main__":
    main()
