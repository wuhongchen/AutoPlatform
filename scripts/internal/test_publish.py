import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from core.manager import AutoPlatformManager

def test_publish():
    mgr = AutoPlatformManager()
    # Find the record
    records = mgr.feishu.list_records(mgr.smart_table_id)
    target = next((item for item in records.get('items', []) if "Tabbit" in item.get('fields', {}).get('标题', '') and item.get('fields', {}).get('数据流程状态') in ['✨ 已改写(待审)', '❌ 发布失败']), None)
    
    if target:
        record_id = target['record_id']
        revised_url = target.get('fields', {}).get('改后文档链接')
        title = target.get('fields', {}).get('标题', '无标题')
        print(f"Found record: {title}, URL: {revised_url}")
        
        # Test publishing logic
        import re
        doc_token_match = re.search(r'([a-zA-Z0-9]{27,})', str(revised_url))
        print("URL inside test:", revised_url)
        print("Match token:", doc_token_match.group(1) if doc_token_match else "NONE", "len:", len(doc_token_match.group(1)) if doc_token_match else 0)
        
        print("🚀 测试执行 step 2 (确认发布)...")
        try:
            mgr.run_pipeline_step_2(record_id, target.get('fields', {}))
        except Exception as e:
            print(f"执行排版/推送时发生异常: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_publish()
