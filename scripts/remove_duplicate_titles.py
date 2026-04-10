#!/usr/bin/env python3
"""
删除标题重复的灵感库记录，只保留每条标题最早的一条
"""
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "output" / "workflow.db"


def remove_duplicates():
    """删除重复标题的记录"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 1. 查找所有重复的标题
    cursor.execute("""
        SELECT title, COUNT(*) as cnt, MIN(captured_at) as earliest
        FROM inspiration_records
        GROUP BY title
        HAVING cnt > 1
        ORDER BY cnt DESC
    """)
    duplicates = cursor.fetchall()

    if not duplicates:
        print("✅ 没有发现重复的标题")
        conn.close()
        return

    print(f"发现 {len(duplicates)} 个重复标题")
    print("-" * 60)

    total_deleted = 0

    for title, count, earliest in duplicates:
        # 查询该标题的所有记录ID，按时间排序
        cursor.execute("""
            SELECT record_id, captured_at
            FROM inspiration_records
            WHERE title = ?
            ORDER BY captured_at ASC
        """, (title,))

        records = cursor.fetchall()
        keep_id = records[0][0]  # 保留最早的一条
        delete_ids = [r[0] for r in records[1:]]  # 删除其余的

        print(f"\n标题: '{title[:50]}{'...' if len(title) > 50 else ''}'")
        print(f"  共 {count} 条，保留: {keep_id} ({earliest})")
        print(f"  删除: {len(delete_ids)} 条")

        # 执行删除
        for del_id in delete_ids:
            cursor.execute("DELETE FROM inspiration_records WHERE record_id = ?", (del_id,))
            total_deleted += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"✅ 完成! 共删除 {total_deleted} 条重复记录")


if __name__ == "__main__":
    # 确认操作
    if len(sys.argv) > 1 and sys.argv[1] == "--confirm":
        remove_duplicates()
    else:
        print("将要删除重复的标题记录，只保留最早的一条")
        print("请运行: python scripts/remove_duplicate_titles.py --confirm")
