import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.feishu import FeishuBitable

def auto_approve():
    feishu = FeishuBitable(
        Config.FEISHU_APP_ID, 
        Config.FEISHU_APP_SECRET, 
        Config.FEISHU_APP_TOKEN
    )
    table_id = feishu.get_table_id_by_name(Config.FEISHU_INSPIRATION_TABLE) or feishu.get_table_id_by_name("内容灵感库")
    
    records = feishu.list_records(table_id)
    items = records.get('items', [])
    updated = 0
    
    for item in items:
        fields = item.get('fields', {})
        record_id = item.get('record_id')
        status = fields.get('处理状态')
        score_val = fields.get('AI 爆款潜力评分', 0)
        
        try:
            score = float(score_val)
        except (ValueError, TypeError):
            score = 0
            
        if status == '待审' and score >= 6:
            print(f"✅ 自动通过: {fields.get('标题', '未命名')} (评分: {score})")
            feishu.update_record(table_id, record_id, {'处理状态': '已同步'})
            updated += 1
            
    print(f"✨ 自动通过了 {updated} 篇文章，它们将被同步到自动化发布队列中。")

if __name__ == '__main__':
    auto_approve()
