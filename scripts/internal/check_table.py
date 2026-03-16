import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.feishu import FeishuBitable

def check():
    feishu = FeishuBitable(
        Config.FEISHU_APP_ID, 
        Config.FEISHU_APP_SECRET, 
        Config.FEISHU_APP_TOKEN
    )
    table_id = feishu.get_table_id_by_name(Config.FEISHU_INSPIRATION_TABLE) or feishu.get_table_id_by_name("内容灵感库")
    
    records = feishu.list_records(table_id)
    items = records.get('items', [])
    
    for item in items:
        fields = item.get('fields', {})
        print(f"[{fields.get('处理状态')}] Score: {fields.get('AI 爆款潜力评分')} Title: {fields.get('标题')}")

if __name__ == '__main__':
    check()
