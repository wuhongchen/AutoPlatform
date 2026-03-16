import os
import sys
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import Config
from modules.feishu import FeishuBitable
from modules.state_machine import PipelineState


def revert_test_record():
    feishu = FeishuBitable(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET, Config.FEISHU_APP_TOKEN)
    if not feishu._get_token():
        print("❌ token 获取失败")
        return

    table_id = feishu.get_table_id_by_name(Config.FEISHU_PIPELINE_TABLE) or feishu.get_table_id_by_name("小龙虾智能内容库")
    records = feishu.list_records(table_id).get("items", [])

    for r in records:
        if "测试" not in r.get("fields", {}).get("标题", ""):
            continue
        rid = r["record_id"]
        url = f"{feishu.base_url}/bitable/v1/apps/{feishu.app_token}/tables/{table_id}/records/{rid}"
        headers = {"Authorization": f"Bearer {feishu.token}", "Content-Type": "application/json; charset=utf-8"}
        payload = {
            "fields": {
                "数据流程状态": PipelineState.PUBLISHED,
                "标题": "测完OpenClaw我直接卸载了：这款免费原生AI浏览器，能替你干80%的网页办公活",
                "备注": "已同步至草稿箱 ID: 测试版"
            }
        }
        resp = requests.put(url, headers=headers, json=payload).json()
        print(resp)
        break


if __name__ == "__main__":
    revert_test_record()
