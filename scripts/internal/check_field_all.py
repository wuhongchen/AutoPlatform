import sys, os, json, requests
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
from config import Config
from modules.feishu import FeishuBitable

def check():
    f = FeishuBitable(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET, Config.FEISHU_APP_TOKEN)
    if not f._get_token(): return
    t = f.get_table_id_by_name(Config.FEISHU_PIPELINE_TABLE) or f.get_table_id_by_name("小龙虾智能内容库")
    url = f"{f.base_url}/bitable/v1/apps/{f.app_token}/tables/{t}/fields"
    headers = {"Authorization": f"Bearer {f.token}"}
    resp = requests.get(url, headers=headers).json()
    for field in resp.get("data", {}).get("items", []):
        if field["field_name"] in ["草稿 ID", "备注"]:
            print(f"{field['field_name']}: {field['type']}")

if __name__ == '__main__':
    check()
