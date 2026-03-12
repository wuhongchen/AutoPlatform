import os
from dotenv import load_dotenv
from modules.feishu import FeishuBitable

load_dotenv()

def inspect_doc():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_APP_TOKEN")
    feishu = FeishuBitable(app_id, app_secret, app_token)
    
    # 1. 创建文档
    doc_id, doc_url = feishu.create_docx("【结构探测】")
    print(f"📄 文档 ID: {doc_id}")
    
    # 2. 获取所有块
    if not feishu.token: feishu._get_token()
    url = f"{feishu.base_url}/docx/v1/documents/{doc_id}/blocks"
    import requests
    resp = requests.get(url, headers={"Authorization": f"Bearer {feishu.token}"}).json()
    print("📦 文档块结构：")
    import json
    print(json.dumps(resp, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    inspect_doc()
