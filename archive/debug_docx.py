import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def debug_docx_append():
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    
    # 1. Get Token
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    token_resp = requests.post(token_url, json={"app_id": app_id, "app_secret": app_secret}).json()
    token = token_resp.get("tenant_access_token")
    
    # 2. Create a test doc
    create_url = "https://open.feishu.cn/open-apis/docx/v1/documents"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    create_resp = requests.post(create_url, headers=headers, json={"title": "Debug Test Doc"}).json()
    doc_id = create_resp["data"]["document"]["document_id"]
    print(f"Created doc: {doc_id}")
    
    # 3. Try to append text
    append_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
    payload = {
        "children": [
            {
                "block_type": 2,
                "text": {
                    "elements": [
                        {
                            "text_run": {
                                "content": "Hello World Test Content",
                                "text_element_style": {}
                            }
                        }
                    ],
                    "style": {}
                }
            }
        ]
    }
    
    print(f"Appending to: {append_url}")
    resp = requests.post(append_url, headers=headers, json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

if __name__ == "__main__":
    debug_docx_append()
