import sys, os, requests, json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from config import Config
from modules.feishu import FeishuBitable
from modules.state_machine import PipelineState

def test():
    f = FeishuBitable(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET, Config.FEISHU_APP_TOKEN)
    if not f._get_token(): return
    t = f.get_table_id_by_name(Config.FEISHU_PIPELINE_TABLE) or f.get_table_id_by_name("小龙虾智能内容库")

    records = f.list_records(t).get('items', [])
    for r in records:
        title = r.get('fields', {}).get('标题', '')
        if "Tabbit" in title or "测试" in title:
            rid = r['record_id']
            url = f"{f.base_url}/bitable/v1/apps/{f.app_token}/tables/{t}/records/{rid}"
            headers = {"Authorization": f"Bearer {f.token}", "Content-Type": "application/json; charset=utf-8"}
            
            payload = {"fields": {"数据流程状态": PipelineState.PUBLISHED, "草稿 ID": "test1234", "标题": "测试", "备注": "123"}}
            resp = requests.put(url, headers=headers, json=payload).json()
            print(f"Update test: {json.dumps(resp, ensure_ascii=False)}")
            break

if __name__ == '__main__':
    test()
