import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from core.manager_inspiration import InspirationManager

load_dotenv()

def reprocess_all_inspiration():
    manager = InspirationManager()
    print(f"🚀 开始重跑所有灵感库数据...")
    
    if not manager.inspiration_table_id:
        print("❌ 找不到 [内容灵感库] 表格")
        return

    # 获取所有记录
    records_data = manager.feishu.list_records(manager.inspiration_table_id)
    if not records_data or not records_data.get('items'):
        print("📭 灵感库为空")
        return

    items = records_data.get('items', [])
    total = len(items)
    print(f"📋 发现 {total} 条记录，准备逐一重跑...")

    for i, record in enumerate(items):
        fields = record.get('fields', {})
        record_id = record.get('record_id')
        url = fields.get('文章 URL')
        
        if url:
            print(f"\n[{i+1}/{total}] 正在重跑: {url}")
            try:
                manager._process_new_url(record_id, url)
                print(f"✅ [{i+1}/{total}] 重跑成功")
            except Exception as e:
                print(f"❌ [{i+1}/{total}] 重跑失败: {e}")
        else:
            print(f"⏩ [{i+1}/{total}] 跳过（无 URL）")

    print("\n✨ 所有灵感库数据已重跑完成！")

if __name__ == "__main__":
    reprocess_all_inspiration()
