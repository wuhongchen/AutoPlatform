import sys, os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from config import Config
from modules.feishu import FeishuBitable

def check():
    f = FeishuBitable(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET, Config.FEISHU_APP_TOKEN)
    t = f.get_table_id_by_name(Config.FEISHU_PIPELINE_TABLE) or f.get_table_id_by_name("小龙虾智能内容库")
    records = f.list_records(t).get('items', [])
    for r in records:
        title = r.get('fields', {}).get('标题', '')
        if "Tabbit" in title:
            print("TITLE:", title)
            print("RAW LINK:", r.get('fields', {}).get('改后文档链接'))

if __name__ == '__main__':
    check()
